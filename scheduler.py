import random
from datetime import datetime, time, timedelta
from pathlib import Path
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from models import get_session, Profile, JourneyState, JourneyLog, Location, Activity, ScheduledTask
from engine.state_machine import StateMachine
from engine.storyteller import Storyteller
from engine.image_gen import get_image_generator


class Scheduler:
    TIME_SLOTS = [
        (6, 9, 30), (10, 12, 25), (14, 17, 30), (20, 22, 15),
    ]

    def __init__(self):
        self._aps = BackgroundScheduler()
        self.state_machine = StateMachine()
        self.storyteller = Storyteller()

    def start(self):
        self._aps.add_job(self.plan_today, trigger="cron", hour=0, minute=1, id="plan_today", replace_existing=True)
        self._aps.start()
        self._first_generation_if_empty()

    def _first_generation_if_empty(self):
        """Generate the first photo immediately if no journey logs exist yet."""
        import threading
        def gen():
            import time
            time.sleep(2)  # Wait for server to fully start
            session = get_session()
            log_count = session.query(JourneyLog).count()
            session.close()
            if log_count == 0:
                self.run_generation()
        t = threading.Thread(target=gen, daemon=True)
        t.start()

    def plan_today(self):
        session = get_session()
        pending = session.query(ScheduledTask).filter_by(status="pending").all()
        for task in pending:
            task.status = "cancelled"
        session.commit()

        times = self._generate_daily_times()
        now = datetime.now()
        for t in times:
            scheduled_dt = datetime(now.year, now.month, now.day, t.hour, t.minute)
            task = ScheduledTask(scheduled_at=scheduled_dt, status="pending")
            session.add(task)
            session.flush()
            self._aps.add_job(self.run_generation, trigger="date", run_date=scheduled_dt, id=f"gen_{task.id}", replace_existing=True)
        session.commit()
        session.close()

    @staticmethod
    def _generate_daily_times() -> list[time]:
        num_events = random.choices([1, 2, 3], weights=[30, 50, 20], k=1)[0]
        for _ in range(100):
            chosen = []
            for _ in range(num_events):
                slot = random.choices(Scheduler.TIME_SLOTS, weights=[s[2] for s in Scheduler.TIME_SLOTS], k=1)[0]
                hour = random.randint(slot[0], slot[1] - 1)
                minute = random.randint(0, 59)
                chosen.append(time(hour, minute))
            chosen.sort()
            valid = True
            for i in range(len(chosen) - 1):
                gap = (datetime.combine(datetime.today(), chosen[i + 1]) -
                       datetime.combine(datetime.today(), chosen[i])).seconds / 3600
                if gap < 4:
                    valid = False
                    break
            if valid:
                return chosen
        return [time(10, 0)]

    def _get_features(self, profile: "Profile") -> str:
        """Extract detailed dog features from reference photos via vision model. Cached."""
        import base64, io, json
        from pathlib import Path
        from PIL import Image

        cache_file = Path("data/xiaobu_features.txt")
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8").strip()

        if not profile.reference_photos or not profile.image_api_key:
            return ""

        try:
            photos_b64 = []
            for path in profile.reference_photos[:3]:
                fp = Path(path)
                if not fp.is_absolute():
                    fp = Path.cwd() / fp
                if fp.exists():
                    img = Image.open(fp).convert("RGB")
                    w, h = img.size
                    ratio = 800 / max(w, h)
                    img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=80)
                    photos_b64.append(base64.b64encode(buf.getvalue()).decode())

            content = [{"type": "text", "text": "请非常详细地描述照片中这只狗的外貌特征。逐项列出：耳朵形状/颜色/大小/位置、头型比例、眼睛颜色/大小/间距/眼神、鼻子颜色/形状、嘴巴特征、毛色分布/纹理/长度、体型、尾巴形状/毛量、独特的白色斑块或标记。用中文，约200字。"}]
            for b64 in photos_b64:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

            resp = httpx.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                json={
                    "model": "doubao-1-5-vision-pro-32k-250115",
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 500,
                },
                headers={"Authorization": f"Bearer {profile.image_api_key}", "Content-Type": "application/json"},
                timeout=60,
            )
            if resp.status_code == 200:
                features = resp.json()["choices"][0]["message"]["content"]
                cache_file.write_text(features, encoding="utf-8")
                return features
        except Exception as e:
            print(f"Vision analysis failed: {e}")
        return ""

    def shutdown(self) -> None:
        if not self._aps.running:
            return
        self._aps.shutdown(wait=False)

    def run_generation(self):
        session = get_session()
        try:
            profile = session.query(Profile).first()
            if not profile:
                session.close()
                return

            state = session.query(JourneyState).first()
            if not state:
                rainbow = session.query(Location).filter_by(name="彩虹桥").first()
                state = JourneyState(current_location_id=rainbow.id if rainbow else None)
                session.add(state)
                session.flush()

            weather = self.state_machine.roll_weather()
            next_location = self.state_machine.select_next_location(state, profile, session)
            activity = self.state_machine.select_activity(next_location, profile)
            if not activity:
                session.close()
                return

            # Extract dog features via vision model (cached after first run)
            features = self._get_features(profile)

            prompt = self.storyteller.compose_prompt(activity, profile, weather, state.mood, features)
            # Use Seedream if key is set, otherwise fall back to env/default
            api_type = "seedream" if profile.image_api_key else None
            image_gen = get_image_generator(api_type=api_type, api_key=profile.image_api_key)
            image_path = image_gen.generate(prompt, profile.reference_photos or [])
            image_path = image_path.replace("\\", "/")  # Normalize for web URLs
            story = self.storyteller.compose_story(activity, profile)
            new_mood = self.state_machine.update_mood(state.mood, activity.name)

            log_entry = JourneyLog(
                location_id=next_location.id, activity_id=activity.id,
                story_text=story, image_path=image_path,
                weather=weather, mood=new_mood, generated_at=datetime.now(),
            )
            session.add(log_entry)
            session.flush()

            state.current_location_id = next_location.id
            state.mood = new_mood
            state.day_number += 1
            state.weather_today = weather
            state.last_activity_id = activity.id

            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

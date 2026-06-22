import random
from datetime import datetime, time, timedelta
from pathlib import Path
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from models import get_session, Profile, JourneyState, JourneyLog, Location, Activity, ScheduledTask, ContentBuffer
from engine.state_machine import StateMachine
from engine.storyteller import Storyteller
from engine.image_gen import get_image_generator
from memory import load_memory_context, save_memory


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
        from models import User
        def gen():
            import time
            time.sleep(2)  # Wait for server to fully start
            session = get_session()
            log_count = session.query(JourneyLog).count()
            if log_count == 0:
                users = session.query(User).all()
                for user in users:
                    profile = session.query(Profile).filter_by(user_id=user.id).first()
                    if profile and profile.image_api_key:
                        self.run_generation(user.id)
            session.close()
        t = threading.Thread(target=gen, daemon=True)
        t.start()

    def plan_today(self):
        sess = get_session()
        # Cancel old pending tasks
        pending = sess.query(ScheduledTask).filter_by(status="pending").all()
        for task in pending:
            task.status = "cancelled"
        sess.commit()

        # Get all users with API keys
        from models import User
        users = sess.query(User).all()
        now = datetime.now()

        for user in users:
            # Check user has profile and API key
            profile = sess.query(Profile).filter_by(user_id=user.id).first()
            if not profile or not profile.image_api_key:
                continue

            times = self._generate_daily_times()
            for t in times:
                scheduled_dt = datetime(now.year, now.month, now.day, t.hour, t.minute)
                task = ScheduledTask(
                    user_id=user.id,
                    scheduled_at=scheduled_dt,
                    status="pending",
                )
                sess.add(task)
                sess.flush()
                self._aps.add_job(
                    self.run_generation,
                    args=[user.id],
                    trigger="date",
                    run_date=scheduled_dt,
                    id=f"gen_{task.id}",
                    replace_existing=True,
                )
        sess.commit()
        sess.close()

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

    def _get_features(self, profile: "Profile", user_id: int) -> str:
        """Extract detailed dog features from reference photos via vision model. Cached."""
        import base64, io, json
        from pathlib import Path
        from PIL import Image

        cache_dir = Path("data/features")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{user_id}_features.txt"
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

    def consume_buffer(self, user_id: int) -> dict | None:
        """Take the oldest ready buffer item, mark as sent, return it as a JourneyLog dict.
        Triggers async refill if buffer goes below target."""
        sess = get_session()
        try:
            item = (
                sess.query(ContentBuffer)
                .filter_by(user_id=user_id, status="ready")
                .order_by(ContentBuffer.created_at.asc())
                .first()
            )
            if not item:
                return None

            # Create JourneyLog from buffer item
            log = JourneyLog(
                user_id=user_id,
                location_id=item.location_id,
                activity_id=item.activity_id,
                story_text=item.story_text,
                image_path=item.image_path,
                weather=item.weather,
                mood=item.mood,
                generated_at=datetime.now(),
            )
            sess.add(log)
            sess.flush()

            result = {
                "id": log.id,
                "story_text": log.story_text,
                "image_path": log.image_path,
                "location_name": item.location_name,
                "weather": item.weather,
                "mood": item.mood,
                "generated_at": log.generated_at.strftime("%m月%d日 %H:%M"),
            }

            # Mark buffer item as sent
            item.status = "sent"
            sess.commit()

            # Async refill
            import threading
            t = threading.Thread(target=self.refill_buffer, args=(user_id,), daemon=True)
            t.start()

            return result
        except Exception:
            sess.rollback()
            return None
        finally:
            sess.close()

    def refill_buffer(self, user_id: int, target: int = 5):
        """Generate content in background until buffer has `target` ready items."""
        sess = get_session()
        try:
            profile = sess.query(Profile).filter_by(user_id=user_id).first()
            if not profile or not profile.image_api_key:
                return

            ready_count = (
                sess.query(ContentBuffer)
                .filter_by(user_id=user_id, status="ready")
                .count()
            )
            generating_count = (
                sess.query(ContentBuffer)
                .filter_by(user_id=user_id, status="generating")
                .count()
            )

            while ready_count + generating_count < target:
                # Mark a placeholder as generating
                placeholder = ContentBuffer(
                    user_id=user_id, status="generating",
                )
                sess.add(placeholder)
                sess.commit()
                placeholder_id = placeholder.id

                try:
                    # Run full generation (story + image)
                    state = sess.query(JourneyState).filter_by(user_id=user_id).first()
                    if not state:
                        rainbow = sess.query(Location).filter_by(name="彩虹桥").first()
                        state = JourneyState(user_id=user_id, current_location_id=rainbow.id if rainbow else None)
                        sess.add(state)
                        sess.flush()

                    weather = self.state_machine.roll_weather()
                    next_location = self.state_machine.select_next_location(state, profile, sess)
                    activity = self.state_machine.select_activity(next_location, profile)
                    if not activity:
                        placeholder.status = "ready"  # fallback
                        sess.commit()
                        break

                    features = self._get_features(profile, user_id)

                    all_logs = (
                        sess.query(JourneyLog)
                        .filter_by(user_id=user_id)
                        .order_by(JourneyLog.generated_at.asc())
                        .all()
                    )
                    all_stories = [log.story_text for log in all_logs if log.story_text]

                    memory_context = load_memory_context(user_id)
                    if not memory_context:
                        memory_context = ""

                    story = self.storyteller.compose_story(
                        activity, profile,
                        weather=weather, mood=state.mood, features=features,
                        memory_context=memory_context,
                        all_stories_count=len(all_stories),
                        api_key=profile.text_api_key or profile.image_api_key or "",
                    )

                    prompt = self.storyteller.compose_prompt(
                        activity, profile, weather, state.mood, features,
                        story_text=story,
                    )
                    api_type = "seedream" if profile.image_api_key else None
                    image_gen = get_image_generator(api_type=api_type, api_key=profile.image_api_key)
                    image_path = image_gen.generate(prompt, profile.reference_photos or [])
                    image_path = image_path.replace("\\", "/")

                    # Move to user-scoped dir
                    import shutil
                    src = Path(image_path)
                    user_gen_dir = Path("data/generated") / str(user_id)
                    user_gen_dir.mkdir(parents=True, exist_ok=True)
                    dst = user_gen_dir / src.name
                    if src != dst and src.exists():
                        shutil.move(str(src), str(dst))
                    image_path = str(dst).replace("\\", "/")

                    placeholder.story_text = story
                    placeholder.image_path = image_path
                    placeholder.location_name = next_location.name
                    placeholder.weather = weather
                    placeholder.mood = state.mood
                    placeholder.location_id = next_location.id
                    placeholder.activity_id = activity.id
                    placeholder.status = "ready"
                    sess.commit()

                    ready_count += 1
                except Exception as e:
                    print(f"Buffer refill error for user {user_id}: {e}")
                    sess.rollback()
                    # Remove failed placeholder
                    try:
                        sess.query(ContentBuffer).filter_by(id=placeholder_id).delete()
                        sess.commit()
                    except Exception:
                        pass
                    break

                # Re-count
                ready_count = (
                    sess.query(ContentBuffer)
                    .filter_by(user_id=user_id, status="ready")
                    .count()
                )
                generating_count = (
                    sess.query(ContentBuffer)
                    .filter_by(user_id=user_id, status="generating")
                    .count()
                )
        finally:
            sess.close()

    def shutdown(self) -> None:
        if not self._aps.running:
            return
        self._aps.shutdown(wait=False)

    def run_generation(self, user_id: int):
        sess = get_session()
        try:
            profile = sess.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                sess.close()
                return

            state = sess.query(JourneyState).filter_by(user_id=user_id).first()
            if not state:
                rainbow = sess.query(Location).filter_by(name="彩虹桥").first()
                state = JourneyState(user_id=user_id, current_location_id=rainbow.id if rainbow else None)
                sess.add(state)
                sess.flush()

            weather = self.state_machine.roll_weather()
            next_location = self.state_machine.select_next_location(state, profile, sess)
            activity = self.state_machine.select_activity(next_location, profile)
            if not activity:
                sess.close()
                return

            features = self._get_features(profile, user_id)

            # Fetch all past stories for memory context
            all_logs = (
                sess.query(JourneyLog)
                .filter_by(user_id=user_id)
                .order_by(JourneyLog.generated_at.asc())
                .all()
            )
            all_stories = [log.story_text for log in all_logs if log.story_text]

            # Load or build full memory
            memory_context = load_memory_context(user_id)
            if not memory_context:
                memory_context = ""  # will be built after first story

            # Generate story FIRST, so image prompt can reference story details
            story = self.storyteller.compose_story(
                activity, profile,
                weather=weather, mood=state.mood, features=features,
                memory_context=memory_context,
                all_stories_count=len(all_stories),
                api_key=profile.text_api_key or profile.image_api_key or "",
            )

            # Now generate image with story context for richer visual details
            prompt = self.storyteller.compose_prompt(
                activity, profile, weather, state.mood, features,
                story_text=story,
            )
            api_type = "seedream" if profile.image_api_key else None
            image_gen = get_image_generator(api_type=api_type, api_key=profile.image_api_key)
            image_path = image_gen.generate(prompt, profile.reference_photos or [])
            image_path = image_path.replace("\\", "/")

            # Move generated image to user-scoped directory
            from pathlib import Path
            import shutil
            src = Path(image_path)
            user_gen_dir = Path("data/generated") / str(user_id)
            user_gen_dir.mkdir(parents=True, exist_ok=True)
            dst = user_gen_dir / src.name
            if src != dst and src.exists():
                shutil.move(str(src), str(dst))
            image_path = str(dst).replace("\\", "/")

            # Persist updated memory
            save_memory(user_id, profile, features, all_stories + [story])
            new_mood = self.state_machine.update_mood(state.mood, activity.name)

            log_entry = JourneyLog(
                user_id=user_id,
                location_id=next_location.id, activity_id=activity.id,
                story_text=story, image_path=image_path,
                weather=weather, mood=new_mood, generated_at=datetime.now(),
            )
            sess.add(log_entry)
            sess.flush()

            state.current_location_id = next_location.id
            state.mood = new_mood
            state.day_number += 1
            state.weather_today = weather
            state.last_activity_id = activity.id

            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

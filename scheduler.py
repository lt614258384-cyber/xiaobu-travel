import random
from datetime import datetime, time, timedelta
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
            next_location = self.state_machine.select_next_location(state, profile)
            activity = self.state_machine.select_activity(next_location, profile)
            if not activity:
                session.close()
                return

            prompt = self.storyteller.compose_prompt(activity, profile, weather, state.mood)
            image_gen = get_image_generator()
            image_path = image_gen.generate(prompt, profile.reference_photos or [])
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

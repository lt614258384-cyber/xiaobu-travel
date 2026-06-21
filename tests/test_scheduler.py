from datetime import datetime, time
from unittest.mock import MagicMock, patch
from scheduler import Scheduler


class TestScheduler:
    def test_shutdown_stops_running_scheduler_without_waiting(self):
        scheduler = Scheduler()
        scheduler._aps = MagicMock()
        scheduler._aps.running = True

        scheduler.shutdown()

        scheduler._aps.shutdown.assert_called_once_with(wait=False)

    def test_shutdown_is_safe_when_scheduler_is_not_running(self):
        scheduler = Scheduler()
        scheduler._aps = MagicMock()
        scheduler._aps.running = False

        scheduler.shutdown()

        scheduler._aps.shutdown.assert_not_called()

    def test_generate_daily_times_count(self):
        for _ in range(50):
            times = Scheduler._generate_daily_times()
            assert 1 <= len(times) <= 3

    def test_generated_times_in_valid_hours(self):
        for _ in range(20):
            times = Scheduler._generate_daily_times()
            for t in times:
                valid = (6 <= t.hour <= 9) or (10 <= t.hour <= 12) or \
                        (14 <= t.hour <= 17) or (20 <= t.hour <= 22)
                assert valid, f"Hour {t.hour} invalid"

    def test_gap_at_least_4_hours(self):
        for _ in range(30):
            times = sorted(Scheduler._generate_daily_times())
            for i in range(len(times) - 1):
                gap = (datetime.combine(datetime.today(), times[i + 1]) -
                       datetime.combine(datetime.today(), times[i])).seconds / 3600
                assert gap >= 4

from unittest.mock import MagicMock, patch
from engine.state_machine import StateMachine


class TestStateMachine:
    def setup_method(self):
        self.sm = StateMachine()

    def test_roll_weather_returns_valid(self):
        for _ in range(20):
            assert self.sm.roll_weather() in ["晴", "多云", "小雨", "彩虹"]

    def test_roll_weather_distribution(self):
        results = {"晴": 0, "多云": 0, "小雨": 0, "彩虹": 0}
        for _ in range(1000):
            results[self.sm.roll_weather()] += 1
        assert results["晴"] > 350
        assert results["多云"] > 200

    def test_select_next_location_from_adjacent(self):
        state = MagicMock()
        state.current_location_id = 1
        loc_a, loc_b, loc_c = MagicMock(), MagicMock(), MagicMock()
        loc_a.id, loc_a.adjacent_locations = 1, [2, 3]
        loc_b.id, loc_b.name = 2, "B"
        loc_c.id, loc_c.name = 3, "C"

        with patch("engine.state_machine.get_session") as mock_sess:
            mock_db = MagicMock()
            mock_sess.return_value = mock_db
            mock_db.get.side_effect = lambda m, id: {1: loc_a, 2: loc_b, 3: loc_c}[id]
            for _ in range(50):
                result = self.sm.select_next_location(state, None)
                assert result.id in [2, 3]

    def test_select_activity_from_pool(self):
        loc = MagicMock()
        act1, act2 = MagicMock(), MagicMock()
        act1.name, act2.name = "running", "sleeping"
        loc.activities = [act1, act2]
        results = set()
        for _ in range(50):
            results.add(self.sm.select_activity(loc, None).name)
        assert "running" in results and "sleeping" in results

    def test_update_mood_changes(self):
        moods = set()
        for _ in range(30):
            moods.add(self.sm.update_mood("开心", "exploring"))
        assert len(moods) >= 2

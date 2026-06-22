import random
from models import get_session, Location, Activity, JourneyState, Profile
from sqlalchemy.sql.expression import func


class StateMachine:
    WEATHER_WEIGHTS = [("晴", 50), ("多云", 30), ("小雨", 15), ("彩虹", 5)]
    MOODS = ["开心", "兴奋", "平静", "好奇", "不舍", "满足", "期待"]
    EXPLORATION_TAGS = {"好动", "爱探险", "好奇", "勇敢", "精力旺盛"}
    GOURMET_TAGS = {"贪吃", "爱吃", "美食家"}
    SOCIAL_TAGS = {"亲人", "爱社交", "友善", "热情"}
    COZY_TAGS = {"安静", "宅", "温柔", "胆小"}

    def roll_weather(self) -> str:
        options, weights = zip(*self.WEATHER_WEIGHTS)
        return random.choices(options, weights=weights, k=1)[0]

    def select_next_location(self, state: JourneyState, profile: Profile = None, session=None) -> Location:
        close_session = False
        if session is None:
            session = get_session()
            close_session = True

        current_loc = session.get(Location, state.current_location_id)
        if not current_loc or not current_loc.adjacent_locations:
            if close_session:
                session.close()
            return current_loc

        adj_ids = current_loc.adjacent_locations
        adj_locations = [session.get(Location, lid) for lid in adj_ids]
        adj_locations = [loc for loc in adj_locations if loc is not None]

        if not adj_locations:
            if close_session:
                session.close()
            return current_loc

        # Region fatigue: check last 3 visits, force jump if all in same region
        current_region_id = current_loc.region_id if current_loc else None
        force_jump = False
        if current_region_id and state and state.user_id:
            from models import JourneyLog as JL
            recent_logs = session.query(JL).filter_by(user_id=state.user_id)\
                .order_by(JL.id.desc()).limit(3).all()
            if len(recent_logs) >= 3:
                recent_locs = [session.get(Location, l.location_id) for l in recent_logs]
                recent_regions = [l.region_id for l in recent_locs if l]
                if all(r == current_region_id for r in recent_regions):
                    force_jump = True

        # Jump: 20% random chance, or forced after 3 same-region visits
        if force_jump or random.random() < 0.20:
            all_locations = session.query(Location).order_by(func.random()).limit(20).all()
            other_regions = [loc for loc in all_locations if loc.region_id != current_region_id]
            if other_regions:
                if close_session:
                    session.close()
                return random.choice(other_regions)

        weights = self._calculate_weights(adj_locations, profile)
        chosen = random.choices(adj_locations, weights=weights, k=1)[0]
        if close_session:
            session.close()
        return chosen

        weights = self._calculate_weights(adj_locations, profile)
        chosen = random.choices(adj_locations, weights=weights, k=1)[0]
        if close_session:
            session.close()
        return chosen

    def _calculate_weights(self, locations: list[Location], profile: Profile = None) -> list[float]:
        weights = [1.0] * len(locations)
        if not profile or not profile.personality_tags:
            return weights
        tags = set(profile.personality_tags)
        for i, loc in enumerate(locations):
            region_name = loc.region.name if loc.region else ""
            if tags & self.EXPLORATION_TAGS and region_name in ["森林区", "山地区"]:
                weights[i] *= 1.5
            if tags & self.GOURMET_TAGS and ("美食" in loc.name or region_name == "小镇区"):
                weights[i] *= 1.5
            if tags & self.SOCIAL_TAGS and region_name in ["小镇区", "海滨区"]:
                weights[i] *= 1.3
            if tags & self.COZY_TAGS and region_name in ["原野区", "森林区"]:
                weights[i] *= 1.3
        return weights

    def select_activity(self, location: Location, profile: Profile = None) -> Activity:
        if location is None or not location.activities:
            return None
        return random.choice(list(location.activities))

    def update_mood(self, current_mood: str, activity_name: str) -> str:
        if random.random() < 0.7:
            return random.choice(["开心", "兴奋", "满足", "平静"])
        new_mood = random.choice(self.MOODS)
        while new_mood == current_mood and len(self.MOODS) > 1:
            new_mood = random.choice(self.MOODS)
        return new_mood

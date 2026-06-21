"""Seed the database with all locations, activities, and templates."""
from models import get_session, Region, Location, Activity, init_db
from seed.locations_data import REGIONS, CROSS_REGION_CONNECTIONS
from seed.activities_data import generate_activities


def seed():
    init_db()
    session = get_session()

    if session.query(Region).count() > 0:
        print("Database already seeded. Skipping.")
        session.close()
        return

    location_map = {}
    for region_data in REGIONS:
        region = Region(name=region_data["name"], description=region_data["description"])
        session.add(region)
        session.flush()

        loc_names = [l[0] for l in region_data["locations"]]
        for i, (name, desc, atmosphere) in enumerate(region_data["locations"]):
            adj_names = []
            if i > 0:
                adj_names.append(loc_names[i - 1])
            if i < len(loc_names) - 1:
                adj_names.append(loc_names[i + 1])

            loc = Location(
                region_id=region.id,
                name=name,
                description=desc,
                atmosphere=atmosphere,
                adjacent_locations=adj_names,  # resolved to IDs below
            )
            session.add(loc)
            session.flush()
            location_map[name] = loc

    # Resolve adjacent names to IDs
    for region_data in REGIONS:
        loc_names = [l[0] for l in region_data["locations"]]
        for i, (name, desc, atmosphere) in enumerate(region_data["locations"]):
            adj_ids = []
            if i > 0:
                adj_ids.append(location_map[loc_names[i - 1]].id)
            if i < len(loc_names) - 1:
                adj_ids.append(location_map[loc_names[i + 1]].id)
            location_map[name].adjacent_locations = adj_ids

    # Add cross-region connections
    for from_name, to_name in CROSS_REGION_CONNECTIONS:
        if from_name in location_map and to_name in location_map:
            fl, tl = location_map[from_name], location_map[to_name]
            adj = list(fl.adjacent_locations or [])
            if tl.id not in adj:
                adj.append(tl.id)
                fl.adjacent_locations = adj
            adj2 = list(tl.adjacent_locations or [])
            if fl.id not in adj2:
                adj2.append(fl.id)
                tl.adjacent_locations = adj2

    session.flush()

    # Create activities
    all_activities = generate_activities()
    for loc_name, acts in all_activities.items():
        loc = location_map.get(loc_name)
        if not loc:
            continue
        for act_data in acts:
            activity = Activity(
                location_id=loc.id,
                name=act_data["name"],
                prompt_template=act_data["prompt_template"],
                captions=act_data["captions"],
                stories=act_data["stories"],
            )
            session.add(activity)

    session.commit()
    print(f"Seeded: {session.query(Region).count()} regions, "
          f"{session.query(Location).count()} locations, "
          f"{session.query(Activity).count()} activities")
    session.close()


if __name__ == "__main__":
    seed()

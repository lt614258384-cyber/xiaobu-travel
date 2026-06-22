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

    import random as _random
    _rng = _random.Random(42)  # fixed seed for reproducible mesh

    # ── Phase 1: compute mesh adjacency for ALL regions ──
    all_mesh_adj = {}  # {name: {neighbor_names}}
    for region_data in REGIONS:
        loc_names = [l[0] for l in region_data["locations"]]
        n = len(loc_names)
        mesh = {name: set() for name in loc_names}
        for i in range(n):
            # Ring: i-2, i-1, i+1, i+2 (wrapping)
            for offset in [-2, -1, 1, 2]:
                j = (i + offset) % n
                if j != i:
                    mesh[loc_names[i]].add(loc_names[j])
        # 2-4 extra random cross-connections per location
        for i in range(n):
            pool = [name for j, name in enumerate(loc_names) if j != i and name not in mesh[loc_names[i]]]
            extra = _rng.sample(pool, min(_rng.randint(2, 4), len(pool)))
            for name in extra:
                mesh[loc_names[i]].add(name)
                mesh[name].add(loc_names[i])
        all_mesh_adj.update(mesh)

    # ── Phase 2: create regions + locations ──
    location_map = {}
    for region_data in REGIONS:
        region = Region(name=region_data["name"], description=region_data["description"])
        session.add(region)
        session.flush()

        for name, desc, atmosphere in region_data["locations"]:
            loc = Location(
                region_id=region.id,
                name=name,
                description=desc,
                atmosphere=atmosphere,
                adjacent_locations=sorted(all_mesh_adj.get(name, [])),
            )
            session.add(loc)
            session.flush()
            location_map[name] = loc

    # ── Phase 3: resolve adjacency names to IDs ──
    for name, adj_names in all_mesh_adj.items():
        if name in location_map:
            location_map[name].adjacent_locations = [
                location_map[n].id for n in adj_names if n in location_map
            ]

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

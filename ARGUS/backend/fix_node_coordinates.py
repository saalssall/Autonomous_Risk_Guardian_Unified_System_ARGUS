"""
One-off fix: existing nodes in argus.db are sitting at whatever coordinates
they got created with (often (0.0, 0.0) — Null Island — from the bug in
ingest_image, or otherwise scattered). This clusters every existing node
around Brisbane, QLD, with a small offset per node so they don't all render
as a single overlapping marker on the map.

Run once from the backend/ folder, with the same venv you run main.py in:
    python fix_node_coordinates.py
"""
import database

# Brisbane, QLD
BASE_LATITUDE = -27.4698
BASE_LONGITUDE = 153.0251

# ~0.003 degrees ≈ 300m — enough to visually separate markers on the map
# without scattering them across the city.
OFFSET_STEP = 0.003


def main():
    db = database.SessionLocal()
    try:
        nodes = db.query(database.NodeModel).all()
        if not nodes:
            print("No nodes found in the database.")
            return

        for i, node in enumerate(nodes):
            # Spread nodes out in a small ring so they don't stack exactly —
            # simple offset pattern, good enough for a handful of demo nodes.
            angle_offset = i * OFFSET_STEP
            node.latitude = BASE_LATITUDE + angle_offset
            node.longitude = BASE_LONGITUDE + angle_offset
            print(f"{node.node_id}: -> ({node.latitude}, {node.longitude})")

        db.commit()
        print(f"\nUpdated {len(nodes)} node(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
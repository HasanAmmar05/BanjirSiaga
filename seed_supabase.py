import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(".env.local")

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env.local")
    exit(1)

supabase: Client = create_client(url, key)
DATA_DIR = Path(__file__).parent / "data"

def seed_evacuation_centres():
    print("Seeding Evacuation Centres...")
    with open(DATA_DIR / "evacuation_centres.json", "r", encoding="utf-8") as f:
        centres = json.load(f)
    
    formatted_data = []
    for c in centres:
        formatted_data.append({
            "name": c["name"],
            "district": c.get("district", "Unknown"),
            "state": c.get("state", "Kuala Lumpur"),
            "capacity": c.get("capacity", 500),
            "active": c.get("active", False),
            "lat": c["lat"],
            "lon": c["lon"],
            # PostGIS geography point format: POINT(lon lat)
            "location": f"POINT({c['lon']} {c['lat']})"
        })
    
    # Clear existing
    supabase.table("evacuation_centres").delete().neq("id", 0).execute()
    # Insert new
    supabase.table("evacuation_centres").insert(formatted_data).execute()
    print(f"✅ Inserted {len(formatted_data)} evacuation centres.")

def seed_flood_history():
    print("Seeding Flood History...")
    with open(DATA_DIR / "flood_history.json", "r", encoding="utf-8") as f:
        history = json.load(f)
    
    formatted_data = []
    for key, data in history.items():
        events_list = data.get("events", [])
        num_events = len(events_list)
        last_date = data.get("last_flood_date")
        if not last_date and events_list:
            last_date = events_list[0].get("date")

        formatted_data.append({
            "area_name": data["area_name"],
            "events": num_events,
            "risk_rating": data["risk_rating"],
            "last_flood_date": last_date,
            "postcode": data.get("postcode", "")
        })
    
    supabase.table("flood_history").delete().neq("id", 0).execute()
    supabase.table("flood_history").insert(formatted_data).execute()
    print(f"✅ Inserted {len(formatted_data)} historical flood records.")

if __name__ == "__main__":
    try:
        seed_evacuation_centres()
        seed_flood_history()
        print("🎉 Database successfully seeded!")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")

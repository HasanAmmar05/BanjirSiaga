from supabase import create_client, Client
from app.core.config import settings
import math

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_nearest_evacuation_centres(lat: float, lon: float, count: int = 3) -> list:
    """
    Fetch nearest evacuation centres using PostGIS ST_Distance.
    """
    try:
        # Note: We use an RPC call if we created a custom Postgres function,
        # but for simplicity, we can fetch active centres and calculate haversine in Python
        # if the user hasn't created a specific RPC yet.
        # Once RPC is set up:
        # response = supabase.rpc("get_nearest_centres", {"user_lat": lat, "user_lon": lon, "limit_count": count}).execute()
        
        # Fallback to fetching all active centres and doing local haversine if RPC doesn't exist
        # This is safe because there are only a few hundred centres.
        response = supabase.table("evacuation_centres").select("*").eq("active", True).execute()
        centres = response.data
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return R * c

        centres_with_dist = []
        for centre in centres:
            dist = haversine(lat, lon, centre["lat"], centre["lon"])
            centres_with_dist.append({**centre, "distance_km": round(dist, 1)})

        centres_with_dist.sort(key=lambda x: x["distance_km"])
        return centres_with_dist[:count]
    except Exception as e:
        print(f"Error fetching from Supabase: {e}")
        return []

def get_flood_history(location: str) -> dict:
    """Fetch flood history for a specific location."""
    try:
        # Try direct or ilike matching
        # Note: ilike is supported by Supabase for case-insensitive matching
        response = supabase.table("flood_history").select("*").ilike("area_name", f"%{location}%").execute()
        if response.data:
            return response.data[0]
            
        # Check by postcode
        response = supabase.table("flood_history").select("*").ilike("postcode", f"%{location.strip()}%").execute()
        if response.data:
            return response.data[0]
            
        return None
    except Exception as e:
        print(f"Error fetching flood history: {e}")
        return None

import httpx
from datetime import datetime, timezone, timedelta

MYT = timezone(timedelta(hours=8))

async def fetch_open_meteo(lat: float, lon: float) -> dict:
    """Fetch current weather data from Open-Meteo API."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=rain,precipitation,weather_code,temperature_2m,relative_humidity_2m,wind_speed_10m,cloud_cover"
        f"&hourly=precipitation_probability"
        f"&timezone=Asia/Kuala_Lumpur"
        f"&forecast_days=1"
    )
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    # Get precipitation probability for next 3 hours
    precip_probs = hourly.get("precipitation_probability", [])
    now_hour = datetime.now(MYT).hour
    next_3hr_probs = precip_probs[now_hour:now_hour + 3] if precip_probs else []
    avg_precip_prob = sum(next_3hr_probs) / len(next_3hr_probs) if next_3hr_probs else 0

    return {
        "current_rain_mm": current.get("rain", 0),
        "precipitation_mm": current.get("precipitation", 0),
        "precipitation_probability_3hr": round(avg_precip_prob),
        "temperature_c": current.get("temperature_2m", 0),
        "humidity_pct": current.get("relative_humidity_2m", 0),
        "wind_speed_kmh": current.get("wind_speed_10m", 0),
        "cloud_cover_pct": current.get("cloud_cover", 0),
        "weather_code": current.get("weather_code", 0),
    }

async def fetch_warnings() -> list:
    """Fetch active weather warnings from data.gov.my."""
    try:
        url = "https://api.data.gov.my/weather/warning"
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            data = resp.json()

        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

async def geocode_location(query: str) -> dict:
    """Geocode a location query using Nominatim (OpenStreetMap)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{query}, Malaysia",
        "format": "json",
        "limit": 1,
        "countrycodes": "my",
    }
    headers = {"User-Agent": "BanjirSiaga/1.0 (production migration)"}
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(url, params=params, headers=headers)
        resp.raise_for_status()
        results = resp.json()

    if not results:
        return None

    result = results[0]
    return {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "display_name": result.get("display_name", query),
    }

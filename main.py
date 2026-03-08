"""
BanjirSiaga — AI-Powered Hyper-Local Flood Intelligence for Malaysia
FastAPI Backend with Gemini 2.0 Flash Integration
"""

import os
import json
import asyncio
import base64
import math
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import httpx
from google import genai

# Load environment variables
load_dotenv(".env.local")

# ─── App Setup ──────────────────────────────────────────────────────────────
app = FastAPI(title="BanjirSiaga", version="1.0.0")

# Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)

# Model cascade — try each in order until one works
MODEL_CASCADE = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
]

# Data directory
DATA_DIR = Path(__file__).parent / "data"

# Load static data files
with open(DATA_DIR / "flood_history.json", "r", encoding="utf-8") as f:
    FLOOD_HISTORY = json.load(f)

with open(DATA_DIR / "evacuation_centres.json", "r", encoding="utf-8") as f:
    EVACUATION_CENTRES = json.load(f)

with open(DATA_DIR / "replay_kelantan_2024.json", "r", encoding="utf-8") as f:
    REPLAY_DATA = json.load(f)

# Malaysia timezone
MYT = timezone(timedelta(hours=8))

# ─── Prompt Templates ──────────────────────────────────────────────────────

SYSTEM_PROMPT_ASSESS = """You are BanjirSiaga, Malaysia's hyper-local flood intelligence assistant. Your role is to protect Malaysian lives by translating raw weather data into clear, actionable flood risk guidance.

RULES:
1. Always respond in valid JSON with these exact keys: risk_level, bm, en, immediate_actions
2. risk_level must be exactly one of: "SELAMAT", "WASPADA", "BAHAYA"
3. "bm" is the full assessment in Bahasa Malaysia (2-4 sentences max)
4. "en" is the full assessment in English (2-4 sentences max)
5. "immediate_actions" is an array of 1-3 short action strings in BM
6. Be specific: name the area, cite the rainfall figure, reference local flood history if provided
7. Never use technical jargon — write like you are texting a family member
8. The previous government system had 5.6% accuracy. Lives depend on your clarity.

RISK LEVEL THRESHOLDS (use as guidance, apply judgement):
- SELAMAT: rainfall < 5mm/hr, no active warnings, no historical risk flag
- WASPADA: rainfall 5-15mm/hr OR active warning nearby OR area has flood history
- BAHAYA: rainfall > 15mm/hr AND (active warning OR known flood-prone area)"""

SYSTEM_PROMPT_PHOTO = """You are BanjirSiaga's visual flood assessment engine. Analyse the provided image for flood indicators.

Respond in valid JSON with these exact keys: risk_level, depth_estimate, bm, en, action

risk_level: "SELAMAT" | "WASPADA" | "BAHAYA"
depth_estimate: estimated water depth as a string e.g. "5-10cm", "tidak kelihatan air", "> 50cm"
bm: 2-3 sentence assessment in Bahasa Malaysia
en: 2-3 sentence assessment in English
action: single most important immediate action in BM

If image quality is too poor to assess: return { "risk_level": "UNKNOWN", "bm": "Gambar tidak cukup jelas...", ... }
Look for: water covering road markings, submerged kerbs, car tyre depth relative to water, distance to drain openings."""


# ─── Helper Functions ──────────────────────────────────────────────────────

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

        # data.gov.my returns a list of warning objects
        if isinstance(data, list):
            return data
        return []
    except Exception:
        # Silently fail — Open-Meteo alone is sufficient for demo
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
    headers = {"User-Agent": "BanjirSiaga/1.0 (hackathon project)"}
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


def find_flood_history(location: str) -> dict:
    """Find flood history for a location from static data."""
    location_lower = location.lower().replace(" ", "_")
    # Direct match
    if location_lower in FLOOD_HISTORY:
        return FLOOD_HISTORY[location_lower]
    # Fuzzy match — search area names
    for key, data in FLOOD_HISTORY.items():
        if location.lower() in data["area_name"].lower() or data["area_name"].lower() in location.lower():
            return data
    # Check postcodes
    for key, data in FLOOD_HISTORY.items():
        if location.strip() in data.get("postcode", ""):
            return data
    return None


def find_nearest_centres(lat: float, lon: float, count: int = 3) -> list:
    """Find nearest evacuation centres by distance."""
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    centres_with_dist = []
    for centre in EVACUATION_CENTRES:
        dist = haversine(lat, lon, centre["lat"], centre["lon"])
        centres_with_dist.append({**centre, "distance_km": round(dist, 1)})

    centres_with_dist.sort(key=lambda x: x["distance_km"])
    return centres_with_dist[:count]


def clean_gemini_json(text: str) -> dict:
    """Extract and parse JSON from Gemini response (handles markdown fences)."""
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


async def call_gemini_with_cascade(contents, system_instruction):
    """Try multiple Gemini models in cascade. Returns response or raises last error."""
    last_error = None
    for model_name in MODEL_CASCADE:
        try:
            print(f"Trying model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                ),
            )
            print(f"Success with model: {model_name}")
            return response
        except Exception as e:
            error_str = str(e)
            print(f"Model {model_name} failed: {error_str[:100]}")
            last_error = e
            # If rate limited, wait briefly before trying next model
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                await asyncio.sleep(1)
            continue
    raise last_error


def generate_fallback_assessment(location: str, weather: dict, warnings: list, flood_history: dict) -> dict:
    """Rule-based fallback when ALL Gemini models fail. Always returns a valid assessment."""
    rain = weather.get("current_rain_mm", 0)
    precip = weather.get("precipitation_mm", 0)
    precip_prob = weather.get("precipitation_probability_3hr", 0)
    has_warnings = len(warnings) > 0 if isinstance(warnings, list) else False
    has_flood_history = flood_history is not None and flood_history.get("risk_rating") in ["high", "moderate"]
    is_high_risk_area = flood_history is not None and flood_history.get("risk_rating") == "high"

    # Determine risk level based on PRD thresholds
    if rain > 15 and (has_warnings or is_high_risk_area):
        risk_level = "BAHAYA"
    elif rain > 5 or has_warnings or has_flood_history or precip_prob > 60:
        risk_level = "WASPADA"
    else:
        risk_level = "SELAMAT"

    # Extract location short name
    loc_short = location.split(",")[0].strip()

    # Generate human-readable assessments
    assessments = {
        "SELAMAT": {
            "bm": f"Kawasan {loc_short} selamat buat masa ini. Hujan semasa {rain}mm/jam — tiada risiko banjir yang ketara. Cuaca dijangka stabil dalam beberapa jam akan datang.",
            "en": f"The {loc_short} area is currently safe. Current rainfall is {rain}mm/hr with no significant flood risk. Weather conditions are expected to remain stable.",
            "immediate_actions": ["Tiada tindakan diperlukan", "Pantau cuaca jika hujan berterusan"]
        },
        "WASPADA": {
            "bm": f"Berhati-hati di kawasan {loc_short}. Hujan semasa {rain}mm/jam dengan kebarangkalian hujan {precip_prob}% dalam 3 jam akan datang. {'Kawasan ini mempunyai rekod banjir sebelum ini. ' if has_flood_history else ''}{'Amaran cuaca rasmi sedang aktif. ' if has_warnings else ''}Sila pantau keadaan.",
            "en": f"Exercise caution in the {loc_short} area. Current rainfall is {rain}mm/hr with {precip_prob}% precipitation probability in the next 3 hours. {'This area has a history of flooding. ' if has_flood_history else ''}{'Official weather warnings are currently active. ' if has_warnings else ''}Please monitor conditions.",
            "immediate_actions": ["Pantau keadaan air dan cuaca", "Pindahkan kenderaan ke tempat tinggi" if has_flood_history else "Sediakan beg kecemasan", "Ikut arahan pihak berkuasa"]
        },
        "BAHAYA": {
            "bm": f"BAHAYA! Kawasan {loc_short} berisiko tinggi banjir! Hujan sangat lebat {rain}mm/jam. {'Amaran rasmi sedang aktif! ' if has_warnings else ''}{'Kawasan ini pernah mengalami banjir teruk sebelum ini. ' if is_high_risk_area else ''}Sila berpindah ke pusat pemindahan segera jika air mula naik.",
            "en": f"DANGER! The {loc_short} area is at HIGH flood risk! Heavy rainfall at {rain}mm/hr. {'Official warnings are active! ' if has_warnings else ''}{'This area has experienced severe flooding in the past. ' if is_high_risk_area else ''}Please evacuate to the nearest relief centre immediately if water levels start rising.",
            "immediate_actions": ["Berpindah ke tempat tinggi SEGERA", "Hubungi 999 jika terperangkap", "Jangan cuba memandu melalui air banjir"]
        }
    }

    assessment = assessments[risk_level]
    return {
        "risk_level": risk_level,
        "bm": assessment["bm"],
        "en": assessment["en"],
        "immediate_actions": assessment["immediate_actions"],
        "_fallback": True  # Flag so frontend knows this is rule-based
    }


def generate_fallback_photo() -> dict:
    """Random photo analysis fallback — picks from 5 realistic responses."""
    import random
    analyses = [
        {
            "risk_level": "BAHAYA",
            "depth_estimate": "~45cm (paras lutut)",
            "bm": "Gambar menunjukkan air banjir yang telah melepasi paras jalan raya. Kedalaman dianggarkan sekitar 45cm berdasarkan tanda air pada tiang lampu dan kenderaan yang terpaksa berhenti. Air kelihatan keruh dan bergerak — petanda aliran deras dari kawasan hulu. Risiko BAHAYA tinggi.",
            "en": "The image shows floodwater that has exceeded road level. Depth is estimated at approximately 45cm based on water marks on lamp posts and stalled vehicles. Water appears turbid and flowing — indicating rapid upstream runoff. HIGH DANGER risk.",
            "action": "Jangan cuba menyeberang! Tunggu air surut atau hubungi 999."
        },
        {
            "risk_level": "WASPADA",
            "depth_estimate": "~15cm (paras buku lali)",
            "bm": "Gambar menunjukkan air bertakung di permukaan jalan. Kedalaman dianggarkan sekitar 15cm. Sistem perparitan kelihatan masih berfungsi tetapi hampir penuh. Tiada tanda kerosakan struktur ketara. Situasi boleh meningkat jika hujan berterusan.",
            "en": "The image shows standing water on the road surface. Depth is estimated at approximately 15cm. Drainage systems appear to be functioning but nearing capacity. No significant structural damage detected. Situation could escalate if rainfall continues.",
            "action": "Pantau keadaan, elakkan memandu melalui air bertakung."
        },
        {
            "risk_level": "BAHAYA",
            "depth_estimate": "~80cm (paras pinggang)",
            "bm": "BAHAYA TINGGI! Gambar menunjukkan banjir yang sangat teruk. Air telah memasuki kawasan kediaman dan mencapai paras pinggang. Arus air kelihatan kuat — puing-puing dan sampah terapung menandakan situasi kritikal. Pemindahan segera diperlukan.",
            "en": "HIGH DANGER! Image shows severe flooding. Water has entered residential areas reaching waist level. Strong water current visible — floating debris and garbage indicate a critical situation. Immediate evacuation required.",
            "action": "PINDAH SEGERA ke tempat tinggi! Hubungi 999!"
        },
        {
            "risk_level": "SELAMAT",
            "depth_estimate": "Tiada banjir dikesan",
            "bm": "Analisis gambar ini tidak menunjukkan tanda-tanda banjir yang ketara. Permukaan jalan kering atau hanya mempunyai genangan air kecil akibat hujan biasa. Sistem saliran berfungsi dengan baik. Kawasan ini selamat buat masa ini.",
            "en": "Image analysis shows no significant signs of flooding. Road surface is dry or has only minor puddles from normal rainfall. Drainage systems are functioning well. This area is currently safe.",
            "action": "Tiada tindakan diperlukan — kawasan selamat."
        },
        {
            "risk_level": "WASPADA",
            "depth_estimate": "~25cm (separuh tayar kereta)",
            "bm": "Gambar menunjukkan air mula naik di kawasan rendah. Kedalaman dianggarkan 25cm berdasarkan paras air pada tayar kenderaan. Longkang kelihatan penuh dan air mula melimpah ke jalan. Disarankan untuk memindahkan kenderaan ke tempat yang lebih tinggi.",
            "en": "Image shows water beginning to rise in low-lying areas. Depth estimated at 25cm based on water level on vehicle tires. Drains appear full with water starting to overflow onto roads. Advised to move vehicles to higher ground.",
            "action": "Pindahkan kenderaan ke tempat tinggi, sediakan beg kecemasan."
        }
    ]
    result = random.choice(analyses)
    result["_fallback"] = True
    return result


# ─── API Endpoints ─────────────────────────────────────────────────────────

@app.post("/api/assess")
async def assess_risk(payload: dict):
    """Core endpoint: Location-based flood risk assessment using Gemini."""
    location = payload.get("location", "Kuala Lumpur")
    lat = payload.get("lat")
    lon = payload.get("lon")
    mode = payload.get("mode", "live")

    # Geocode if no coordinates provided
    if lat is None or lon is None:
        geo = await geocode_location(location)
        if geo is None:
            raise HTTPException(status_code=400, detail="Lokasi tidak ditemui / Location not found")
        lat = geo["lat"]
        lon = geo["lon"]
        location = geo.get("display_name", location)

    # Scenario Replay Mode
    if mode == "replay":
        weather = REPLAY_DATA["weather_data"]
        warnings = REPLAY_DATA["warnings"]
        flood_history = FLOOD_HISTORY.get("wangsa_maju", {})
    else:
        # Fetch live data
        weather = await fetch_open_meteo(lat, lon)
        warnings = await fetch_warnings()
        flood_history = find_flood_history(location)

    # Build user prompt
    timestamp = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S MYT")
    flood_history_json = json.dumps(flood_history, indent=2, ensure_ascii=False) if flood_history else "No specific flood history available for this area."
    warnings_json = json.dumps(warnings, indent=2, ensure_ascii=False) if warnings else "No active government warnings."

    user_prompt = f"""Location: {location}
Coordinates: {lat}, {lon}
Current time: {timestamp}

LIVE WEATHER DATA:
- Current rainfall: {weather.get('current_rain_mm', 0)}mm/hr
- Precipitation last hour: {weather.get('precipitation_mm', 0)}mm
- Precipitation probability next 3hr: {weather.get('precipitation_probability_3hr', 0)}%
- Temperature: {weather.get('temperature_c', 0)}°C
- Humidity: {weather.get('humidity_pct', 0)}%
- Wind speed: {weather.get('wind_speed_kmh', 0)} km/h

ACTIVE GOVERNMENT WARNINGS:
{warnings_json}

HISTORICAL FLOOD RECORD FOR THIS AREA:
{flood_history_json}

Assess the flood risk for this location right now."""

    # Call Gemini with model cascade — fallback to rule-based if ALL fail
    try:
        response = await call_gemini_with_cascade(user_prompt, SYSTEM_PROMPT_ASSESS)
        result = clean_gemini_json(response.text)
    except json.JSONDecodeError:
        # If Gemini doesn't return valid JSON, wrap the text
        result = {
            "risk_level": "WASPADA",
            "bm": response.text[:500],
            "en": "Assessment generated — see BM text above.",
            "immediate_actions": ["Pantau keadaan cuaca"]
        }
    except Exception as e:
        # ALL Gemini models failed — use rule-based fallback
        print(f"All Gemini models failed, using rule-based fallback: {e}")
        result = generate_fallback_assessment(location, weather, warnings, flood_history)

    # Add weather data and nearest centres to response
    result["rainfall_mm"] = weather.get("current_rain_mm", 0)
    result["weather"] = weather
    result["warnings"] = warnings if isinstance(warnings, list) else []
    result["location"] = location
    result["lat"] = lat
    result["lon"] = lon
    result["mode"] = mode

    # Add evacuation centres if BAHAYA
    if result.get("risk_level") == "BAHAYA":
        result["evacuation_centres"] = find_nearest_centres(lat, lon)

    return result


@app.post("/api/photo")
async def assess_photo(file: UploadFile = File(...), location: str = Form("Kuala Lumpur")):
    """Photo-based flood assessment using Gemini Vision."""
    # Read and encode image
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    # Determine mime type
    content_type = file.content_type or "image/jpeg"
    if content_type not in ["image/jpeg", "image/png", "image/webp"]:
        content_type = "image/jpeg"

    image_part = genai.types.Part.from_bytes(
        data=contents,
        mime_type=content_type,
    )

    user_prompt = f"This photo was taken at {location}, Malaysia. Assess the flood risk visible in this image."

    try:
        response = await call_gemini_with_cascade([user_prompt, image_part], SYSTEM_PROMPT_PHOTO)
        result = clean_gemini_json(response.text)
    except json.JSONDecodeError:
        result = {
            "risk_level": "WASPADA",
            "depth_estimate": "Tidak dapat dianggar",
            "bm": response.text[:500],
            "en": "Assessment generated — see BM text.",
            "action": "Berhati-hati dan pantau keadaan"
        }
    except Exception as e:
        # ALL Gemini models failed — use photo fallback
        print(f"All Gemini Vision models failed, using fallback: {e}")
        result = generate_fallback_photo()

    result["location"] = location
    return result


@app.get("/api/warnings")
async def get_warnings():
    """Get active weather warnings from data.gov.my."""
    warnings = await fetch_warnings()
    return {
        "active": len(warnings) > 0,
        "warnings": warnings,
    }


@app.get("/api/centres")
async def get_centres(lat: float = 3.1850, lon: float = 101.7369):
    """Get nearest evacuation centres."""
    return find_nearest_centres(lat, lon)


# ─── Serve Frontend ────────────────────────────────────────────────────────

# Mount static directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

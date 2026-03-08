from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
import json
from datetime import datetime, timezone, timedelta
from app.schemas.assessment import AssessRequest, AssessmentResponseSchema, PhotoAssessmentResponseSchema
from app.services.weather import fetch_open_meteo, fetch_warnings, geocode_location
from app.services.db import get_nearest_evacuation_centres, get_flood_history
from app.services.gemini import call_gemini_cascade, generate_fallback_assessment, generate_fallback_photo, SYSTEM_PROMPT_ASSESS, SYSTEM_PROMPT_PHOTO
from app.services.groq_api import call_groq_fallback

from google import genai
import os
from pathlib import Path

# Load static replay data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
with open(DATA_DIR / "replay_kelantan_2024.json", "r", encoding="utf-8") as f:
    REPLAY_DATA = json.load(f)

MYT = timezone(timedelta(hours=8))
router = APIRouter()

from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/assess")
@limiter.limit("5/minute")
async def assess_risk(request: Request, payload: AssessRequest):
    location = payload.location
    lat = payload.lat
    lon = payload.lon
    mode = payload.mode

    if lat is None or lon is None:
        geo = await geocode_location(location)
        if geo is None:
            raise HTTPException(status_code=400, detail="Location not found")
        lat = geo["lat"]
        lon = geo["lon"]
        location = geo.get("display_name", location)

    if mode == "replay":
        weather = REPLAY_DATA["weather_data"]
        warnings = REPLAY_DATA["warnings"]
        flood_history = {"risk_rating": "high"}
    else:
        weather = await fetch_open_meteo(lat, lon)
        warnings = await fetch_warnings()
        flood_history = get_flood_history(location)

    timestamp = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S MYT")
    flood_history_json = json.dumps(flood_history, ensure_ascii=False) if flood_history else "No history."
    warnings_json = json.dumps(warnings, ensure_ascii=False) if warnings else "No warnings."

    user_prompt = f"Location: {location}\nCoordinates: {lat}, {lon}\nCurrent time: {timestamp}\nWEATHER: {weather}\nWARNINGS: {warnings_json}\nHISTORY: {flood_history_json}\nAssess the flood risk for this location right now."

    try:
        # Pydantic schema enforced structurally
        result = await call_gemini_cascade(user_prompt, SYSTEM_PROMPT_ASSESS, AssessmentResponseSchema)
    except Exception as e:
        print(f"Gemini cascade failed: {e}. Falling back to Groq...")
        try:
            result = await call_groq_fallback(SYSTEM_PROMPT_ASSESS, user_prompt)
            result["_fallback_groq"] = True
        except Exception as groq_e:
            print(f"Groq fallback failed: {groq_e}. Falling back to rule-based.")
            result = generate_fallback_assessment(location, weather, warnings, flood_history)

    result["rainfall_mm"] = weather.get("current_rain_mm", 0)
    result["weather"] = weather
    result["warnings"] = warnings if isinstance(warnings, list) else []
    result["location"] = location
    result["lat"] = lat
    result["lon"] = lon
    result["mode"] = mode

    if result.get("risk_level") == "BAHAYA":
        result["evacuation_centres"] = get_nearest_evacuation_centres(lat, lon)

    return result

@router.post("/photo")
@limiter.limit("2/minute")
async def assess_photo(request: Request, file: UploadFile = File(...), location: str = Form("Kuala Lumpur")):
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    image_part = genai.types.Part.from_bytes(data=contents, mime_type=file.content_type or "image/jpeg")
    user_prompt = f"This photo was taken at {location}, Malaysia. Assess the flood risk visible in this image."

    try:
        result = await call_gemini_cascade([user_prompt, image_part], SYSTEM_PROMPT_PHOTO, PhotoAssessmentResponseSchema)
    except Exception as e:
        print(f"Fallback photo: {e}")
        result = generate_fallback_photo()

    result["location"] = location
    return result

@router.get("/warnings")
async def get_warnings_endpoint():
    warnings = await fetch_warnings()
    return {"active": len(warnings) > 0, "warnings": warnings}

@router.get("/centres")
async def get_centres_endpoint(lat: float = 3.1850, lon: float = 101.7369):
    return get_nearest_evacuation_centres(lat, lon)

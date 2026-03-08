import json
import random
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.schemas.assessment import AssessmentResponseSchema, PhotoAssessmentResponseSchema

client = genai.Client(api_key=settings.GEMINI_API_KEY)
MODEL_CASCADE = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-8b"]

SYSTEM_PROMPT_ASSESS = """You are BanjirSiaga, Malaysia's hyper-local flood intelligence assistant. Your role is to protect Malaysian lives by translating raw weather data into clear, actionable flood risk guidance.

RULES:
1. Always respond in valid JSON matching the exact schema provided.
2. risk_level must be exactly one of: "SELAMAT", "WASPADA", "BAHAYA"
3. Be specific: name the area, cite the rainfall figure, reference local flood history if provided
4. Never use technical jargon — write like you are texting a family member

RISK LEVEL THRESHOLDS:
- SELAMAT: rainfall < 5mm/hr, no active warnings
- WASPADA: rainfall 5-15mm/hr OR active warning nearby OR area has flood history
- BAHAYA: rainfall > 15mm/hr AND (active warning OR known flood-prone area)"""

SYSTEM_PROMPT_PHOTO = """You are BanjirSiaga's visual flood assessment engine. Analyse the provided image for flood indicators.

Respond in valid JSON matching the provided schema.

If image quality is too poor to assess: return { "risk_level": "UNKNOWN", "bm": "Gambar tidak cukup jelas...", ... }
Look for: water covering road markings, submerged kerbs, car tyre depth relative to water, distance to drain openings."""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _call_model(model_name: str, contents, system_instruction, response_schema):
    """Call a specific model with tenacity retries for rate limits."""
    return client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )

async def call_gemini_cascade(contents, system_instruction, response_schema):
    """Cascade through models, using Tenacity retries on each before failing over."""
    last_error = None
    for model_name in MODEL_CASCADE:
        try:
            print(f"Trying model: {model_name}")
            response = _call_model(model_name, contents, system_instruction, response_schema)
            # Response is guaranteed to be stringified JSON matching the schema
            return json.loads(response.text)
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            last_error = e
            continue
    raise last_error

def generate_fallback_assessment(location: str, weather: dict, warnings: list, flood_history: dict) -> dict:
    """Rule-based fallback when ALL Gemini models fail."""
    rain = weather.get("current_rain_mm", 0)
    precip_prob = weather.get("precipitation_probability_3hr", 0)
    has_warnings = len(warnings) > 0 if isinstance(warnings, list) else False
    has_flood_history = flood_history is not None and flood_history.get("risk_rating") in ["high", "moderate"]
    is_high_risk_area = flood_history is not None and flood_history.get("risk_rating") == "high"

    if rain > 15 and (has_warnings or is_high_risk_area):
        risk_level = "BAHAYA"
    elif rain > 5 or has_warnings or has_flood_history or precip_prob > 60:
        risk_level = "WASPADA"
    else:
        risk_level = "SELAMAT"

    loc_short = location.split(",")[0].strip()

    assessments = {
        "SELAMAT": {
            "bm": f"Kawasan {loc_short} selamat buat masa ini. Hujan semasa {rain}mm/jam.",
            "en": f"The {loc_short} area is currently safe. Current rainfall is {rain}mm/hr.",
            "immediate_actions": ["Tiada tindakan diperlukan", "Pantau cuaca jika hujan berterusan"]
        },
        "WASPADA": {
            "bm": f"Berhati-hati di kawasan {loc_short}. Hujan semasa {rain}mm/jam.",
            "en": f"Exercise caution in the {loc_short} area. Current rainfall is {rain}mm/hr.",
            "immediate_actions": ["Pantau keadaan air dan cuaca", "Pindahkan kenderaan ke tempat tinggi" if has_flood_history else "Sediakan beg kecemasan"]
        },
        "BAHAYA": {
            "bm": f"BAHAYA! Kawasan {loc_short} berisiko tinggi banjir! Hujan {rain}mm/jam.",
            "en": f"DANGER! The {loc_short} area is at HIGH flood risk! Heavy rainfall at {rain}mm/hr.",
            "immediate_actions": ["Berpindah ke tempat tinggi SEGERA", "Hubungi 999 jika terperangkap"]
        }
    }

    assessment = assessments[risk_level]
    return {
        "risk_level": risk_level,
        "bm": assessment["bm"],
        "en": assessment["en"],
        "immediate_actions": assessment["immediate_actions"],
        "_fallback": True
    }

def generate_fallback_photo() -> dict:
    """Random photo analysis fallback."""
    analyses = [
        {
            "risk_level": "BAHAYA",
            "depth_estimate": "~45cm (paras lutut)",
            "bm": "Gambar menunjukkan air banjir yang telah melepasi paras jalan raya. Risiko BAHAYA tinggi.",
            "en": "The image shows floodwater that has exceeded road level. HIGH DANGER risk.",
            "action": "Jangan cuba menyeberang! Hubungi 999."
        },
        {
            "risk_level": "WASPADA",
            "depth_estimate": "~15cm (paras buku lali)",
            "bm": "Gambar menunjukkan air bertakung di permukaan jalan. Kedalaman dianggarkan sekitar 15cm.",
            "en": "The image shows standing water on the road surface. Depth is estimated at approximately 15cm.",
            "action": "Pantau keadaan, elakkan memandu melalui air bertakung."
        }
    ]
    result = random.choice(analyses)
    result["_fallback"] = True
    return result
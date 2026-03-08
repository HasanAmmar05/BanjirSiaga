from pydantic import BaseModel, Field
from typing import List, Optional

class AssessRequest(BaseModel):
    location: str = Field(default="Kuala Lumpur", description="The string location name")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")
    mode: str = Field(default="live", description="'live' or 'replay'")

# Pydantic schema used by Gemini structured outputs to enforce JSON
class AssessmentResponseSchema(BaseModel):
    risk_level: str = Field(description="Must be exactly one of: SELAMAT, WASPADA, BAHAYA")
    bm: str = Field(description="2-4 sentence assessment in Bahasa Malaysia")
    en: str = Field(description="2-4 sentence assessment in English")
    immediate_actions: List[str] = Field(description="1-3 short action strings in BM")

class PhotoAssessmentResponseSchema(BaseModel):
    risk_level: str = Field(description="Must be exactly one of: SELAMAT, WASPADA, BAHAYA")
    depth_estimate: str = Field(description="Estimated water depth as a string e.g. '5-10cm', 'tidak kelihatan air', '> 50cm'")
    bm: str = Field(description="2-4 sentence assessment in Bahasa Malaysia")
    en: str = Field(description="2-4 sentence assessment in English")
    action: str = Field(description="Single most important immediate action in BM")

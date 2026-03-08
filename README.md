# BanjirSiaga

AI-Powered Hyper-Local Flood Intelligence for Malaysia.

Built with **Gemini 2.0 Flash**, **FastAPI**, and **Open-Meteo** + **data.gov.my** live data sources.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Open http://localhost:8000

## Deploy to Cloud Run

```bash
gcloud run deploy banjirsiaga \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here
```

## Features

- 🌧️ Real-time flood risk assessment by location
- 📸 Photo-based flood severity analysis (Gemini Vision)
- 🇲🇾 Bilingual — Bahasa Malaysia & English
- 🔄 Scenario replay mode for demo stability
- 🏥 Nearest evacuation centres
- ⚠️ Live government weather warnings

## Data Sources

- [Open-Meteo](https://open-meteo.com/) — Real-time weather (free, no key)
- [data.gov.my](https://developer.data.gov.my/) — Official Malaysian weather warnings (free, no key)
- Historical flood data — compiled from news and NADMA reports

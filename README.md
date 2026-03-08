<p align="center">
  <img src="https://img.shields.io/badge/🌊_BanjirSiaga-AI_Flood_Intelligence-0ea5e9?style=for-the-badge&labelColor=0a0e1a" alt="BanjirSiaga" />
</p>

<h1 align="center">
  🌊 BanjirSiaga
</h1>

<p align="center">
  <strong>AI-Powered Hyper-Local Flood Intelligence for Malaysia</strong><br/>
  <em>Protecting 33 million lives — one postcode at a time.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Gemini_2.0_Flash-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini 2.0" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python_3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Leaflet.js-199900?style=flat-square&logo=leaflet&logoColor=white" alt="Leaflet" />
  <img src="https://img.shields.io/badge/Cloud_Run-4285F4?style=flat-square&logo=googlecloud&logoColor=white" alt="Cloud Run" />
  <img src="https://img.shields.io/badge/🇲🇾_Bilingual-BM_&_EN-fbbf24?style=flat-square" alt="Bilingual" />
</p>

<p align="center">
  <a href="#-the-problem">The Problem</a> •
  <a href="#-our-solution">Our Solution</a> •
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-data-sources">Data Sources</a>
</p>

---

## 🚨 The Challenge

Malaysia faces complex flooding scenarios that require increasingly advanced technological solutions to manage:

| Metric | Challenge | Impact |
|--------|-----------|--------|
| 🌦️ Rapid Weather Changes | **Unpredictable** | Flash floods can occur with minimal warning signs |
| 📉 Forecast Granularity | **Often Broad** | State-level alerts may not reflect street-level reality |
| 🙈 Information Overload | **Reachability** | Critical alerts must compete with daily digital noise |
| 🏘️ Nationwide Scope | **All 16 States** | A crisis that affects the entire country |

> **The December 2021 KL flood** displaced **over 125,000 people** and caused **RM 6.1 billion** in damages. In areas like Taman Sri Muda, rapid water level rises engulfed entire homes in a matter of hours.

**BanjirSiaga exists to complement existing early-warning infrastructure by bringing real-time, AI-driven contextual insights directly to the people.**

---

## 💡 Our Solution

BanjirSiaga fuses **real-time multi-source data** with **Gemini 2.0 Flash AI reasoning** to deliver hyper-local, bilingual flood risk assessments that anyone can understand — in seconds, not hours.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Open-Meteo API │     │  data.gov.my     │     │  Historical Flood   │
│  (Live Weather) │     │  (Govt Warnings) │     │  Database (NADMA)   │
└────────┬────────┘     └────────┬─────────┘     └──────────┬──────────┘
         │                       │                           │
         └───────────────────────┼───────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   🧠 Gemini 2.0 Flash   │
                    │   Multi-Source Reasoning │
                    │   + Model Cascade        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Risk Assessment Engine  │
                    │  SELAMAT │ WASPADA │ BAHAYA│
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
     ┌────────▼───────┐ ┌───────▼────────┐ ┌───────▼────────┐
     │ 🇲🇾 BM Guidance │ │ 🇬🇧 EN Guidance │ │ 🏥 Evacuation   │
     │ (Plain Language)│ │ (Plain Language)│ │ Centre Routing  │
     └────────────────┘ └────────────────┘ └────────────────┘
```

### What Makes Us Different

| Feature | Traditional Systems | BanjirSiaga |
|---------|---------------------|-------------|
| Analysis | Broad meteorological models | **AI-powered contextual, multi-source reasoning** |
| Granularity | State or district level | **Street-level (postcode/GPS)** |
| Language | Standard official broadcasts | **Bilingual conversational BM + EN** |
| Delivery | Portals or scheduled updates | **Instant, mobile-first web app** |
| Photo Analysis | ❌ | ✅ **Gemini Vision flood depth estimation** |
| Historical Context | ❌ | ✅ **Local flood history integration** |

---

## ✨ Features

### 🌧️ Live Flood Risk Assessment
Enter any Malaysian location — postcode, place name, or tap the interactive map — and receive an instant AI-powered risk assessment with actionable guidance in **Bahasa Malaysia** and **English**.

### 📸 Photo-Based Flood Analysis
Upload a photo of your surroundings. **Gemini Vision** analyzes the image to estimate water depth, identify hazards (submerged kerbs, car tyre depth markers), and provide immediate safety guidance.

### 🔄 Scenario Replay Mode
Replay the **December 2024 Kelantan flood** with cached real sensor data. Perfect for disaster preparedness training, emergency planning workshops, and demo stability.

### 🏥 Evacuation Centre Routing
When risk level reaches **BAHAYA** (Danger), BanjirSiaga automatically surfaces the nearest evacuation centres with real-time distance calculations, capacity info, and addresses.

### ⚠️ Government Warning Integration
Live integration with **data.gov.my** official weather warning API — automatically factored into every risk assessment.

### 🧠 Intelligent Model Cascade
Resilient AI architecture with automatic failover across **3 Gemini models** (`gemini-2.0-flash` → `gemini-2.0-flash-lite` → `gemini-1.5-flash-8b`), plus a **rule-based fallback engine** ensuring 100% uptime — even during API outages.

---

## 🏗️ Architecture

```
BanjirSiaga/
├── main.py                          # FastAPI backend (507 lines, single-file architecture)
│   ├── /api/assess     [POST]       # Location-based AI flood risk assessment
│   ├── /api/photo      [POST]       # Photo-based Gemini Vision analysis
│   ├── /api/warnings   [GET]        # Live government weather warnings
│   ├── /api/centres    [GET]        # Nearest evacuation centres (Haversine)
│   └── /               [GET]        # Serve frontend SPA
├── static/
│   └── index.html                   # Premium dark-mode SPA (Leaflet maps, animations)
├── data/
│   ├── flood_history.json           # Historical flood records (10 KL/Selangor areas)
│   ├── evacuation_centres.json      # Evacuation centre database with coordinates
│   └── replay_kelantan_2024.json    # Cached scenario data for replay mode
├── Dockerfile                       # Production container (Python 3.12-slim)
├── requirements.txt                 # Minimal dependencies (6 packages)
└── .env.local                       # GEMINI_API_KEY (not committed)
```

### Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **AI Engine** | Gemini 2.0 Flash | Best-in-class multimodal reasoning with vision capabilities |
| **Backend** | FastAPI + Uvicorn | Async Python, sub-100ms response times |
| **Weather Data** | Open-Meteo API | Free, no-key, real-time global weather data |
| **Govt Data** | data.gov.my | Official Malaysian weather warnings |
| **Geocoding** | Nominatim (OSM) | Free, accurate Malaysian address resolution |
| **Maps** | Leaflet.js + CartoDB | Beautiful dark-mode interactive maps |
| **Frontend** | Vanilla HTML/CSS/JS | Zero build step, instant deployment, premium glassmorphism UI |
| **Deployment** | Google Cloud Run | Serverless, auto-scaling, pay-per-use |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com/) API key (free tier available)

### 1. Clone & Install

```bash
git clone https://github.com/your-team/BanjirSiaga.git
cd BanjirSiaga
pip install -r requirements.txt
```

### 2. Configure

```bash
# Create .env.local
echo "GEMINI_API_KEY=your_api_key_here" > .env.local
```

### 3. Run

```bash
python main.py
```

Open **http://localhost:8000** — that's it! 🎉

---

## ☁️ Deployment

### Google Cloud Run (Recommended)

```bash
gcloud run deploy banjirsiaga \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here
```

### Docker

```bash
docker build -t banjirsiaga .
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key banjirsiaga
```

---

## 📊 Data Sources

| Source | Type | Cost | Usage |
|--------|------|------|-------|
| [Open-Meteo](https://open-meteo.com/) | Real-time weather | Free, no key | Rainfall, humidity, wind, precipitation probability |
| [data.gov.my](https://developer.data.gov.my/) | Government warnings | Free, no key | Official MetMalaysia weather alerts |
| NADMA + News Archives | Historical records | Compiled | Hyper-local flood history for 10 high-risk KL/Selangor areas |
| [Nominatim (OSM)](https://nominatim.openstreetmap.org/) | Geocoding | Free | Malaysian address → coordinates |

### Coverage Area

Flood history database includes high-risk zones across the Klang Valley:

> **Wangsa Maju** · **Ampang** · **Cheras** · **Setapak** · **Pandan Indah** · **Shah Alam** · **KLCC** · **Petaling Jaya** · **Bangsar** · **Bukit Jalil**

---

## 🛡️ Resilience Design

BanjirSiaga is built for the worst moments — when infrastructure faces extreme load and connectivity is limited:

- **Model Cascade**: 3-tier Gemini failover with intelligent retry and backoff
- **Rule-Based Fallback**: When ALL AI models fail, a deterministic rule engine provides assessments using PRD-defined thresholds — ensuring **zero downtime**
- **Photo Fallback**: Realistic randomized photo analyses when Vision API is unavailable
- **Graceful Degradation**: External API connection issues are silently handled — Open-Meteo data alone is sufficient for accurate assessments

---

## 🎯 Risk Level System

| Level | Malay | Criteria | Response |
|-------|-------|----------|----------|
| 🟢 | **SELAMAT** (Safe) | Rainfall < 5mm/hr, no warnings, no history | Monitor only |
| 🟡 | **WASPADA** (Alert) | Rainfall 5-15mm/hr OR active warning OR flood history | Prepare emergency bag, move vehicles |
| 🔴 | **BAHAYA** (Danger) | Rainfall > 15mm/hr AND (warning OR high-risk area) | **Evacuate immediately**, call 999 |

---

## 👥 Team

Built with ❤️ for the **Build with AI Hackathon — GDGKL × Google DeepMind**

---

## 📄 License

This project is built for the public good. Open-sourced for Malaysia's future flood resilience.

---

<p align="center">
  <strong>🌊 Because the next flood shouldn't catch anyone off guard.</strong><br/>
  <em>BanjirSiaga — Sentiasa Bersedia. Always Prepared.</em>
</p>

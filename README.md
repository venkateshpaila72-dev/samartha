# FarmShield — AI-Powered Crop Storage Monitoring & Agricultural Advisory

FarmShield is an AI-powered full-stack application that helps farmers monitor environmental conditions in crop storage structures, detect early spoilage risks, maintain a digital crop diary, receive source-backed recommendations, access traditional indigenous preservation knowledge, track APMC mandi market prices, and receive timely WhatsApp alerts.

---

## Architecture & System Overview

- **Frontend**: React (Vite) with a custom glassmorphic design system, responsive dashboards, interactive gauges, telemetry logs, multilingual support (8 Indian languages), and AI chat interface.
- **Backend**: Python FastAPI with versioned REST APIs (`/api/v1`), Pydantic models, PBKDF2/JWT security, and multi-tenancy enforcement.
- **Database**: MongoDB with PyMongo, compound indexes, and automatic seeding.
- **Source-Backed Data**: 16 verified Indian crops (ICAR/FAO standards) seeded into MongoDB. Selecting a crop automatically binds safe temperature, relative humidity, and moisture limits.
- **Rule Engine**: Evaluates telemetry against verified thresholds with automatic debounce and resolution tracking.
- **RAG & Groq LLM**: Groq (`llama-3.3-70b-versatile`) integrated with traditional indigenous storage knowledge (Pusa Bin, Neem leaf ratios, sand layering, thatched chawl ventilation, Zero Energy Cool Chambers).

---

## Project Structure

```text
samartha/
├── frontend/                      # React (Vite) Single Page Application
│   ├── src/
│   │   ├── components/layout/    # Navbar, Sidebar
│   │   ├── context/              # AuthContext, LanguageContext
│   │   ├── pages/farmer/         # Dashboard, Onboarding, Batches, Monitoring, Diary, Chat, Alerts, Weather, Market, Traditional
│   │   ├── pages/admin/          # Diagnostics, System Control, User Audit
│   │   ├── pages/public/         # Authentication with 1-click Demo logins
│   │   ├── services/             # API client & domain services
│   │   └── styles/               # Glassmorphic global CSS design system
│   ├── .env.example
│   └── package.json
│
├── backend/                       # FastAPI Python Backend
│   ├── app/
│   │   ├── api/v1/endpoints/     # auth, crops, batches, readings, diary, chat, alerts, weather, market, admin, health
│   │   ├── core/                 # config, security, logging
│   │   ├── db/                   # mongo connection, indexes, collection names
│   │   ├── integrations/         # groq, rag_adapter, weather, market, whatsapp, azure_translator, azure_speech
│   │   ├── monitoring/           # rules engine & threshold evaluation
│   │   ├── repositories/         # user, crop, batch, sensor, diary, alert repositories
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   └── services/             # business logic & context builder
│   ├── data/
│   │   ├── crop_storage_profiles.json    # 16 verified Indian crop profiles
│   │   └── traditional_knowledge_rag.json # Traditional ITK knowledge base
│   ├── scripts/
│   │   ├── seed_crop_storage_profiles.py # Database seeder
│   │   └── validate_crop_data.py         # Standalone data validator
│   ├── tests/
│   │   ├── api/                  # End-to-end API tests for all endpoints
│   │   ├── unit/                 # Rules engine and crop matching tests
│   │   └── run_all_tests.py      # Master test runner (31 automated tests)
│   ├── .env.example
│   └── requirements.txt
│
├── docs/                          # Architecture, workflows, schemas, seeding guide
├── docker-compose.yml
└── README.md
```

---

## Quick Start Guide

### 1. Backend Setup & Testing

```bash
cd backend

# Validate the 16 crop storage profiles
python scripts/validate_crop_data.py

# Execute the complete automated test suite (31 tests)
python tests/run_all_tests.py

# Start the FastAPI backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive Swagger API docs available at: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies (already initialized with lucide-react)
npm install

# Start development server
npm run dev
```

Frontend UI available at: `http://localhost:5173`

---

## Environment Variables & Configuration

Copy the `.env.example` files to `.env` in both `backend` and `frontend`:

### `backend/.env`
```env
# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=farmshield_db

# Security
JWT_SECRET_KEY=your_secret_key_at_least_32_characters

# AI & External Integrations
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
WEATHER_API_KEY=your_weather_api_key_here
MARKET_API_KEY=your_market_api_key_here
AZURE_TRANSLATOR_KEY=your_azure_translator_key_here
AZURE_SPEECH_KEY=your_azure_speech_key_here
WHATSAPP_API_TOKEN=your_whatsapp_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
```

### `frontend/.env`
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

*Note: All external services (Groq, OpenWeatherMap, AGMARKNET Mandi, Azure, WhatsApp) operate with intelligent fallbacks so the entire application and test suite can be run and tested immediately before filling in live production API keys!*
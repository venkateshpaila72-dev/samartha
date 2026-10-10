# FarmShield — System Architecture

## 1. Overview
FarmShield is an AI-powered crop storage monitoring and agricultural advisory system designed to help Indian farmers preserve harvested produce, minimize post-harvest loss, prevent aflatoxin and pulse beetle infestations, and make informed selling decisions.

```text
                                  FARMSHIELD ARCHITECTURE
                                             |
                         +-------------------+-------------------+
                         |                                       |
                   React Frontend                           Admin Portal
                   (Vite / Glassmorphic)                    (Diagnostics & Verification)
                         |                                       |
                         +-------------------+-------------------+
                                             |
                                     HTTPS REST API (/api/v1)
                                             |
                                      FastAPI Backend
                                             |
            +--------------------------------+--------------------------------+
            |               |                |               |                |
         Auth API        Crop API        Batch API       Sensor API       Chatbot API
            |               |                |               |                |
            +---------------+----------------+---------------+----------------+
                                             |
                                       Service Layer
                                             |
            +--------------------------------+--------------------------------+
            |                 |              |               |                |
       Repositories     Monitoring &    AI Context       RAG Adapter     Integrations
        (PyMongo)       Rule Engine       Builder          (ITK)           (Weather,
            |                 |              |               |            Market, Azure,
            |                 |              |               |              WhatsApp)
            v                 v              v               v                v
      MongoDB Database    Debounce &    Groq LLM       Traditional       External APIs
      - Crop Profiles     Auto-Resolve  llama-3.3      Knowledge Base
      - Batches & Read.   Transitions
```

## 2. Core Subsystems

### 2.1 Verified Crop Reference Data & Deterministic Matching
- **Source-Backed Data**: 16 major Indian crops (Paddy, Wheat, Maize, Groundnut, Chickpea, Pigeon Pea, Green Gram, Black Gram, Soybean, Bajra, Ragi, Onion, Potato, Tomato, Mango, Banana).
- **Standards**: Formulated according to ICAR (Indian Council of Agricultural Research), Indian Institute of Rice Research (IIRR), Indian Institute of Pulses Research (IIPR), Central Potato Research Institute (CPRI), and FAO Post-Harvest Protocols.
- **Deterministic Selection**: Backend matches crops based on identity, variety, crop form, storage structure, and duration. Authoritative temperature and humidity bounds are loaded dynamically from MongoDB, never hardcoded in frontend UI or prompt text.

### 2.2 Monitoring & Alert Engine
- **Telemetry Validation**: Ingests temperature, relative humidity, grain moisture, and provenance (`manual`, `hardware_sensor`, `simulated`).
- **Debounce & Auto-Resolution**: 
  - Prevents alert storms by checking if a condition is already active.
  - Automatically resolves alerts when measurements return to safe thresholds.
  - Dispatches WhatsApp alerts via Meta Cloud API / WhatsApp provider.

### 2.3 RAG Traditional Knowledge & Groq LLM
- **Context Builder**: Gathers active batch metadata, verified limits, recent readings, diary entries, and RAG traditional documents into a coherent domain context.
- **RAG Adapter**: Retrieves Indigenous Technical Knowledge (ITK) documents (Neem leaf ratio, Pusa Bin hermetic design, vegetable oil smearing, Thatched Chawl ventilation, Zero Energy Cool Chamber).
- **Groq LLM**: Reasoner using `llama-3.3-70b-versatile` with structured source citation extraction.

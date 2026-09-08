# ORCA — Marine Intelligence Dashboard

**ORCA** is an AI-powered marine intelligence and decision-support system designed to help fishers and marine operators make better-informed decisions about **where to fish, whether conditions are safe, and how to reach a selected fishing zone**.

ORCA combines oceanographic data, safety forecasts, route analysis, deterministic scoring, and an AI assistant into a single interactive dashboard.

---

## ✨ Key Features

### 🎣 Potential Fishing Zones

* Identifies and ranks potential fishing zones (PFZs).
* Calculates a **fishing potential score** using oceanographic indicators.
* Uses:

  * Chlorophyll concentration
  * Sea Surface Temperature (SST)
  * Ocean current speed
* Displays recommended zones directly on an interactive map.

### 🌊 Ocean Conditions

Provides zone-level marine information including:

* Sea Surface Temperature
* Chlorophyll concentration
* Current speed
* PFZ-related distance information

The Ocean Agent calculates a normalized **Habitat Suitability Index (HSI)** to estimate fishing potential.

### 🛟 Marine Safety Assessment

Evaluates marine conditions using weather and marine forecasts.

Safety analysis considers:

* Wind speed
* Wave height
* Rainfall
* Forecast conditions

Safety results are classified into levels such as:

* **SAFE**
* **MODERATE**
* **CAUTION**
* **UNSAFE**

The system also identifies the safest available forecast time based on the calculated safety score.

### 🧭 Route Planning

The Routing Agent estimates accessibility to fishing zones using:

* Distance
* Travel time
* Fuel requirements
* Route safety
* Route efficiency

The routing system uses the **M3_v2 deterministic scoring engine** and its associated scoring artifact rather than relying on an opaque prediction at runtime.

### 🤖 ORCA AI Assistant

ORCA includes a conversational AI assistant that allows users to ask questions naturally about:

* Fishing zones
* Ocean conditions
* Safety
* Routes
* Distance
* Travel time
* Fuel requirements
* Previously discussed zones

The assistant supports contextual follow-up questions such as:

> "Why this zone?"

> "Is it safe?"

> "How far is it?"

> "What about the waves?"

> "How much fuel will I need?"

Gemini is used primarily for **query understanding, intent detection, agent selection, language detection, and response synthesis**. It does not independently generate the marine measurements or final decision.

### 🌐 Multilingual Interaction

The assistant is designed to respond according to the user's language and writing style, including:

* English
* Hindi
* Hinglish
* Tamil
* Punjabi
* Marathi
* Telugu
* Bengali
* Malayalam
* Kannada
* Gujarati

Hinglish is specifically distinguished from Hindi written in Devanagari, allowing Romanized Hindi queries to receive Romanized Hindi responses.

### 🗺️ Interactive Marine Map

The dashboard provides an interactive map where users can:

* View fishing zones
* See the user's current location
* Inspect zone details
* Locate zones mentioned by the AI assistant

AI responses containing known PFZ IDs can provide a **"Locate on map"** action to quickly focus the corresponding zone.

---

## 🧠 System Architecture

ORCA follows a modular multi-agent architecture.

```text
                         ┌─────────────────────┐
                         │    ORCA Frontend    │
                         │ React + TanStack    │
                         │      + Leaflet      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Query Agent      │
                         │ Gemini-based Planner │
                         │ + Context Handling  │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             ┌────────────┐  ┌────────────┐  ┌────────────┐
             │ Ocean Agent│  │Safety Agent│  │Route Agent │
             │            │  │            │  │            │
             │ Fishing    │  │ Wind/Wave  │  │ Distance   │
             │ Potential  │  │ Rain/Weather│ │ Time/Fuel  │
             └─────┬──────┘  └──────┬─────┘  └─────┬──────┘
                   │                │              │
                   └────────────────┼──────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │   Decision Layer    │
                         │ Deterministic Final │
                         │      Decision       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Gemini Synthesizer  │
                         │ Natural-language    │
                         │ response generation │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   ORCA Dashboard    │
                         │ Recommendation +    │
                         │ Evidence + Map      │
                         └─────────────────────┘
```

---

## 🔄 How ORCA Processes a Query

For a query such as:

> **"Where should I go fishing tomorrow and is it safe?"**

ORCA follows this general pipeline:

1. **User submits a query**
2. The **Query Agent** interprets the request.
3. Gemini identifies:

   * User intent
   * Language
   * Required specialist agents
   * Relevant entities such as zone IDs or locations
4. The required specialist agents are executed.
5. The **Ocean Agent** evaluates fishing potential.
6. The **Safety Agent** evaluates marine/weather risk.
7. The **Route Agent** evaluates accessibility when required.
8. The **Decision Layer** combines the relevant scores and applies decision constraints.
9. Gemini receives the verified results and converts them into a concise natural-language response.
10. The frontend displays the result and can connect referenced PFZs back to the map.

---

## 🎯 Decision Layer

A central design principle of ORCA is that the LLM is **not the final decision-maker**.

The Decision Layer combines specialist outputs using deterministic scoring logic.

The current combined decision uses:

```text
Final Score =
    0.40 × Fishing Score
  + 0.35 × Safety Score
  + 0.25 × Route Score
```

The Decision Layer then applies constraints to determine the final recommendation.

Possible decisions include:

* **SAFE** — conditions support proceeding based on the available analysis.
* **CAUTION** — conditions require additional care.
* **NO-GO** — proceeding is not recommended.

This separation makes the system more predictable and helps prevent the language model from overriding calculated safety or routing results.

---

## 🧩 Specialist Agents

### Ocean Agent

The Ocean Agent reads the unified ocean dataset and calculates fishing potential.

The HSI currently considers:

```text
Chlorophyll → 40%
SST         → 30%
Current     → 30%
```

Missing values are handled without inventing replacement measurements, and available components are appropriately reweighted.

---

### Safety Agent

The Safety Agent obtains forecast information for a location and evaluates:

```text
Wind       → 30%
Wave       → 25%
Rainfall   → 10%
```

Available weights are normalized when some forecast variables are unavailable.

The system produces both component safety scores and an overall forecast safety level.

---

### Routing Agent

The Routing Agent uses the `M3_v2` deterministic route scoring engine.

The route score incorporates:

* Route efficiency
* Route safety

Safety scoring considers factors such as:

* Water depth
* MPA/constraint conditions
* Current speed

The scoring engine uses a stored model artifact containing the required scoring references and weights.

---

### Query Agent

The Query Agent acts as ORCA's semantic planning layer.

It determines:

* Intent
* Language
* Required agents
* Entities
* Requested operations
* Query confidence

It can route a single request to multiple specialist agents.

For example:

```text
"Find the best fishing zone and tell me if it is
safe and how much fuel I need."

                ↓

        Query Agent

       ┌───────────────┐
       │ Ocean Agent   │
       │ Safety Agent  │
       │ Route Agent   │
       └───────────────┘

                ↓

        Decision Layer

                ↓

       Gemini Response
```

---

## 💬 Conversation Context

ORCA maintains lightweight conversation context using a conversation ID.

Relevant information from previous analyses can be stored and reused for follow-up questions.

For example:

```text
User:
"Which zone is best?"

ORCA:
"PFZ0105 is currently the best option..."

User:
"Why?"

ORCA:
Explains why PFZ0105 was selected.

User:
"How far is it?"

ORCA:
Provides the route information for PFZ0105.
```

This allows the assistant to understand short contextual questions without requiring the user to repeat the zone every time.

---

## 🛡️ Reliability Principles

ORCA is designed around several important safeguards:

* Specialist agents provide the underlying data.
* The Decision Layer is authoritative for combined decisions.
* Gemini does not invent marine measurements.
* Missing values are not silently fabricated.
* Current conditions and forecasts are kept distinct.
* Numerical values are rounded only for presentation.
* The AI response layer explains verified results rather than independently calculating them.
* If a combined Decision Layer result is unavailable, the assistant does not pretend that one was generated.

---

## 🛠️ Technology Stack

### Frontend

* **React 19**
* **TypeScript**
* **TanStack Start**
* **TanStack Router**
* **TanStack Query**
* **Vite**
* **Tailwind CSS**
* **Leaflet**
* **React Leaflet**
* **Recharts**
* **Lucide React**

### Backend

* **Python**
* **FastAPI**
* **Pydantic**
* **Pandas**
* **NumPy**
* **Joblib**
* **Requests**
* **Uvicorn**

### AI

* **Google Gemini API**
* Gemini-based query planning
* Intent and language detection
* Specialist-agent selection
* Natural-language response synthesis

### External Forecast Data

ORCA's safety forecast adapter uses:

* Open-Meteo Marine API
* Open-Meteo Weather Forecast API

---

## 📁 Project Structure

```text
ORCA-Web-main/
│
├── backend/
│   ├── agents/
│   │   ├── decision_layer/
│   │   │   ├── main.py
│   │   │   ├── scoring.py
│   │   │   ├── constraints.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── query_agent/
│   │   │   ├── main.py
│   │   │   ├── gemini_planner.py
│   │   │   ├── gemini_synthesizer.py
│   │   │   └── parser.py
│   │   │
│   │   ├── routing_agent/
│   │   │   ├── predict.py
│   │   │   └── route_model.pkl
│   │   │
│   │   └── safety_agent/
│   │       └── forecast_adapter.py
│   │
│   ├── api/
│   │   ├── ocean_api.py
│   │   ├── safety_api.py
│   │   └── route_api.py
│   │
│   ├── data/
│   │   ├── ocean/
│   │   └── routing/
│   │
│   ├── gemini_client.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── .env.example
├── START_ORCA.bat
└── gemini_test.py
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd ORCA-Web-main
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

OCEAN_API=http://localhost:8002
SAFETY_API=http://localhost:8003
ROUTE_API=http://localhost:8004
DECISION_API=http://localhost:8000

FRONTEND_URL=http://localhost:8080
```

Never commit your actual API key to GitHub.

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 6. Start ORCA

On Windows, the included startup script can launch the complete system:

```text
START_ORCA.bat
```

It starts:

| Service        |   Port |
| -------------- | -----: |
| Decision Layer | `8000` |
| Query Agent    | `8001` |
| Ocean Agent    | `8002` |
| Safety Agent   | `8003` |
| Routing Agent  | `8004` |
| Frontend       | `8080` |

The dashboard is then available at:

```text
http://localhost:8080
```

---

## 🧪 Example Queries

Try questions such as:

```text
Which fishing zone is best?
```

```text
Is it safe to go fishing?
```

```text
What are the ocean conditions?
```

```text
How far is PFZ0005?
```

```text
Which zone has the best fishing potential?
```

```text
Find the best fishing zone and check whether it is safe.
```

```text
Mujhe fishing ke liye best zone batao
```

```text
Mujhe batao wahan jaana safe hai ya nahi
```

```text
What about the route?
```

```text
How much fuel will I need?
```

---

## 📊 Data & Scoring

ORCA separates **data processing**, **decision-making**, and **language generation**.

```text
Raw / Forecast Data
        ↓
Specialist Analysis
        ↓
Normalized Scores
        ↓
Deterministic Decision Layer
        ↓
Verified Results
        ↓
Natural-language Explanation
```

This architecture allows the AI assistant to provide a conversational interface while keeping the underlying recommendations grounded in structured calculations.

---

## 🔮 Future Scope

Potential future improvements include:

* Real-time satellite/ocean data integration
* More detailed PFZ boundary visualization
* Real-time vessel tracking
* Offline/low-connectivity support
* Voice-based interaction
* Personalized fishing recommendations
* Historical trip analytics
* User feedback loops
* Additional marine hazards and alerts
* More sophisticated route optimization
* Deployment as a scalable cloud service


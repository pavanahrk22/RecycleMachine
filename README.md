# CampusCycle ♻️

CampusCycle is the software layer for smart campus reverse vending and recycling machines. Students deposit recyclable items (bottles, cans, rigid plastics, snack wrappers), AI identifies the item and detects contamination/multiple objects, and the backend converts weight readings into reward points redeemable for campus perks.

---

## Architecture & Tech Stack

- **Frontend:** React (Vite), Tailwind CSS, Recharts
- **Backend:** FastAPI, Python 3.12, Pydantic v2
- **AI Classification:** Google GenAI SDK (`google-genai`), Gemini 2.5 Flash
- **Database & Auth:** Firebase Auth (Google Sign-In) + Firestore

---

## Milestone 1: Core API & AI Classification Engine

### Features Implemented
1. **`/api/drop` Endpoint:** Accepts multipart image upload, simulated weight (`weight_g`), and `machine_id`.
2. **Gemini Vision Classification:** Sends image bytes with structured schema (`ItemAnalysis`) to Gemini Flash with retry & timeout handling.
3. **Config-Driven Rules Engine:**
   - Rates loaded from `config/rates.json`
   - Points formula: `points = round(weight_g / 100 * rate_per_100g)` with half-up rounding.
   - Physical weight bounds checking per material (e.g. PET bottle 8–60g, can 8–25g, wrapper 1–12g).
   - Multi-item detection and contamination rejection.
   - Confidence threshold enforcement (minimum 0.70).
4. **Automated Test Suite:** 12 unit and integration tests covering calculation, bounds, fraud conditions, and API behavior.

---

## Quickstart

### 1. Backend Setup
```bash
# Navigate to backend and create virtual environment
python -m venv backend/venv

# Activate virtual environment
# Windows:
.\backend\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
copy backend\.env.example backend\.env
```
Set your `GEMINI_API_KEY` in `backend/.env`. (If testing offline or without an active key, you can set `MOCK_CLASSIFICATION=true`).

### 3. Run the Backend Server
```bash
# From workspace root
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Run Test Suite
```bash
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest backend/tests -v
```

### 5. Test with curl
```bash
# Accepted drop test
curl.exe -X POST "http://127.0.0.1:8000/api/drop" `
  -F "image=@backend/sample_item.png;type=image/png" `
  -F "weight_g=25.0" `
  -F "machine_id=sim-machine-01"

# Rejected drop test (out of bounds weight: 80g for PET bottle)
curl.exe -X POST "http://127.0.0.1:8000/api/drop" `
  -F "image=@backend/sample_item.png;type=image/png" `
  -F "weight_g=80.0" `
  -F "machine_id=sim-machine-01"
```

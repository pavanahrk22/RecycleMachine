# CampusCycle ♻️

CampusCycle is the software layer for smart campus reverse vending and recycling machines. Students deposit recyclable items (bottles, cans, rigid plastics, snack wrappers), AI identifies the item and detects contamination/multiple objects, and the backend converts weight readings into reward points redeemable for campus perks.

---

## Architecture & Tech Stack

- **Frontend:** React (Vite), Tailwind CSS, Recharts
- **Backend:** FastAPI, Python 3.12, Pydantic v2
- **AI Classification:** Google GenAI SDK (`google-genai`), Gemini 3.8 Flash
- **Database & Auth:** Firebase Auth (Google Sign-In) + Firestore (Admin SDK)

---

## Firestore Document Structure

### 1. `users/{uid}`
Created automatically on the user's first request:
```json
{
  "displayName": "student_pavana",
  "email": "student_pavana@campus.edu",
  "pointsBalance": 25,
  "totalGrams": 25.0,
  "totalItems": 1,
  "createdAt": "2026-10-09T06:23:51.892000+00:00"
}
```

### 2. `drops/{id}`
Created inside a single Firestore transaction for each drop:
```json
{
  "id": "drop_9673db44c565",
  "uid": "student_pavana",
  "machineId": "sim-machine-01",
  "material": "pet_bottle",
  "confidence": 0.95,
  "contaminated": false,
  "weightG": 25.0,
  "points": 25,
  "status": "accepted",
  "rejectReason": null,
  "imageHash": "bf6e855b67618763d38f0cd8c2ab5ea9aed7b28f4475939f040e4e3ac016bedc",
  "createdAt": "2026-10-09T06:24:14.824651+00:00"
}
```
*(Images are never stored; only the SHA-256 hash is kept for 24h duplicate fraud detection).*

### 3. `stats/campus`
Aggregated campus-wide metrics updated atomically on accepted drops:
```json
{
  "totalGrams": 25.0,
  "totalItems": 1,
  "countsByMaterial": {
    "pet_bottle": 1
  }
}
```

---

## Fraud & Abuse Controls Enforced Server-Side

1. **SHA-256 Duplicate Detection:** Rejects identical photo hashes from the same user within 24 hours.
2. **Cooldown Guard:** Rejects drops submitted within 12 seconds of the previous drop.
3. **Daily Quota Caps:** Rejects drops if user exceeds 30 drops or 1000g total weight within 24 hours.
4. **Physical Weight Bounds:** Validates simulated load-cell readings against material ranges (e.g. PET bottle 8–60g).
5. **AI Contamination & Multi-Item Flags:** Rejects dirty, wet, food-stained, or multiple items.

---

## Quickstart & Running

### 1. Backend Setup
```bash
python -m venv backend/venv
.\backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2. Configuration (`.env`)
```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.8-flash
ENV=dev
GOOGLE_APPLICATION_CREDENTIALS=serviceAccountKey.json
```

### 3. Run Tests (22 Passing Tests)
```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest backend/tests -v
```

### 4. Start Server
```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

---

## Endpoint Curl Examples

### Health Check (Public)
```bash
curl.exe -s http://127.0.0.1:8000/health
```

### Get My Profile (`GET /api/me`)
```bash
# In Dev mode using X-Dev-User bypass:
curl.exe -s -H "X-Dev-User: student_pavana" http://127.0.0.1:8000/api/me

# In Production using Firebase ID Token:
curl.exe -s -H "Authorization: Bearer <FIREBASE_ID_TOKEN>" https://your-backend.run.app/api/me
```

### Submit Item (`POST /api/drop`)
```bash
curl.exe -s -X POST "http://127.0.0.1:8000/api/drop" `
  -H "X-Dev-User: student_pavana" `
  -F "image=@backend/sample_item.png;type=image/png" `
  -F "weight_g=25.0" `
  -F "machine_id=sim-machine-01"
```

### Get My Drops History (`GET /api/drops?limit=20`)
```bash
curl.exe -s -H "X-Dev-User: student_pavana" "http://127.0.0.1:8000/api/drops?limit=20"
```

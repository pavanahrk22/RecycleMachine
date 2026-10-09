# CampusCycle — Product Requirements Document and Build Plan

Working title · Prepared for Pavana · PromptWars x Error Zero (Hack2skill) · 9 Oct 2026

## 1. Overview

CampusCycle is the software layer for a campus recycling machine. A student drops in an empty bottle or snack wrapper, AI identifies the item, a weight reading is converted into reward points, and the points can be redeemed as rupee value (default: 100 points per 100 g, and 100 points = ₹1).

- **Track:** Smart Campus Solutions (fallback: Open Innovation if the brief feels too narrow).
- **Prototype scope:** a working web app with a simulated machine (laptop or phone camera plus a simulated weight input). No physical hardware.
- **Deadline:** the countdown in your screenshot read about 8h 38m at 9:51 AM on 9 Oct, which is roughly 6:30 PM IST. Confirm on the Submissions tab and aim to submit by 5:45 PM at the latest.
- **Guiding principle:** one simple flow, executed reliably, beats a long feature list. Everything below is ordered so that the core flow works first.

## 2. Problem statement

Campuses generate a steady stream of plastic bottles and snack wrappers that end up in general bins. Students have no incentive to segregate, and the campus has no data on what is being thrown away. Reverse vending machines exist, but they are rarely tied to student accounts, rewards, fraud control, or campus analytics.

## 3. Goals and non-goals

**Goals**

- A deployed, end-to-end demo: login, drop item, AI classification, points, wallet, redeem, impact dashboard.
- Visible AI value: Gemini vision identifies the material and flags contaminated or invalid items.
- Believable anti-fraud logic that judges can see working.
- A clean story for how real hardware plugs into the same API later.

**Non-goals (do not build these)**

- Real hardware, a real load cell, or a physical machine.
- Real money payments or UPI payouts.
- Multi-campus support, native mobile apps, or complex admin tooling.
- Calibrated real-world accuracy. The prototype only needs to work on a controlled demo set.

## 4. Users

- **Student (primary):** drops waste, earns and redeems points.
- **Campus sustainability officer (secondary):** views the impact dashboard and flagged activity.
- **Judges:** need to understand the idea and see it work in about two minutes.

## 5. User stories (MVP)

- As a student, I sign in with my Google account so my points are tied to me.
- As a student, I show an item to the camera, confirm the weight, and see how many points I earned and why.
- As a student, I see a clear reason when an item is rejected (dirty, not recyclable, unclear image, duplicate).
- As a student, I can view my balance and history and redeem points for a coupon code.
- As an officer, I can see total kilograms diverted, items by material, and a leaderboard.

## 6. Scope priorities

**P0 — must work, no exceptions**

- Google sign-in (Firebase Auth) and a points wallet.
- Kiosk screen: camera capture, simulated weight input, Drop button.
- Backend /api/drop: Gemini classification, points rules, fraud checks, Firestore write.
- Result card showing material, confidence, points, and any rejection reason.
- Deployed frontend and backend with a public link.

**P1 — should have**

- Wallet history, redeem flow with a mock coupon code.
- Impact dashboard with totals, a material chart, and a top-5 leaderboard.
- Duplicate-image detection and daily caps.

**P2 — only if time remains**

- Admin flagged-activity list.
- First drop of the day bonus.
- Hindi or Kannada UI labels.
- Short lock-out after repeated rejected drops.

**Cut order if you fall behind:** P2 first, then the leaderboard, then the redeem screen polish. Never cut the core drop flow or the deployment.

## 7. Functional requirements

**7.1 Authentication**

- Google sign-in through Firebase Auth. Optionally restrict to the college email domain.
- Backend verifies the Firebase ID token on every request.

**7.2 Drop flow**

1. Student opens the Kiosk screen and grants camera permission.
2. Student holds up one item and captures a photo (file upload is the fallback).
3. Student sets the simulated load cell reading (slider or number field, clearly labelled as simulated).
4. Frontend sends the image and weight to POST /api/drop.
5. Backend classifies, validates, calculates points, writes the result, and returns it.
6. UI shows an accepted or rejected result card.

**7.3 AI classification**

- Gemini returns structured JSON: material, confidence, contaminated, multiple_items, reason.
- Materials: pet_bottle, aluminium_can, rigid_plastic, snack_wrapper, non_recyclable, no_item.
- Confidence below 0.70 asks the student to retake the photo. Contaminated or multiple items are rejected.

**7.4 Points engine**

- Formula: points = round(weight_g / 100 × rate_per_100g), with the rate chosen by material.
- All rates, bounds, and caps live in one config document so they can be tuned without code changes.

**7.5 Wallet and redeem**

- Balance is updated inside a Firestore transaction.
- Redeem converts points to rupees at 100 points = ₹1 and issues a mock coupon code. Minimum redemption: 100 points.

**7.6 Impact dashboard**

- Total kg diverted, total items, items by material, and top 5 contributors.
- Dashboard reads from a single aggregated stats document so it loads instantly.

## 8. Points rules (starter values, keep in config)

Rates are in points per 100 g. They are placeholders: before presenting, sanity-check them against local scrap prices.

- PET bottle: 100
- Aluminium can: 150
- Other rigid plastic: 80
- Multilayer snack wrapper: 50 (low scrap value, so a lower rate; it also shows the AI classification has a real job)
- Non-recyclable or contaminated: 0 (rejected with a reason)

Example: a 20 g PET bottle earns 20 points, which is ₹0.20. Per-item rewards are small by design, so show points and cumulative impact prominently rather than rupee amounts on each drop.

## 9. Fraud and abuse controls

- **Weight sanity bounds per material** (starting values, tune after testing): pet_bottle 8–60 g, aluminium_can 8–25 g, rigid_plastic 5–150 g, snack_wrapper 1–12 g. Outside the range: reject and log a flag.
- **Contamination check:** Gemini flags wet, dirty, or filled items. Reject them.
- **Duplicate detection:** store a SHA-256 hash of each accepted image. The same hash within 24 hours is rejected.
- **Rate limits:** minimum 5 seconds between drops, and a daily cap of 30 drops or 1 kg per student.
- **Low confidence:** below 0.70, ask for a retake. Do not award points on a guess.
- **Privacy:** do not store images. Store only the hash, result, and metadata.
- **Server-side only:** points are always calculated on the backend. The client never sends a points value.

## 10. Architecture

Flow: React web app (kiosk, wallet, dashboard) → FastAPI service on Cloud Run → Gemini API for vision classification, with Firestore for data and Firebase Auth for identity.

- The simulated machine is just a client that calls POST /api/drop with an image and a weight. A real machine (Raspberry Pi with a camera and a load cell module) would call the same endpoint, which is the hardware story for your pitch.
- Frontend is hosted on Firebase Hosting (or Netlify, which you already use).
- Secrets (Gemini API key, Firebase service account) are environment variables on Cloud Run. Never commit them.

## 11. Tech stack

- **Frontend:** React (Vite), Tailwind, recharts for the material chart.
- **Backend:** Python, FastAPI, pydantic, firebase-admin, google-genai SDK.
- **Data and auth:** Firestore and Firebase Auth.
- **Hosting:** Cloud Run (backend), Firebase Hosting (frontend).
- **AI:** a current Gemini Flash model from Google AI Studio. Check the exact model name available to your key.

## 12. Data model (Firestore)

- **users/{uid}:** displayName, email, pointsBalance, totalGrams, totalItems, createdAt.
- **drops/{id}:** uid, machineId, material, confidence, contaminated, weightG, points, status (accepted or rejected), rejectReason, imageHash, createdAt.
- **redemptions/{id}:** uid, points, rupees, code, createdAt.
- **config/rates:** rate per material, weight bounds, caps, points-to-rupee ratio.
- **stats/campus:** totalGrams, totalItems, countsByMaterial, updated with atomic increments on each accepted drop.

## 13. API specification

All endpoints except /health require the header Authorization: Bearer <Firebase ID token>.

- **POST /api/drop** (multipart: image, weight_g, machine_id) returns status, material, confidence, points, newBalance, and a reason when rejected.
- **GET /api/me** returns the profile and balance.
- **GET /api/drops?limit=20** returns the student's history.
- **POST /api/redeem** (body: points) returns the coupon code, rupees, and newBalance.
- **GET /api/stats** returns campus totals, counts by material, and the top 5 leaderboard.
- **GET /health** returns ok, for deployment checks.

## 14. Gemini integration

**Prompt**

You are the vision classifier for a campus recycling machine. Look at the item in the image and return JSON only. Fields: material (one of pet_bottle, aluminium_can, rigid_plastic, snack_wrapper, non_recyclable, no_item), confidence (0 to 1), contaminated (true if visibly dirty, wet, or containing liquid, food, or foreign objects), multiple_items (true if more than one item is visible), reason (one short sentence). If no clear single item is visible, use no_item. Do not guess: if unsure, lower the confidence.

**Code sketch**

```python
from pydantic import BaseModel
from google import genai
from google.genai import types

class ItemAnalysis(BaseModel):
    material: str
    confidence: float
    contaminated: bool
    multiple_items: bool
    reason: str

client = genai.Client()  # reads GEMINI_API_KEY from the environment

def classify(img_bytes, mime='image/jpeg'):
    resp = client.models.generate_content(
        model='gemini-2.5-flash',  # use the current Flash model your key supports
        contents=[types.Part.from_bytes(data=img_bytes, mime_type=mime), PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=ItemAnalysis,
            temperature=0.1))
    return resp.parsed
```

Wrap the call in a timeout and one retry. If it still fails, return a friendly retry message instead of an error screen.

## 15. UI screens

1. **Login:** Google sign-in button and a one-line pitch.
2. **Kiosk:** live camera preview, simulated weight control, Drop button, and a result card (accepted in green with points; rejected in red with the reason).
3. **Wallet:** balance, recent drops with material and points.
4. **Redeem:** enter points, get a mock coupon code.
5. **Impact dashboard:** total kg, total items, material chart, top-5 leaderboard.

Note: browsers only allow camera access on HTTPS or localhost, so test the deployed version early.

## 16. Hour-by-hour plan (adjust to your actual start time, deadline about 6:30 PM)

- **10:00–10:30 Setup:** Firebase project, Firestore, Auth, Gemini API key, repo, project skeletons, environment variables.
- **10:30–12:00 Backend core:** /api/drop with Gemini classification, points rules, fraud checks, Firestore writes. Test with curl and 15 sample images.
- **12:00–12:30 Break and buffer.**
- **12:30–14:30 Frontend core:** auth, kiosk screen with camera, result card, wallet.
- **14:30–15:30 P1 features:** redeem flow, stats endpoint, dashboard.
- **15:30–16:30 Deploy:** Cloud Run and Firebase Hosting, fix CORS, test the live link on a phone.
- **16:30–17:15 Polish and test:** run the full test plan, fix the top three bugs, tidy the UI.
- **17:15–17:45 Submission assets:** README, demo video, screenshots, form fields.
- **17:45–18:00 Submit.** Do not wait for the final minutes.

Hard rule: if the core drop flow is not working end to end by 14:30, drop every P1 and P2 item and spend the time on stability.

## 17. Master checklist

**Setup**

- [ ] Create Firebase project; enable Firestore and Google sign-in
- [ ] Get a Gemini API key from Google AI Studio and test one image call
- [ ] Create a GitHub repo with a README stub (keep it public or share access as the form requires)
- [ ] Scaffold React (Vite) and FastAPI projects; add a .gitignore and an .env.example

**Backend**

- [ ] Firebase ID token verification middleware
- [ ] Config loader (rates, bounds, caps)
- [ ] Gemini classify function with timeout and retry
- [ ] Points calculation and weight bounds check
- [ ] Duplicate hash check, cooldown, and daily cap
- [ ] Firestore transaction for drop record, balance, and campus stats
- [ ] Endpoints: drop, me, drops, redeem, stats, health
- [ ] Dockerfile and Cloud Run deployment

**Frontend**

- [ ] Google sign-in and an authenticated API client
- [ ] Kiosk screen: camera capture, weight control, Drop button, result card
- [ ] Wallet and history
- [ ] Redeem screen
- [ ] Dashboard with chart and leaderboard
- [ ] Loading and error states everywhere
- [ ] Firebase Hosting deployment and a mobile layout check

**Quality**

- [ ] Run the test plan below
- [ ] Confirm no secrets are in the repo
- [ ] Seed a few demo users and drops so the dashboard is not empty

**Submission**

- [ ] README with problem, solution, architecture, setup steps, and limitations
- [ ] 60 to 120 second demo video
- [ ] Screenshots, live link, and repo link
- [ ] Fill in and submit the form, then confirm it shows as submitted

## 18. Test plan

Collect about 20 real test images before you start tuning prompts: 5 PET bottles of different sizes, 3 cans, 5 wrappers (clean), 2 wet or dirty items, 2 non-recyclable items (a paper cup, a food-stained wrapper), 2 photos with multiple items, and 1 empty or blurry shot.

- Each material is classified correctly on clean, well-lit photos against a plain background.
- Contaminated, multiple-item, and empty photos are rejected with a clear reason.
- A weight outside the bounds is rejected and flagged.
- The same image submitted twice is rejected the second time.
- The cooldown and the daily cap trigger as expected.
- Balance and stats stay consistent after rapid repeated drops (transaction check).
- The deployed app works on a phone, including camera access over HTTPS.

## 19. Demo script (about 2 minutes)

1. **0:00** Problem in one sentence: campus waste, no incentive, no data.
2. **0:15** Sign in with Google.
3. **0:30** Drop a PET bottle: show the classification, weight, and points earned.
4. **0:50** Drop a snack wrapper: it earns points at a lower rate, which shows material-aware rules.
5. **1:05** Drop a wet or dirty item: it is rejected with a clear reason.
6. **1:15** Resubmit the same image: duplicate detected.
7. **1:25** Open the wallet and redeem points for a coupon.
8. **1:40** Show the impact dashboard.
9. **1:50** Close: a real machine only needs a Raspberry Pi, a camera, and a load cell calling the same API.

Record this as a backup video even if you plan to demo live.

## 20. Pitch and judge Q&A

- **Where is the hardware?** This is the software layer. The machine is a client calling one API, so a Raspberry Pi with a camera and load cell can replace the simulated inputs without backend changes.
- **How do you stop cheating?** Vision check, weight bounds per material, duplicate detection, rate limits, and daily caps, all enforced server-side.
- **Why AI instead of a barcode scanner?** Wrappers and crushed bottles often have no readable barcode, and AI also detects contamination and non-recyclables.
- **Who pays for the rewards?** Recycling partners buy the sorted material, and the campus can fund part of it through canteen coupons or sustainability budgets. Mention that rates are configurable and need validation against real scrap prices.
- **What about privacy?** Images are not stored. Only a hash and the result are kept.
- **How accurate is it?** Say honestly that it is tested on a controlled demo set and that production would need a larger labelled dataset and confidence thresholds tuned on it.
- **How does it scale?** Stateless backend on Cloud Run, Firestore for data, and a per-machine ID for fleet analytics.

## 21. Risks and fallbacks

- **Gemini quota or latency:** use a Flash model, keep images small (resize to about 1024 px before sending), add one retry, and have the recorded demo ready.
- **Cloud Run deploy problems:** start the deployment early (by 15:30). Fallback: run the backend locally and expose it through a tunnel for the demo.
- **Camera permission issues:** keep file upload as a fallback and test on HTTPS early.
- **Flaky classification:** use good lighting and a plain background, and demo only items you have tested.
- **Running out of time:** follow the cut order in section 6 and protect the core flow.

## 22. Submission checklist

Open the Submissions tab on Hack2skill and check exactly which fields are required. Typical items are a project title and description, a repository link, a live demo link, a demo video, and sometimes a slide deck. Do not assume. Then:

- Make sure the repo and any Drive or YouTube links are accessible without login.
- Re-read the challenge text and mention how your solution meets the expected outcome (a functional prototype solving a real campus problem).
- Submit at least 30 minutes before the deadline and confirm the status afterwards.

## 23. Future scope (for the last slide or README only)

Real load cell and Raspberry Pi integration, QR-based student login at the machine, multi-machine fleet analytics, bin-full alerts, department leaderboards, canteen and vendor partnerships, and impact estimates (such as emissions avoided) using cited emission factors.

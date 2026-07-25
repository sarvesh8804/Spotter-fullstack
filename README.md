# Spotter HOS Trip Planner

Full-stack assessment app: **Django + React**. Enter current / pickup / dropoff locations and cycle hours used; get a mapped route with HOS-compliant stops and drawn Drivers Daily Log sheets.

## Features

- Geocoding via Nominatim (OpenStreetMap)
- Routing via public OSRM
- FMCSA HOS planner (property-carrying, 70hr/8day):
  - 11-hour driving limit
  - 14-hour window
  - 30-minute break after 8 hours driving
  - 10-hour off-duty reset / 34-hour restart when cycle exhausted
  - Fuel every 1,000 miles
  - 1 hour pickup + 1 hour dropoff
- Interactive Leaflet map with stop markers
- Multi-day paper-style ELD / daily log sheets (SVG)

## Project layout

```
backend/     Django REST API
frontend/    React (Vite) UI
PLAN.md      Detailed plan from assessment docs
```

## Local development

### Backend

```bash
cd spotter-fullstack-assessment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

API: `http://127.0.0.1:8000/api/plan-trip/` (POST JSON)

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Dallas, TX",
  "dropoff_location": "Los Angeles, CA",
  "current_cycle_used": 20
}
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: `http://127.0.0.1:5173`  
Optional: set `VITE_API_URL=http://127.0.0.1:8000` (defaults to that).

### Tests

```bash
cd backend && source ../.venv/bin/activate
python manage.py test trips
```

## Deploy

### Frontend (Vercel)

1. Import the repo; set root directory to `frontend`
2. Build: `npm run build` · Output: `dist`
3. Env: `VITE_API_URL=https://<your-backend-host>`

### Backend (Railway / Render)

1. Root or `backend` with `requirements.txt`
2. Start: `gunicorn config.wsgi --bind 0.0.0.0:$PORT` (from `backend/`)
3. Env:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=false`
   - `DJANGO_ALLOWED_HOSTS=<host>`
   - `CORS_ALLOWED_ORIGINS=https://<vercel-app>`

## Loom walkthrough outline (3–5 min)

1. Problem + assumptions (HOS 70/8, fuel, pickup/dropoff)
2. Live demo: plan Chicago → Dallas → LA
3. Map stops (fuel / break / overnight)
4. Flip through daily log sheets (grid + remarks + recap)
5. Code tour: `hos_planner.py` rules, React log SVG, API endpoint

## Assessment sources

- `new-full-stack-dev-assessment.docx`
- `blank-paper-log.png`
- `fmsca-image.png` (highlighted FMCSA TOC)
- `fmcsa-hos-395-drivers-guide-to-hos-2022-04-28-0-1-.pdf`
- [YouTube log book walkthrough](https://www.youtube.com/watch?v=whxe41XYXS8)

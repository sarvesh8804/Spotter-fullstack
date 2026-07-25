# Spotter Full Stack Assessment — Plan

## Goal

Build a Django + React app that plans a truck trip under FMCSA Hours of Service (HOS) rules and outputs:

1. A **map** of the route with stops (pickup, fuel, rest, dropoff)
2. **Driver’s Daily Log sheets** (paper-log style grid) for each day of the trip

Deliverables: GitHub repo, hosted app, 3–5 min Loom walkthrough.

## Inputs

| Field | Meaning |
| --- | --- |
| Current location | Where the driver starts |
| Pickup location | Where cargo is loaded (1 hour on-duty) |
| Dropoff location | Where cargo is unloaded (1 hour on-duty) |
| Current Cycle Used (Hrs) | Hours already used in the 70hr/8day cycle |

## Assumptions (from brief)

- Property-carrying driver
- **70 hours / 8 days** cycle
- No adverse driving conditions
- Fuel at least once every **1,000 miles** (~30 min on-duty not driving)
- **1 hour** pickup and **1 hour** dropoff (on-duty not driving)

## HOS Rules to Enforce

From FMCSA guide (highlighted TOC) + assessment assumptions:

| Rule | Constraint |
| --- | --- |
| 11-hour driving | Max 11 hours driving after 10 consecutive hours off duty |
| 14-hour window | No driving after 14 consecutive hours from coming on duty; off-duty does **not** pause this window |
| 30-minute break | After 8 cumulative hours of driving without a 30+ min non-driving interruption |
| 10-hour reset | Need 10 consecutive hours off duty (or sleeper) before next driving day |
| 70/8 cycle | Cannot drive after 70 on-duty hours in rolling 8 days; input = hours already used |
| Fuel | Insert fuel stop every ≤1000 miles |

Duty statuses for the log grid (same as blank paper log):

1. Off Duty  
2. Sleeper Berth  
3. Driving  
4. On Duty (not driving)

## Architecture

```
spotter-fullstack-assessment/
├── backend/          # Django REST API
│   └── trips/        # geocode, route, HOS planner, log sheet builder
├── frontend/         # React (Vite) + Leaflet map + SVG log sheets
├── PLAN.md
└── README.md
```

### Backend (Django)

- `POST /api/plan-trip/`  
  Body: `{ current_location, pickup_location, dropoff_location, current_cycle_used }`  
  Response: route geometry, stop list, daily logs, summary stats

- Services:
  1. **Geocoding** — Nominatim (OpenStreetMap), free
  2. **Routing** — OSRM public API (`router.project-osrm.org`), free
  3. **HOS Planner** — pure Python: walk the route mile-by-mile / hour-by-hour, insert rests/fuel/pickup/dropoff, respect all limits
  4. **Log Builder** — split timeline into calendar days; produce grid segments (status + start/end minutes) + remarks + totals + 70hr recap

### Frontend (React)

- Trip form (locations + cycle hours)
- Interactive Leaflet map (route polyline + stop markers)
- Multi-day ELD / paper-style daily log sheets (SVG canvas matching blank-paper-log layout)
- Trip summary (miles, days, driving hours, remaining cycle)
- Strong UI/UX — logistics aesthetic, not generic dashboard chrome

### Hosting

- Frontend → Vercel
- Backend → Railway / Render (free tier) with CORS for Vercel origin  
  (Vercel alone cannot host Django long-running process)

## HOS Planner Algorithm (core)

1. Geocode 3 locations → lat/lon  
2. Route: current → pickup → dropoff; get distance (miles), duration, geometry  
3. Build a timeline starting at a chosen day start (e.g. 06:00 local / home-terminal midnight-aligned for logs):
   - Drive toward next waypoint until a limit is hit
   - At pickup / dropoff: 1h On Duty (not driving)
   - Every 1000 miles driven: ~30m fuel (On Duty not driving)
   - After 8h driving since last 30m+ break: 30m Off Duty break
   - When hitting 11h driving **or** end of 14h window **or** cycle exhausted: stop driving, take 10h Off Duty, start new day
4. Emit events → daily log segments (midnight-to-midnight grid)  
5. Remarks: location name + reason for each duty change  

Average truck speed: derive from OSRM duration/distance; fallback ~55 mph if needed.

## Log Sheet Rendering

Reproduce the blank Drivers Daily Log:

- Header: date, from/to, miles, carrier placeholders  
- 24h grid: 4 rows × 96 quarter-hours; draw horizontal line segments per status  
- Totals column (hours per status)  
- Remarks list  
- Recap: on-duty today; 70hr/8day A/B/C using `current_cycle_used` + prior days in trip  

## Accuracy Checklist

- [ ] Pickup & dropoff each add 1h on-duty  
- [ ] Fuel stops ≤ every 1000 miles  
- [ ] No day exceeds 11h driving  
- [ ] No driving past 14h window  
- [ ] 30m break after 8h driving  
- [ ] 10h off between duty days when required  
- [ ] Cycle never exceeds 70h including `current_cycle_used`  
- [ ] Multiple log sheets for multi-day trips  
- [ ] Map shows all stops with labels  

## Out of Scope (per assumptions)

- Adverse conditions  
- Sleeper-berth split sleeper provision (use full 10h off-duty for simplicity)  
- 60/7 cycle  
- Personal conveyance / yard moves  

## Execution Order

1. Scaffold Django project + planner service with unit-testable pure logic  
2. Scaffold React + form + map + log SVG  
3. Connect API; polish design  
4. README with run/deploy + Loom script outline  
5. Local E2E verification with a sample long-haul trip (e.g. Chicago → Dallas → LA)

## Sample Test Trip

- Current: Chicago, IL  
- Pickup: Dallas, TX  
- Dropoff: Los Angeles, CA  
- Cycle used: 20 hrs  

Expect: multi-day plan, fuel stop(s), rest overnight, several daily logs.

"""
FMCSA Hours-of-Service trip planner for property-carrying drivers (70/8).

Rules enforced (assessment assumptions):
- 11-hour driving limit after 10 consecutive hours off duty
- 14-hour consecutive driving window (short off-duty does NOT extend it)
- 30-minute break after 8 cumulative hours of driving
- 70-hour / 8-day on-duty cycle
- Fuel at least once every 1,000 miles (~30 min on-duty)
- 1 hour on-duty for pickup and 1 hour for dropoff
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Literal

from .routing import point_along_geometry

Status = Literal["off_duty", "sleeper", "driving", "on_duty"]

MAX_DRIVE_HOURS = 11.0
MAX_WINDOW_HOURS = 14.0
MAX_DRIVE_BEFORE_BREAK = 8.0
BREAK_HOURS = 0.5
OFF_DUTY_RESET_HOURS = 10.0
CYCLE_LIMIT_HOURS = 70.0
FUEL_EVERY_MILES = 1000.0
FUEL_HOURS = 0.5
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
# Start each new duty day at 06:00 for readable logs
DAY_START_HOUR = 6


@dataclass
class Segment:
    status: Status
    start: datetime
    end: datetime
    remark: str = ""
    location: str = ""
    miles: float = 0.0

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass
class Stop:
    kind: str  # start | pickup | fuel | rest_break | overnight | dropoff | end
    label: str
    lat: float
    lon: float
    time: datetime
    duration_hours: float
    miles_from_start: float


@dataclass
class PlannerState:
    now: datetime
    cycle_used: float
    window_start: datetime | None = None
    driving_in_window: float = 0.0
    driving_since_break: float = 0.0
    miles_since_fuel: float = 0.0
    miles_from_start: float = 0.0
    segments: list[Segment] = field(default_factory=list)
    stops: list[Stop] = field(default_factory=list)

    @property
    def window_elapsed(self) -> float:
        if self.window_start is None:
            return 0.0
        return (self.now - self.window_start).total_seconds() / 3600.0

    @property
    def cycle_remaining(self) -> float:
        return max(0.0, CYCLE_LIMIT_HOURS - self.cycle_used)


def _round_hours(h: float) -> float:
    return round(h * 4) / 4  # nearest 15 minutes for log grid friendliness


def plan_trip(
    *,
    current: dict[str, Any],
    pickup: dict[str, Any],
    dropoff: dict[str, Any],
    current_cycle_used: float,
    route: dict[str, Any],
    start_date: date | None = None,
) -> dict[str, Any]:
    """
    Build a HOS-compliant itinerary and daily log sheets.

    `route` must include distance_miles, average_speed_mph, geometry, legs
    for points [current, pickup, dropoff].
    """
    if current_cycle_used < 0 or current_cycle_used >= CYCLE_LIMIT_HOURS:
        raise ValueError("current_cycle_used must be in [0, 70)")

    speed = max(25.0, min(70.0, route.get("average_speed_mph") or 55.0))
    geometry = route["geometry"]
    legs = route["legs"]

    # Leg 0: current → pickup, Leg 1: pickup → dropoff
    if len(legs) < 2:
        raise ValueError("Expected two route legs (current→pickup, pickup→dropoff)")

    trip_start_day = start_date or date.today()
    # Begin at 06:00 with prior off-duty from midnight (clean first log sheet)
    start_dt = datetime.combine(trip_start_day, datetime.min.time()).replace(
        hour=DAY_START_HOUR
    )

    state = PlannerState(now=start_dt, cycle_used=float(current_cycle_used))

    # Pre-duty off time on first sheet (midnight → 06:00)
    midnight = datetime.combine(trip_start_day, datetime.min.time())
    if start_dt > midnight:
        state.segments.append(
            Segment(
                status="off_duty",
                start=midnight,
                end=start_dt,
                remark="Off duty before trip start",
                location=current["display_name"],
            )
        )

    state.stops.append(
        Stop(
            kind="start",
            label="Current location",
            lat=current["lat"],
            lon=current["lon"],
            time=state.now,
            duration_hours=0,
            miles_from_start=0,
        )
    )

    # --- Drive current → pickup ---
    _drive_leg(
        state,
        miles=legs[0]["distance_miles"],
        speed_mph=speed,
        geometry=geometry,
        route_start_fraction=0.0,
        route_end_fraction=legs[0]["distance_miles"] / route["distance_miles"]
        if route["distance_miles"]
        else 0.5,
        destination_label=pickup["display_name"],
        purpose="En route to pickup",
    )

    # Pickup (1h on-duty)
    _ensure_can_be_on_duty(state, PICKUP_HOURS, location=pickup["display_name"])
    _add_on_duty(
        state,
        hours=PICKUP_HOURS,
        remark="Pickup / loading",
        location=pickup["display_name"],
        stop_kind="pickup",
        lat=pickup["lat"],
        lon=pickup["lon"],
    )

    # --- Drive pickup → dropoff ---
    pickup_frac = (
        legs[0]["distance_miles"] / route["distance_miles"]
        if route["distance_miles"]
        else 0.5
    )
    _drive_leg(
        state,
        miles=legs[1]["distance_miles"],
        speed_mph=speed,
        geometry=geometry,
        route_start_fraction=pickup_frac,
        route_end_fraction=1.0,
        destination_label=dropoff["display_name"],
        purpose="En route to dropoff",
    )

    # Dropoff (1h on-duty)
    _ensure_can_be_on_duty(state, DROPOFF_HOURS, location=dropoff["display_name"])
    _add_on_duty(
        state,
        hours=DROPOFF_HOURS,
        remark="Dropoff / unloading",
        location=dropoff["display_name"],
        stop_kind="dropoff",
        lat=dropoff["lat"],
        lon=dropoff["lon"],
    )

    state.stops.append(
        Stop(
            kind="end",
            label="Trip complete",
            lat=dropoff["lat"],
            lon=dropoff["lon"],
            time=state.now,
            duration_hours=0,
            miles_from_start=state.miles_from_start,
        )
    )

    # Fill remaining day to midnight as off-duty for a complete final sheet
    _pad_to_midnight_off(state, location=dropoff["display_name"])

    daily_logs = build_daily_logs(
        state.segments,
        initial_cycle_used=float(current_cycle_used),
        origin_label=_short_place(current["display_name"]),
        dest_label=_short_place(dropoff["display_name"]),
    )

    total_driving = sum(s.hours for s in state.segments if s.status == "driving")
    total_on_duty = sum(
        s.hours for s in state.segments if s.status in ("driving", "on_duty")
    )

    return {
        "summary": {
            "total_miles": round(state.miles_from_start, 1),
            "route_miles": round(route["distance_miles"], 1),
            "average_speed_mph": round(speed, 1),
            "total_driving_hours": round(total_driving, 2),
            "total_on_duty_hours": round(total_on_duty, 2),
            "days": len(daily_logs),
            "cycle_used_start": round(float(current_cycle_used), 2),
            "cycle_used_end": round(state.cycle_used, 2),
            "cycle_remaining_end": round(max(0.0, CYCLE_LIMIT_HOURS - state.cycle_used), 2),
            "fuel_stops": sum(1 for s in state.stops if s.kind == "fuel"),
            "rest_breaks": sum(1 for s in state.stops if s.kind == "rest_break"),
            "overnights": sum(1 for s in state.stops if s.kind == "overnight"),
        },
        "stops": [_stop_dict(s) for s in state.stops],
        "segments": [_segment_dict(s) for s in state.segments],
        "daily_logs": daily_logs,
        "route_geometry": geometry,
        "locations": {
            "current": current,
            "pickup": pickup,
            "dropoff": dropoff,
        },
    }


def _short_place(name: str) -> str:
    parts = [p.strip() for p in name.split(",")]
    if len(parts) >= 2:
        return f"{parts[0]}, {parts[1]}"
    return name[:48]


def _drive_leg(
    state: PlannerState,
    *,
    miles: float,
    speed_mph: float,
    geometry: list[list[float]],
    route_start_fraction: float,
    route_end_fraction: float,
    destination_label: str,
    purpose: str,
) -> None:
    remaining = miles
    if miles <= 0:
        return

    while remaining > 1e-6:
        _ensure_ready_to_drive(state, location=destination_label)

        # How far can we drive right now?
        drive_cap = MAX_DRIVE_HOURS - state.driving_in_window
        window_cap = MAX_WINDOW_HOURS - state.window_elapsed
        break_cap = MAX_DRIVE_BEFORE_BREAK - state.driving_since_break
        cycle_cap = state.cycle_remaining
        fuel_miles_left = FUEL_EVERY_MILES - state.miles_since_fuel

        hours_cap = min(drive_cap, window_cap, break_cap, cycle_cap)
        if hours_cap <= 1e-6:
            # Need break or overnight — handled by ensure / break helpers
            if state.driving_since_break >= MAX_DRIVE_BEFORE_BREAK - 1e-6:
                _take_rest_break(state, geometry, route_start_fraction, route_end_fraction, miles, remaining)
                continue
            _take_overnight(state, geometry, route_start_fraction, route_end_fraction, miles, remaining)
            continue

        miles_cap_by_time = hours_cap * speed_mph
        miles_this = min(remaining, miles_cap_by_time, fuel_miles_left)

        if miles_this <= 1e-6:
            # Hit fuel threshold exactly
            _fuel_stop(state, geometry, route_start_fraction, route_end_fraction, miles, remaining)
            continue

        hours = miles_this / speed_mph
        # Snap to 15-min increments when close for cleaner logs
        hours = max(0.25, _round_hours(hours)) if hours >= 0.2 else hours
        # Recompute miles from snapped hours without overshooting remaining
        miles_this = min(remaining, hours * speed_mph)

        frac = _fraction_for_miles(
            route_start_fraction, route_end_fraction, miles, miles - remaining + miles_this
        )
        lat, lon = point_along_geometry(geometry, frac)

        start = state.now
        end = start + timedelta(hours=hours)
        state.segments.append(
            Segment(
                status="driving",
                start=start,
                end=end,
                remark=purpose,
                location=destination_label,
                miles=miles_this,
            )
        )
        state.now = end
        state.driving_in_window += hours
        state.driving_since_break += hours
        state.miles_since_fuel += miles_this
        state.miles_from_start += miles_this
        state.cycle_used += hours
        remaining -= miles_this

        # Mandatory break after 8h driving
        if state.driving_since_break >= MAX_DRIVE_BEFORE_BREAK - 1e-6 and remaining > 1e-6:
            _take_rest_break(state, geometry, route_start_fraction, route_end_fraction, miles, remaining)
            continue

        # Fuel stop
        if state.miles_since_fuel >= FUEL_EVERY_MILES - 1e-6 and remaining > 1e-6:
            _fuel_stop(state, geometry, route_start_fraction, route_end_fraction, miles, remaining)
            continue

        # Window / drive / cycle exhausted
        if (
            state.driving_in_window >= MAX_DRIVE_HOURS - 1e-6
            or state.window_elapsed >= MAX_WINDOW_HOURS - 1e-6
            or state.cycle_remaining <= 1e-6
        ) and remaining > 1e-6:
            _take_overnight(state, geometry, route_start_fraction, route_end_fraction, miles, remaining)


def _fraction_for_miles(
    start_f: float, end_f: float, leg_miles: float, miles_into_leg: float
) -> float:
    if leg_miles <= 0:
        return end_f
    t = max(0.0, min(1.0, miles_into_leg / leg_miles))
    return start_f + t * (end_f - start_f)


def _ensure_ready_to_drive(state: PlannerState, location: str) -> None:
    """Start a duty window if needed; overnight if cycle/window blocks driving."""
    if state.window_start is None:
        state.window_start = state.now
        state.driving_in_window = 0.0
        state.driving_since_break = 0.0
        return

    if state.cycle_remaining <= 0.25:
        # 34-hour restart to continue (assessment allows multi-day long hauls)
        _take_restart_34(state, location)
        return

    if (
        state.driving_in_window >= MAX_DRIVE_HOURS - 1e-6
        or state.window_elapsed >= MAX_WINDOW_HOURS - 1e-6
    ):
        # Caller will overnight; nothing here
        return


def _ensure_can_be_on_duty(state: PlannerState, hours: float, location: str) -> None:
    """Make sure we can place on-duty time (pickup/dropoff/fuel) within cycle/window."""
    if state.window_start is None:
        state.window_start = state.now

    # Pickup/dropoff consume window and cycle but not driving limits.
    # If window would exceed 14h, take overnight first.
    if state.window_elapsed + hours > MAX_WINDOW_HOURS + 1e-6:
        # Overnight at current position (already at facility)
        _add_off_duty_reset(state, location=location, kind="overnight")
        state.window_start = state.now
        state.driving_in_window = 0.0
        state.driving_since_break = 0.0

    if state.cycle_remaining < hours:
        _take_restart_34(state, location)


def _add_on_duty(
    state: PlannerState,
    *,
    hours: float,
    remark: str,
    location: str,
    stop_kind: str,
    lat: float,
    lon: float,
) -> None:
    if state.window_start is None:
        state.window_start = state.now
    start = state.now
    end = start + timedelta(hours=hours)
    state.segments.append(
        Segment(status="on_duty", start=start, end=end, remark=remark, location=location)
    )
    state.now = end
    state.cycle_used += hours
    # On-duty not driving counts as break interruption for the 8h driving rule
    state.driving_since_break = 0.0
    state.stops.append(
        Stop(
            kind=stop_kind,
            label=remark,
            lat=lat,
            lon=lon,
            time=start,
            duration_hours=hours,
            miles_from_start=state.miles_from_start,
        )
    )


def _take_rest_break(
    state: PlannerState,
    geometry: list[list[float]],
    start_f: float,
    end_f: float,
    leg_miles: float,
    remaining: float,
) -> None:
    miles_into = leg_miles - remaining
    frac = _fraction_for_miles(start_f, end_f, leg_miles, miles_into)
    lat, lon = point_along_geometry(geometry, frac)
    # 30-min break can be off-duty; does NOT extend 14h window
    start = state.now
    end = start + timedelta(hours=BREAK_HOURS)
    state.segments.append(
        Segment(
            status="off_duty",
            start=start,
            end=end,
            remark="30-minute rest break (HOS)",
            location=f"Break @ {lat:.3f}, {lon:.3f}",
        )
    )
    state.now = end
    state.driving_since_break = 0.0
    # Off-duty break does not add to cycle
    state.stops.append(
        Stop(
            kind="rest_break",
            label="30-min rest break",
            lat=lat,
            lon=lon,
            time=start,
            duration_hours=BREAK_HOURS,
            miles_from_start=state.miles_from_start,
        )
    )


def _fuel_stop(
    state: PlannerState,
    geometry: list[list[float]],
    start_f: float,
    end_f: float,
    leg_miles: float,
    remaining: float,
) -> None:
    miles_into = leg_miles - remaining
    frac = _fraction_for_miles(start_f, end_f, leg_miles, miles_into)
    lat, lon = point_along_geometry(geometry, frac)
    _ensure_can_be_on_duty(state, FUEL_HOURS, location=f"Fuel stop @ {lat:.3f}, {lon:.3f}")
    _add_on_duty(
        state,
        hours=FUEL_HOURS,
        remark="Fueling",
        location=f"Fuel stop @ {lat:.3f}, {lon:.3f}",
        stop_kind="fuel",
        lat=lat,
        lon=lon,
    )
    state.miles_since_fuel = 0.0


def _take_overnight(
    state: PlannerState,
    geometry: list[list[float]],
    start_f: float,
    end_f: float,
    leg_miles: float,
    remaining: float,
) -> None:
    miles_into = leg_miles - remaining
    frac = _fraction_for_miles(start_f, end_f, leg_miles, miles_into)
    lat, lon = point_along_geometry(geometry, frac)
    loc = f"Overnight rest @ {lat:.3f}, {lon:.3f}"
    _add_off_duty_reset(state, location=loc, kind="overnight", lat=lat, lon=lon)
    state.window_start = state.now
    state.driving_in_window = 0.0
    state.driving_since_break = 0.0


def _take_restart_34(state: PlannerState, location: str) -> None:
    """34-hour restart resets the 70-hour cycle."""
    start = state.now
    end = start + timedelta(hours=34)
    state.segments.append(
        Segment(
            status="off_duty",
            start=start,
            end=end,
            remark="34-hour restart (cycle reset)",
            location=location,
        )
    )
    state.now = end
    state.cycle_used = 0.0
    state.window_start = None
    state.driving_in_window = 0.0
    state.driving_since_break = 0.0
    state.stops.append(
        Stop(
            kind="overnight",
            label="34-hour restart",
            lat=0,
            lon=0,
            time=start,
            duration_hours=34,
            miles_from_start=state.miles_from_start,
        )
    )
    # Align next duty to 06:00
    _align_to_day_start(state, location)


def _add_off_duty_reset(
    state: PlannerState,
    *,
    location: str,
    kind: str,
    lat: float = 0.0,
    lon: float = 0.0,
) -> None:
    start = state.now
    end = start + timedelta(hours=OFF_DUTY_RESET_HOURS)
    state.segments.append(
        Segment(
            status="off_duty",
            start=start,
            end=end,
            remark="10-hour off-duty reset",
            location=location,
        )
    )
    state.now = end
    state.window_start = None
    state.driving_in_window = 0.0
    state.driving_since_break = 0.0
    if kind == "overnight":
        state.stops.append(
            Stop(
                kind="overnight",
                label="10-hour overnight rest",
                lat=lat,
                lon=lon,
                time=start,
                duration_hours=OFF_DUTY_RESET_HOURS,
                miles_from_start=state.miles_from_start,
            )
        )
    _align_to_day_start(state, location)


def _align_to_day_start(state: PlannerState, location: str) -> None:
    """If we finish overnight mid-morning awkwardly, pad off-duty to next 06:00."""
    target = state.now.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
    if state.now.hour >= DAY_START_HOUR and not (
        state.now.hour == DAY_START_HOUR and state.now.minute == 0
    ):
        target = target + timedelta(days=1)
    if state.now < target:
        state.segments.append(
            Segment(
                status="off_duty",
                start=state.now,
                end=target,
                remark="Off duty until duty day start",
                location=location,
            )
        )
        state.now = target


def _pad_to_midnight_off(state: PlannerState, location: str) -> None:
    midnight = (state.now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # If already exactly midnight, nothing to do
    if state.now.hour == 0 and state.now.minute == 0 and state.now.second == 0:
        return
    # Pad only within the same calendar day remainder
    end_of_day = state.now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    if state.now < end_of_day:
        state.segments.append(
            Segment(
                status="off_duty",
                start=state.now,
                end=end_of_day,
                remark="Off duty — end of day",
                location=location,
            )
        )
        state.now = end_of_day


def build_daily_logs(
    segments: list[Segment],
    *,
    initial_cycle_used: float,
    origin_label: str,
    dest_label: str,
) -> list[dict[str, Any]]:
    """Split segments into midnight-bounded daily log sheets with grid data."""
    if not segments:
        return []

    # Group by calendar date
    by_day: dict[date, list[Segment]] = {}
    for seg in segments:
        cursor = seg.start
        while cursor < seg.end:
            day = cursor.date()
            day_end = datetime.combine(day, datetime.min.time()) + timedelta(days=1)
            slice_end = min(seg.end, day_end)
            piece = Segment(
                status=seg.status,
                start=cursor,
                end=slice_end,
                remark=seg.remark,
                location=seg.location,
                miles=seg.miles * ((slice_end - cursor) / (seg.end - seg.start))
                if seg.end != seg.start and seg.miles
                else 0.0,
            )
            by_day.setdefault(day, []).append(piece)
            cursor = slice_end

    days_sorted = sorted(by_day.keys())
    logs = []
    # Rolling on-duty history for 8-day recap (hours per day)
    on_duty_by_day: dict[date, float] = {}
    # Seed prior cycle: distribute initial_cycle_used across prior 7 days equally
    # so recap math is sensible without inventing fake history detail
    prior = initial_cycle_used
    for i in range(1, 8):
        d = days_sorted[0] - timedelta(days=i)
        share = prior / 7.0 if prior else 0.0
        on_duty_by_day[d] = share

    running_cycle = initial_cycle_used

    for day in days_sorted:
        day_segs = by_day[day]
        totals = {"off_duty": 0.0, "sleeper": 0.0, "driving": 0.0, "on_duty": 0.0}
        grid = []
        remarks = []
        miles = 0.0
        for seg in day_segs:
            totals[seg.status] += seg.hours
            miles += seg.miles
            start_min = seg.start.hour * 60 + seg.start.minute
            end_min = seg.end.hour * 60 + seg.end.minute
            if end_min == 0 and seg.end.date() > day:
                end_min = 24 * 60
            grid.append(
                {
                    "status": seg.status,
                    "start_minute": start_min,
                    "end_minute": end_min,
                    "hours": round(seg.hours, 2),
                }
            )
            remark_l = (seg.remark or "").lower()
            notable = seg.status in ("driving", "on_duty", "sleeper") or any(
                k in remark_l
                for k in ("break", "restart", "overnight", "10-hour", "fuel", "pickup", "dropoff")
            )
            if seg.remark and notable:
                remarks.append(
                    {
                        "time": seg.start.strftime("%H:%M"),
                        "text": seg.remark,
                        "location": seg.location,
                        "status": seg.status,
                    }
                )

        on_duty_today = totals["driving"] + totals["on_duty"]
        on_duty_by_day[day] = on_duty_today
        running_cycle += on_duty_today

        # 70hr/8day recap: last 8 days including today
        last_8 = [on_duty_by_day.get(day - timedelta(days=i), 0.0) for i in range(8)]
        total_8 = sum(last_8)
        # A in form: last 7 days including today
        last_7 = sum(last_8[:7])
        available_tomorrow = max(0.0, CYCLE_LIMIT_HOURS - last_7)

        # Deduplicate remarks
        seen = set()
        unique_remarks = []
        for r in remarks:
            key = (r["time"], r["text"])
            if key not in seen:
                seen.add(key)
                unique_remarks.append(r)

        logs.append(
            {
                "date": day.isoformat(),
                "from": origin_label,
                "to": dest_label,
                "total_miles_driving": round(
                    sum(s.miles for s in day_segs if s.status == "driving"), 1
                ),
                "total_mileage": round(miles, 1),
                "grid": grid,
                "totals": {k: round(v, 2) for k, v in totals.items()},
                "on_duty_hours_today": round(on_duty_today, 2),
                "remarks": unique_remarks,
                "recap_70": {
                    "A_hours_last_7_including_today": round(last_7, 2),
                    "B_hours_available_tomorrow": round(available_tomorrow, 2),
                    "C_hours_last_8_including_today": round(total_8, 2),
                },
                "carrier": "Spotter Demo Carrier",
                "main_office": "Assessment — HOS Trip Planner",
                "home_terminal": "Home Terminal",
            }
        )

    return logs


def _segment_dict(s: Segment) -> dict[str, Any]:
    return {
        "status": s.status,
        "start": s.start.isoformat(),
        "end": s.end.isoformat(),
        "hours": round(s.hours, 2),
        "remark": s.remark,
        "location": s.location,
        "miles": round(s.miles, 2),
    }


def _stop_dict(s: Stop) -> dict[str, Any]:
    return {
        "kind": s.kind,
        "label": s.label,
        "lat": s.lat,
        "lon": s.lon,
        "time": s.time.isoformat(),
        "duration_hours": s.duration_hours,
        "miles_from_start": round(s.miles_from_start, 1),
    }

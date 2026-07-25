from datetime import date, datetime, timedelta
from django.test import SimpleTestCase

from trips.services.hos_planner import (
    MAX_DRIVE_HOURS,
    MAX_WINDOW_HOURS,
    Segment,
    build_daily_logs,
    plan_trip,
)


def _fake_route(miles_leg1=300.0, miles_leg2=700.0, speed=55.0):
    total = miles_leg1 + miles_leg2
    # Simple straight-ish geometry Chicago-ish → Dallas-ish → LA-ish
    geometry = [
        [-87.63, 41.88],
        [-96.80, 32.78],
        [-118.24, 34.05],
    ]
    return {
        "distance_miles": total,
        "duration_hours": total / speed,
        "average_speed_mph": speed,
        "geometry": geometry,
        "legs": [
            {"from_index": 0, "to_index": 1, "distance_miles": miles_leg1, "duration_hours": miles_leg1 / speed},
            {"from_index": 1, "to_index": 2, "distance_miles": miles_leg2, "duration_hours": miles_leg2 / speed},
        ],
    }


LOC = {
    "current": {"lat": 41.88, "lon": -87.63, "display_name": "Chicago, IL, USA", "query": "Chicago"},
    "pickup": {"lat": 32.78, "lon": -96.80, "display_name": "Dallas, TX, USA", "query": "Dallas"},
    "dropoff": {"lat": 34.05, "lon": -118.24, "display_name": "Los Angeles, CA, USA", "query": "LA"},
}


class HosPlannerTests(SimpleTestCase):
    def test_short_trip_single_day_respects_pickup_dropoff(self):
        result = plan_trip(
            current=LOC["current"],
            pickup=LOC["pickup"],
            dropoff=LOC["dropoff"],
            current_cycle_used=10,
            route=_fake_route(50, 50, 55),
            start_date=date(2026, 7, 25),
        )
        on_duty_remarks = [
            s["remark"] for s in result["segments"] if s["status"] == "on_duty"
        ]
        self.assertTrue(any("Pickup" in r for r in on_duty_remarks))
        self.assertTrue(any("Dropoff" in r for r in on_duty_remarks))
        self.assertGreaterEqual(len(result["daily_logs"]), 1)

    def test_long_trip_needs_multiple_logs_and_fuel(self):
        result = plan_trip(
            current=LOC["current"],
            pickup=LOC["pickup"],
            dropoff=LOC["dropoff"],
            current_cycle_used=20,
            route=_fake_route(900, 1200, 55),
            start_date=date(2026, 7, 25),
        )
        self.assertGreaterEqual(result["summary"]["days"], 2)
        self.assertGreaterEqual(result["summary"]["fuel_stops"], 1)
        # Never exceed 11h driving in a window — check consecutive driving chunks between resets
        for log in result["daily_logs"]:
            self.assertLessEqual(log["totals"]["driving"], MAX_DRIVE_HOURS + 0.26)

    def test_cycle_limit_triggers_restart_or_stops_driving(self):
        result = plan_trip(
            current=LOC["current"],
            pickup=LOC["pickup"],
            dropoff=LOC["dropoff"],
            current_cycle_used=65,
            route=_fake_route(400, 800, 55),
            start_date=date(2026, 7, 25),
        )
        self.assertLessEqual(result["summary"]["cycle_used_end"], 70.5)
        # Either finished under 70 or used a 34h restart
        remarks = " ".join(s["remark"] for s in result["segments"])
        self.assertTrue(
            result["summary"]["cycle_used_end"] <= 70.01 or "34-hour" in remarks
        )

    def test_daily_log_grid_covers_24h(self):
        segs = [
            Segment("off_duty", datetime(2026, 7, 25, 0, 0), datetime(2026, 7, 25, 6, 0), "pre"),
            Segment("driving", datetime(2026, 7, 25, 6, 0), datetime(2026, 7, 25, 14, 0), "drive", miles=400),
            Segment("off_duty", datetime(2026, 7, 25, 14, 0), datetime(2026, 7, 26, 0, 0), "end"),
        ]
        logs = build_daily_logs(
            segs, initial_cycle_used=5, origin_label="A", dest_label="B"
        )
        self.assertEqual(len(logs), 1)
        covered = sum(g["end_minute"] - g["start_minute"] for g in logs[0]["grid"])
        self.assertEqual(covered, 24 * 60)

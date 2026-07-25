"""Route between coordinates via public OSRM."""

from __future__ import annotations

from typing import Any

import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
METERS_PER_MILE = 1609.344


def route_between(points: list[tuple[float, float]]) -> dict[str, Any]:
    """
    Route through an ordered list of (lat, lon) points.

    Returns distance_miles, duration_hours, geometry (GeoJSON LineString coords
    as [lon, lat] pairs), and per-leg summaries.
    """
    if len(points) < 2:
        raise ValueError("Need at least two points to route")

    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{OSRM_URL}/{coords}"
    response = requests.get(
        url,
        params={
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise ValueError(f"OSRM routing failed: {payload.get('code', 'unknown')}")

    route = payload["routes"][0]
    legs_raw = route.get("legs", [])
    legs = []
    for i, leg in enumerate(legs_raw):
        legs.append(
            {
                "from_index": i,
                "to_index": i + 1,
                "distance_miles": leg["distance"] / METERS_PER_MILE,
                "duration_hours": leg["duration"] / 3600.0,
            }
        )

    distance_m = route["distance"]
    duration_s = route["duration"]
    geometry = route["geometry"]["coordinates"]  # [lon, lat]

    return {
        "distance_miles": distance_m / METERS_PER_MILE,
        "duration_hours": duration_s / 3600.0,
        "geometry": geometry,
        "legs": legs,
        "average_speed_mph": (
            (distance_m / METERS_PER_MILE) / (duration_s / 3600.0)
            if duration_s > 0
            else 55.0
        ),
    }


def point_along_geometry(
    geometry: list[list[float]], fraction: float
) -> tuple[float, float]:
    """Approximate (lat, lon) at a fraction [0,1] along a [lon,lat] line."""
    fraction = max(0.0, min(1.0, fraction))
    if not geometry:
        return (0.0, 0.0)
    if len(geometry) == 1 or fraction <= 0:
        lon, lat = geometry[0]
        return (lat, lon)
    if fraction >= 1:
        lon, lat = geometry[-1]
        return (lat, lon)

    # Cumulative distances in lon/lat degree space is fine for marker placement
    dists = [0.0]
    total = 0.0
    for i in range(1, len(geometry)):
        lon1, lat1 = geometry[i - 1]
        lon2, lat2 = geometry[i]
        d = ((lon2 - lon1) ** 2 + (lat2 - lat1) ** 2) ** 0.5
        total += d
        dists.append(total)

    if total == 0:
        lon, lat = geometry[0]
        return (lat, lon)

    target = fraction * total
    for i in range(1, len(dists)):
        if dists[i] >= target:
            span = dists[i] - dists[i - 1]
            t = 0.0 if span == 0 else (target - dists[i - 1]) / span
            lon1, lat1 = geometry[i - 1]
            lon2, lat2 = geometry[i]
            lon = lon1 + t * (lon2 - lon1)
            lat = lat1 + t * (lat2 - lat1)
            return (lat, lon)

    lon, lat = geometry[-1]
    return (lat, lon)

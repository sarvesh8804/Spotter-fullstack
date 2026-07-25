"""Geocode place names via Photon (Komoot) with Nominatim fallback."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

USER_AGENT = "SpotterTripPlanner/1.0 (education assessment; local-dev)"
PHOTON_URL = "https://photon.komoot.io/api/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

_last_nominatim = 0.0
_nominatim_lock = threading.Lock()

_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()


def geocode(query: str) -> dict[str, Any]:
    """Return {lat, lon, display_name, query} for a free-text place."""
    key = query.strip().lower()
    with _cache_lock:
        hit = _cache.get(key)
    if hit:
        return dict(hit)

    errors: list[str] = []

    for fn in (_geocode_photon, _geocode_open_meteo, _geocode_nominatim):
        try:
            result = fn(query)
            if result:
                result["query"] = query
                with _cache_lock:
                    _cache[key] = dict(result)
                return result
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{fn.__name__}: {exc}")

    raise ValueError(
        f"Could not geocode location: {query!r} ({'; '.join(errors) or 'no results'})"
    )


def geocode_many(queries: list[str]) -> list[dict[str, Any]]:
    """Geocode several places concurrently, preserving input order."""
    with ThreadPoolExecutor(max_workers=min(4, len(queries) or 1)) as pool:
        return list(pool.map(geocode, queries))


def _geocode_photon(query: str) -> dict[str, Any] | None:
    response = requests.get(
        PHOTON_URL,
        params={"q": query, "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    features = response.json().get("features") or []
    if not features:
        return None
    feat = features[0]
    lon, lat = feat["geometry"]["coordinates"]
    props = feat.get("properties") or {}
    parts = [
        props.get("name"),
        props.get("city"),
        props.get("state"),
        props.get("country"),
    ]
    display = ", ".join(p for p in parts if p) or query
    return {"lat": float(lat), "lon": float(lon), "display_name": display}


def _geocode_open_meteo(query: str) -> dict[str, Any] | None:
    # Open-Meteo works best with city-like names
    name = query.split(",")[0].strip()
    response = requests.get(
        OPEN_METEO_URL,
        params={"name": name, "count": 5, "language": "en", "format": "json"},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None

    # Prefer a result whose admin1 / country matches leftover query tokens
    tokens = {t.strip().lower() for t in query.replace(",", " ").split() if t.strip()}
    best = results[0]
    for r in results:
        hay = " ".join(
            str(r.get(k, ""))
            for k in ("name", "admin1", "admin2", "country", "country_code")
        ).lower()
        if any(t in hay for t in tokens if len(t) > 1):
            best = r
            break

    display = ", ".join(
        p
        for p in [
            best.get("name"),
            best.get("admin1"),
            best.get("country"),
        ]
        if p
    )
    return {
        "lat": float(best["latitude"]),
        "lon": float(best["longitude"]),
        "display_name": display or query,
    }


def _geocode_nominatim(query: str) -> dict[str, Any] | None:
    global _last_nominatim
    # Nominatim's usage policy allows at most one request per second.
    with _nominatim_lock:
        elapsed = time.time() - _last_nominatim
        if elapsed < 1.05:
            time.sleep(1.05 - elapsed)
        _last_nominatim = time.time()

    response = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
    hit = data[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "display_name": hit.get("display_name", query),
    }

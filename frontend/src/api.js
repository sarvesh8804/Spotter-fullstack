const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function planTrip(payload) {
  const res = await fetch(`${API_BASE}/api/plan-trip/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

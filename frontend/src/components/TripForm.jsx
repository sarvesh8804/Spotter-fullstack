import { useState } from "react";

const EXAMPLES = [
  {
    label: "Midwest haul",
    current_location: "Chicago, IL",
    pickup_location: "Dallas, TX",
    dropoff_location: "Los Angeles, CA",
    current_cycle_used: 20,
  },
  {
    label: "East short",
    current_location: "Newark, NJ",
    pickup_location: "Philadelphia, PA",
    dropoff_location: "Baltimore, MD",
    current_cycle_used: 8,
  },
];

export default function TripForm({ onSubmit, loading, compact = false }) {
  const [form, setForm] = useState({
    current_location: "Chicago, IL",
    pickup_location: "Dallas, TX",
    dropoff_location: "Los Angeles, CA",
    current_cycle_used: 20,
  });

  function update(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      ...form,
      current_cycle_used: Number(form.current_cycle_used),
    });
  }

  return (
    <form className={`trip-form ${compact ? "compact" : ""}`} onSubmit={handleSubmit}>
      <div className="form-grid">
        <label>
          <span>Current</span>
          <input
            required
            value={form.current_location}
            onChange={(e) => update("current_location", e.target.value)}
            placeholder="City, State"
          />
        </label>
        <label>
          <span>Pickup</span>
          <input
            required
            value={form.pickup_location}
            onChange={(e) => update("pickup_location", e.target.value)}
            placeholder="City, State"
          />
        </label>
        <label>
          <span>Dropoff</span>
          <input
            required
            value={form.dropoff_location}
            onChange={(e) => update("dropoff_location", e.target.value)}
            placeholder="City, State"
          />
        </label>
        <label>
          <span>Cycle used (hrs)</span>
          <input
            required
            type="number"
            min="0"
            max="69.9"
            step="0.25"
            value={form.current_cycle_used}
            onChange={(e) => update("current_cycle_used", e.target.value)}
          />
        </label>
      </div>

      <div className="form-actions">
        <div className="example-row">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              className="chip"
              onClick={() =>
                setForm({
                  current_location: ex.current_location,
                  pickup_location: ex.pickup_location,
                  dropoff_location: ex.dropoff_location,
                  current_cycle_used: ex.current_cycle_used,
                })
              }
            >
              {ex.label}
            </button>
          ))}
        </div>
        <button type="submit" className="btn-optimizer" disabled={loading}>
          {loading ? "Planning…" : "+ Plan trip"}
        </button>
      </div>
    </form>
  );
}

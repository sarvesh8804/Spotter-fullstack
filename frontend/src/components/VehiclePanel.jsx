export default function VehiclePanel({ summary, locations, loading }) {
  const stats = summary
    ? [
        { label: "Distance", value: `${summary.route_miles} mi` },
        { label: "Driving", value: `${summary.total_driving_hours}h` },
        { label: "On duty", value: `${summary.total_on_duty_hours}h` },
        { label: "Cycle left", value: `${summary.cycle_remaining_end}h` },
      ]
    : [
        { label: "Distance", value: "—" },
        { label: "Driving", value: "—" },
        { label: "On duty", value: "—" },
        { label: "Cycle left", value: "—" },
      ];

  const routeLabel = locations
    ? `${(locations.current?.query || "").split(",")[0]} → ${(locations.dropoff?.query || "").split(",")[0]}`
    : "Awaiting plan";

  return (
    <section className="panel vehicle-panel">
      <header className="panel-head">
        <div>
          <h2>Planning</h2>
          <p>Vehicle · HOS capacity</p>
        </div>
        {summary && (
          <span className="pill-soft">
            {summary.days} day{summary.days === 1 ? "" : "s"} · {summary.fuel_stops} fuel
          </span>
        )}
      </header>

      <div className="vehicle-body">
        <div className="truck-stage">
          <img
            src="/truck-side.png"
            alt="Delivery truck"
            className={`truck-img ${loading ? "loading" : ""}`}
          />
        </div>

        <div className="vehicle-meta">
          <div className="vehicle-route">
            <span className="meta-k">Route</span>
            <strong>{routeLabel}</strong>
          </div>
          <div className="vehicle-stats">
            {stats.map((s) => (
              <div key={s.label}>
                <span className="meta-k">{s.label}</span>
                <strong>{s.value}</strong>
              </div>
            ))}
          </div>

          {summary && (
            <ul className="vehicle-orders">
              <li>
                <i className="check" />
                <div>
                  <strong>Pickup</strong>
                  <span>
                    {(locations?.pickup?.query || locations?.pickup?.display_name || "")
                      .split(",")
                      .slice(0, 2)
                      .join(",")}
                  </span>
                </div>
                <em>1h</em>
              </li>
              <li>
                <i className="check" />
                <div>
                  <strong>Dropoff</strong>
                  <span>
                    {(locations?.dropoff?.query || locations?.dropoff?.display_name || "")
                      .split(",")
                      .slice(0, 2)
                      .join(",")}
                  </span>
                </div>
                <em>1h</em>
              </li>
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

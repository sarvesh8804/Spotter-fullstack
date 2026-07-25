import { useState } from "react";
import { planTrip } from "./api";
import TripForm from "./components/TripForm";
import RouteMap from "./components/RouteMap";
import VehiclePanel from "./components/VehiclePanel";
import StopsList from "./components/StopsList";
import DutyGantt from "./components/DutyGantt";
import DailyLogSheet from "./components/DailyLogSheet";
import "./App.css";

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeLog, setActiveLog] = useState(0);
  const [selectedStop, setSelectedStop] = useState(0);
  const [mobileTab, setMobileTab] = useState("plan");

  async function handlePlan(payload) {
    setLoading(true);
    setError("");
    try {
      const data = await planTrip(payload);
      setResult(data);
      setActiveLog(0);
      setSelectedStop(0);
      setMobileTab("map");
    } catch (err) {
      setError(err.message || "Something went wrong");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <div className="logo" aria-hidden="true" />
          <div className="crumb">
            <strong>Spotter</strong>
            <span>HOS Trip Planner</span>
          </div>
        </div>

        <div className="topbar-right">
          <span className="pill">by Sarvesh Huddar</span>
          <span className="pill">70hr / 8day · FMCSA</span>
        </div>
      </header>

      <div className="planner-bar">
        <TripForm onSubmit={handlePlan} loading={loading} compact />
        {error && <p className="error-banner">{error}</p>}
      </div>

      <nav className="mobile-tabs" aria-label="Sections">
        {[
          ["plan", "Plan"],
          ["map", "Map"],
          ["truck", "Truck"],
          ["stops", "Stops"],
          ["timeline", "Timeline"],
          ["logs", "Logs"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={mobileTab === id ? "active" : ""}
            onClick={() => setMobileTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <main className={`cockpit mobile-${mobileTab}`}>
        <section className="cell map-cell">
          <RouteMap
            geometry={result?.route_geometry}
            stops={result?.stops}
            summary={result?.summary}
            locations={result?.locations}
            active={mobileTab === "map"}
          />
        </section>

        <section className="cell truck-cell">
          <VehiclePanel
            summary={result?.summary}
            locations={result?.locations}
            loading={loading}
          />
        </section>

        <section className="cell stops-cell">
          <StopsList
            stops={result?.stops}
            summary={result?.summary}
            selectedIndex={selectedStop}
            onSelect={setSelectedStop}
          />
        </section>

        <section className="cell gantt-cell">
          <DutyGantt segments={result?.segments} />
        </section>
      </main>

      <section className={`logs-dock mobile-${mobileTab}`}>
        <div className="logs-dock-head">
          <div>
            <h2>Daily log sheets</h2>
            <p>FMCSA-style grid · drawn from the HOS plan</p>
          </div>
          {result?.daily_logs?.length > 0 && (
            <div className="log-tabs">
              {result.daily_logs.map((log, i) => (
                <button
                  key={log.date}
                  type="button"
                  className={i === activeLog ? "active" : ""}
                  onClick={() => setActiveLog(i)}
                >
                  Day {i + 1}
                </button>
              ))}
            </div>
          )}
        </div>
        {result?.daily_logs?.[activeLog] ? (
          <DailyLogSheet
            log={result.daily_logs[activeLog]}
            index={activeLog}
          />
        ) : (
          <div className="logs-placeholder">
            <div className="log-preview-card">
              <strong>Drivers Daily Log</strong>
              <p>
                After planning, each calendar day gets a filled 24-hour grid —
                Off Duty, Sleeper, Driving, On Duty — plus remarks and the 70hr
                recap.
              </p>
              <ul>
                <li>Graph grid drawn from HOS segments</li>
                <li>Pickup / dropoff / fuel called out in remarks</li>
                <li>Multiple sheets for multi-day hauls</li>
              </ul>
            </div>
          </div>
        )}
      </section>

      <footer className="footer">
        <span>Django · React · OSRM · Photon · FMCSA HOS</span>
        <span>Built by Sarvesh Huddar · Spotter AI assessment</span>
      </footer>
    </div>
  );
}

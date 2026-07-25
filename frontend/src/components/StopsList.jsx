import { useEffect, useRef, useState } from "react";
import { STOP_COLORS } from "./RouteMap";

const LABELS = {
  start: "Start",
  pickup: "Pickup",
  dropoff: "Dropoff",
  fuel: "Fuel",
  rest_break: "Rest break",
  overnight: "Overnight",
  end: "Complete",
};

const PREVIEW_STOPS = [
  { kind: "start", label: "Current location", meta: "Origin" },
  { kind: "pickup", label: "Pickup · 1h on-duty", meta: "Loading" },
  { kind: "fuel", label: "Fuel every 1,000 mi", meta: "On duty" },
  { kind: "rest_break", label: "30-min rest after 8h drive", meta: "HOS" },
  { kind: "overnight", label: "10-hour off-duty reset", meta: "Rest" },
  { kind: "dropoff", label: "Dropoff · 1h on-duty", meta: "Unload" },
];

export default function StopsList({ stops, summary, selectedIndex, onSelect }) {
  const items = (stops || []).filter((s) => s.kind !== "end");
  const listRef = useRef(null);
  const [canScroll, setCanScroll] = useState(false);
  const [atBottom, setAtBottom] = useState(true);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;

    function update() {
      const overflow = el.scrollHeight > el.clientHeight + 4;
      setCanScroll(overflow);
      setAtBottom(el.scrollTop + el.clientHeight >= el.scrollHeight - 8);
    }

    update();
    el.addEventListener("scroll", update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", update);
      ro.disconnect();
    };
  }, [items.length]);

  return (
    <section className={`panel stops-panel ${canScroll ? "is-scrollable" : ""}`}>
      <header className="panel-head">
        <div>
          <h2>Trip stops</h2>
          <p>
            {items.length
              ? `${items.length} events${summary ? ` · Σ ${summary.route_miles} mi` : ""}`
              : "Pickup, fuel, rest & dropoff"}
          </p>
        </div>
        {canScroll && (
          <span className="scroll-hint">{atBottom ? "Scroll up" : "Scroll for more"}</span>
        )}
      </header>

      <div className="stops-scroll-wrap">
        <ul className="stops-list" ref={listRef}>
          {!items.length &&
            PREVIEW_STOPS.map((stop) => (
              <li key={stop.kind}>
                <div className="stop-card preview">
                  <span
                    className="stop-dot"
                    style={{ background: STOP_COLORS[stop.kind] || "#9aa3b2" }}
                  />
                  <div className="stop-main">
                    <strong>{LABELS[stop.kind] || stop.kind}</strong>
                    <span>{stop.label}</span>
                  </div>
                  <div className="stop-meta">
                    <em>{stop.meta}</em>
                  </div>
                </div>
              </li>
            ))}
          {items.map((stop, i) => {
            const active = selectedIndex === i;
            return (
              <li key={`${stop.kind}-${i}`}>
                <button
                  type="button"
                  className={`stop-card ${active ? "active" : ""}`}
                  onClick={() => onSelect?.(i)}
                >
                  <span
                    className="stop-dot"
                    style={{ background: STOP_COLORS[stop.kind] || "#9aa3b2" }}
                  />
                  <div className="stop-main">
                    <strong>{LABELS[stop.kind] || stop.kind}</strong>
                    <span>{stop.label}</span>
                  </div>
                  <div className="stop-meta">
                    <time>
                      {new Date(stop.time).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                    <em>
                      {stop.miles_from_start} mi
                      {stop.duration_hours > 0 ? ` · ${stop.duration_hours}h` : ""}
                    </em>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
        {canScroll && !atBottom && <div className="stops-fade" aria-hidden="true" />}
      </div>
    </section>
  );
}

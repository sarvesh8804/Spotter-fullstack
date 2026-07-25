const STATUS_ROWS = [
  { key: "off_duty", label: "Off Duty" },
  { key: "sleeper", label: "Sleeper Berth" },
  { key: "driving", label: "Driving" },
  { key: "on_duty", label: "On Duty (not driving)" },
];

const WIDTH = 900;
const HEIGHT = 520;
const GRID_X = 150;
const GRID_Y = 130;
const GRID_W = 680;
const GRID_H = 160;
const ROW_H = GRID_H / 4;

function minuteToX(minute) {
  return GRID_X + (minute / (24 * 60)) * GRID_W;
}

function statusRowY(status) {
  const idx = STATUS_ROWS.findIndex((r) => r.key === status);
  return GRID_Y + idx * ROW_H + ROW_H / 2;
}

function formatDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DailyLogSheet({ log, index }) {
  const hours = Array.from({ length: 25 }, (_, i) => i);

  return (
    <article className="log-sheet">
      <div className="log-sheet-label">Daily log · Day {index + 1}</div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="log-svg"
        role="img"
        aria-label={`Driver daily log for ${log.date}`}
      >
        <rect x="0" y="0" width={WIDTH} height={HEIGHT} fill="#f7f3ea" />
        <rect
          x="8"
          y="8"
          width={WIDTH - 16}
          height={HEIGHT - 16}
          fill="none"
          stroke="#1a2332"
          strokeWidth="2"
        />

        <text x="24" y="36" className="log-title">
          Drivers Daily Log (24 hours)
        </text>
        <text x="620" y="28" className="log-small">
          Date: {formatDate(log.date)}
        </text>
        <text x="620" y="46" className="log-tiny">
          ({log.date})
        </text>

        <text x="24" y="62" className="log-small">
          From: {log.from}
        </text>
        <text x="320" y="62" className="log-small">
          To: {log.to}
        </text>

        <text x="24" y="88" className="log-tiny">
          Total Miles Driving Today: {log.total_miles_driving}
        </text>
        <text x="280" y="88" className="log-tiny">
          Total Mileage Today: {log.total_mileage}
        </text>
        <text x="520" y="88" className="log-tiny">
          Carrier: {log.carrier}
        </text>

        {/* Grid background */}
        <rect
          x={GRID_X}
          y={GRID_Y}
          width={GRID_W}
          height={GRID_H}
          fill="#fffef8"
          stroke="#1a2332"
          strokeWidth="1.5"
        />

        {STATUS_ROWS.map((row, i) => (
          <g key={row.key}>
            <text
              x={GRID_X - 10}
              y={GRID_Y + i * ROW_H + ROW_H / 2 + 4}
              textAnchor="end"
              className="log-row-label"
            >
              {row.label}
            </text>
            <line
              x1={GRID_X}
              y1={GRID_Y + (i + 1) * ROW_H}
              x2={GRID_X + GRID_W}
              y2={GRID_Y + (i + 1) * ROW_H}
              stroke="#1a2332"
              strokeWidth={i === 3 ? 1.5 : 0.6}
              opacity={0.35}
            />
          </g>
        ))}

        {/* Hour ticks — label every 3h to avoid overlap */}
        {hours.map((h) => {
          const x = minuteToX(h * 60);
          const showLabel = h % 3 === 0;
          return (
            <g key={h}>
              <line
                x1={x}
                y1={GRID_Y}
                x2={x}
                y2={GRID_Y + GRID_H}
                stroke="#1a2332"
                strokeWidth={h % 12 === 0 ? 1.2 : 0.4}
                opacity={h % 12 === 0 ? 0.55 : 0.2}
              />
              {showLabel && (
                <text
                  x={x}
                  y={GRID_Y - 8}
                  textAnchor="middle"
                  className="log-hour"
                >
                  {h === 0 || h === 24
                    ? "Mid"
                    : h === 12
                      ? "Noon"
                      : h > 12
                        ? String(h - 12)
                        : String(h)}
                </text>
              )}
            </g>
          );
        })}

        {/* Duty line segments */}
        {log.grid.map((seg, i) => {
          const x1 = minuteToX(seg.start_minute);
          const x2 = minuteToX(seg.end_minute);
          const y = statusRowY(seg.status);
          if (x2 <= x1) return null;
          return (
            <g key={i}>
              <line
                x1={x1}
                y1={y}
                x2={x2}
                y2={y}
                stroke="#1a2332"
                strokeWidth="3.2"
                strokeLinecap="butt"
              />
              {/* vertical connectors at changes */}
              <line
                x1={x1}
                y1={GRID_Y + 2}
                x2={x1}
                y2={GRID_Y + GRID_H - 2}
                stroke="#1a2332"
                strokeWidth="1"
                opacity="0.15"
              />
            </g>
          );
        })}

        {/* Totals column */}
        <text x={GRID_X + GRID_W + 16} y={GRID_Y - 10} className="log-tiny">
          Total hours
        </text>
        {STATUS_ROWS.map((row, i) => (
          <text
            key={row.key}
            x={GRID_X + GRID_W + 16}
            y={GRID_Y + i * ROW_H + ROW_H / 2 + 4}
            className="log-total"
          >
            {(log.totals[row.key] || 0).toFixed(2)}
          </text>
        ))}

        {/* Remarks */}
        <text x="24" y="320" className="log-small">
          Remarks
        </text>
        <line x1="24" y1="326" x2="560" y2="326" stroke="#1a2332" strokeWidth="0.8" />
        {(log.remarks || []).slice(0, 6).map((r, i) => (
          <text key={i} x="24" y={348 + i * 16} className="log-remark">
            {r.time} — {r.text}
            {r.location ? ` @ ${String(r.location).slice(0, 42)}` : ""}
          </text>
        ))}

        {/* Recap */}
        <text x="580" y="320" className="log-small">
          70 Hour / 8 Day Recap
        </text>
        <text x="580" y="348" className="log-remark">
          On duty today (lines 3 &amp; 4): {log.on_duty_hours_today.toFixed(2)}
        </text>
        <text x="580" y="368" className="log-remark">
          A. Last 7 days incl. today: {log.recap_70.A_hours_last_7_including_today}
        </text>
        <text x="580" y="388" className="log-remark">
          B. Available tomorrow: {log.recap_70.B_hours_available_tomorrow}
        </text>
        <text x="580" y="408" className="log-remark">
          C. Last 8 days incl. today: {log.recap_70.C_hours_last_8_including_today}
        </text>

        <text x="24" y="490" className="log-tiny">
          Home terminal time · Generated for Spotter HOS assessment · Not a legal RODS substitute
        </text>
      </svg>
    </article>
  );
}

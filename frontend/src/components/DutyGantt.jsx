const STATUS_META = {
  off_duty: { label: "Off", color: "#c5cad3", text: "#3a4050" },
  sleeper: { label: "Sleeper", color: "#7c6cf0", text: "#fff" },
  driving: { label: "Drive", color: "#2f6fed", text: "#fff" },
  on_duty: { label: "On duty", color: "#f0a020", text: "#fff" },
};

function parseIso(iso) {
  return new Date(iso);
}

function dayKey(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function mergeSegments(segments) {
  const sorted = [...segments].sort(
    (a, b) => parseIso(a.start) - parseIso(b.start)
  );
  const out = [];
  for (const seg of sorted) {
    const last = out[out.length - 1];
    if (
      last &&
      last.status === seg.status &&
      Math.abs(parseIso(last.end) - parseIso(seg.start)) < 60_000
    ) {
      last.end = seg.end;
      last.hours = (parseIso(last.end) - parseIso(last.start)) / 3_600_000;
      if (seg.remark && !last.remark?.includes(seg.remark)) {
        last.remark = [last.remark, seg.remark].filter(Boolean).join(" · ");
      }
    } else {
      out.push({ ...seg });
    }
  }
  return out;
}

function buildDayRows(segments) {
  const merged = mergeSegments(segments);
  const byDay = new Map();

  for (const seg of merged) {
    let cursor = parseIso(seg.start);
    const end = parseIso(seg.end);
    while (cursor < end) {
      const key = dayKey(cursor);
      const [y, m, day] = key.split("-").map(Number);
      const dayStart = new Date(y, m - 1, day, 0, 0, 0, 0);
      const dayEnd = new Date(y, m - 1, day + 1, 0, 0, 0, 0);
      const sliceEnd = end < dayEnd ? end : dayEnd;
      const startMin = (cursor - dayStart) / 60_000;
      const endMin = (sliceEnd - dayStart) / 60_000;
      if (!byDay.has(key)) byDay.set(key, []);
      byDay.get(key).push({
        status: seg.status,
        remark: seg.remark,
        startMin,
        endMin,
        hours: (endMin - startMin) / 60,
      });
      cursor = sliceEnd;
    }
  }

  return [...byDay.entries()].map(([date, bars]) => ({ date, bars }));
}

const HOUR_MARKS = [0, 6, 12, 18, 24];

function TimelineTrack({ bars, preview = false }) {
  return (
    <div className={`day-track ${preview ? "preview" : ""}`}>
      <div className="day-grid" aria-hidden="true">
        {HOUR_MARKS.map((h) => (
          <i key={h} style={{ left: `${(h / 24) * 100}%` }} />
        ))}
      </div>
      {bars.map((bar, i) => {
        const meta = STATUS_META[bar.status] || STATUS_META.off_duty;
        const left = (bar.startMin / (24 * 60)) * 100;
        const width = Math.max(((bar.endMin - bar.startMin) / (24 * 60)) * 100, 0.5);
        const showLabel = width >= 14;
        return (
          <div
            key={i}
            className="day-bar"
            title={`${meta.label}${bar.remark ? `: ${bar.remark}` : ""} (${bar.hours.toFixed(1)}h)`}
            style={{
              left: `${left}%`,
              width: `${width}%`,
              background: meta.color,
              color: meta.text,
            }}
          >
            {showLabel && <span>{meta.label}</span>}
          </div>
        );
      })}
    </div>
  );
}

export default function DutyGantt({ segments }) {
  const rows = segments?.length ? buildDayRows(segments) : null;

  return (
    <section className="panel gantt-panel">
      <header className="panel-head">
        <div>
          <h2>Duty timeline</h2>
          <p>
            {rows
              ? `${rows.length} day${rows.length === 1 ? "" : "s"} · 24h per row`
              : "HOS status · 24h per day"}
          </p>
        </div>
        <ul className="gantt-legend">
          {Object.entries(STATUS_META).map(([k, v]) => (
            <li key={k}>
              <i style={{ background: v.color }} />
              {v.label === "Off" ? "Off duty" : v.label === "Drive" ? "Driving" : v.label}
            </li>
          ))}
        </ul>
      </header>

      <div className="gantt-body">
        <div className="day-axis">
          <span className="day-axis-spacer" />
          <div className="day-axis-hours">
            {HOUR_MARKS.map((h) => (
              <span
                key={h}
                style={{ left: `${(h / 24) * 100}%` }}
                className={h === 24 ? "end" : h === 0 ? "start" : ""}
              >
                {h === 0 || h === 24 ? "12a" : h === 12 ? "12p" : `${h}`}
              </span>
            ))}
          </div>
        </div>

        {!rows && (
          <div className="day-row">
            <div className="day-row-label">
              <strong>Sample</strong>
              <span>preview</span>
            </div>
            <TimelineTrack
              preview
              bars={[
                { status: "off_duty", startMin: 0, endMin: 360, hours: 6 },
                { status: "driving", startMin: 360, endMin: 840, hours: 8 },
                { status: "on_duty", startMin: 840, endMin: 900, hours: 1 },
                { status: "driving", startMin: 900, endMin: 1080, hours: 3 },
                { status: "off_duty", startMin: 1080, endMin: 1440, hours: 6 },
              ]}
            />
          </div>
        )}

        {rows?.map((row) => {
          const [y, m, day] = row.date.split("-").map(Number);
          const d = new Date(y, m - 1, day);
          return (
            <div className="day-row" key={row.date}>
              <div className="day-row-label">
                <strong>
                  {d.toLocaleDateString(undefined, {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  })}
                </strong>
                <span>{row.date}</span>
              </div>
              <TimelineTrack bars={row.bars} />
            </div>
          );
        })}

        {!rows && (
          <p className="gantt-preview-note">
            Example day — plan a trip for live HOS bars
          </p>
        )}
      </div>
    </section>
  );
}

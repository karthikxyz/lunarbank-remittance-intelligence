"use client";

import { useMemo, useState } from "react";

import type { Analytics, Corridor, Processor } from "./types";

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const compact = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const number = new Intl.NumberFormat("en-US");
const shortDate = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});
const fullDate = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

function asUtcDate(value: string) {
  return new Date(`${value}T00:00:00Z`);
}

function periodLabel(period: Analytics["period"]) {
  const start = asUtcDate(period.start);
  const end = asUtcDate(period.end);
  if (start.getUTCMonth() === end.getUTCMonth()) {
    return `${shortDate.format(start)}–${end.getUTCDate()}, ${end.getUTCFullYear()}`;
  }
  return `${shortDate.format(start)}–${fullDate.format(end)}`;
}

function signed(value: number, suffix: string) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}${suffix}`;
}

function ArrowIcon() {
  return <span aria-hidden="true">↗</span>;
}

function corridorLabel(value: string) {
  return value.replace("->", " → ");
}

function SparkBars({ values }: { values: Analytics["daily_trend"] }) {
  const max = Math.max(...values.map((item) => item.take_rate), 1);
  const min = Math.min(...values.map((item) => item.take_rate));
  const spread = Math.max(max - min, max * 0.04);

  return (
    <div className="spark" aria-label="Daily effective take rate for the last 14 days">
      {values.map((item) => {
        const relativeHeight = 25 + ((item.take_rate - min) / spread) * 75;
        return (
          <i
            key={item.date}
            title={`${fullDate.format(asUtcDate(item.date))}: ${item.take_rate.toFixed(2)}%`}
            style={{ height: `${Math.min(100, relativeHeight)}%` }}
          />
        );
      })}
    </div>
  );
}

function Sidebar({ data }: { data: Analytics }) {
  const refreshedAt = new Date(data.generated_at).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="moon">L</div>
        <span>LunarBank</span>
      </div>
      <nav aria-label="Main navigation">
        <a className="active" href="#overview"><span>⌁</span> Cost overview</a>
        <a href="#corridors"><span>⇄</span> Corridors</a>
        <a href="#processors"><span>◈</span> Processors</a>
        <a href="#recommendations">
          <span>◎</span> Recommendations <b>{data.summary.inefficient_corridors}</b>
        </a>
      </nav>
      <div className="sidebar-note">
        <small>DATA QUALITY</small>
        <strong>{data.summary.completion_rate.toFixed(1)}% completed</strong>
        <p>{number.format(data.summary.input_transactions)} validated rows</p>
        <p>Data through · {refreshedAt}</p>
      </div>
      <div className="profile">
        <div>AM</div>
        <p><strong>Ana Morales</strong><small>Operations lead</small></p>
        <span>•••</span>
      </div>
    </aside>
  );
}

function SummaryBanner({ data }: { data: Analytics }) {
  const trend = data.daily_trend.slice(-14);
  const change = data.summary.take_rate_change_bps;
  const comparisonAvailable = data.summary.comparison_available;
  const trendClass = change > 0 ? "negative" : change < 0 ? "positive" : "neutral";

  return (
    <section className="pulse" aria-label="Executive summary">
      <div className="pulse-copy">
        <span className="live">MONTHLY OPTIMIZATION CEILING</span>
        <h2>{money.format(data.summary.optimization_savings)}</h2>
        <p>if every transfer matched the best observed corridor rate</p>
        <div className="pulse-detail">
          <strong>{money.format(data.summary.actionable_savings)}</strong> tied to {" "}
          <strong>{data.summary.inefficient_corridors} flagged routes</strong>
          <span>·</span>
          <strong>
            {(data.summary.optimization_savings / data.summary.total_cost * 100).toFixed(1)}%
          </strong> of cost
        </div>
      </div>
      <div className="pulse-chart">
        <div>
          <small>14-DAY TAKE-RATE SIGNAL</small>
          <strong>
            {comparisonAvailable ? "vs prior 7d " : "Awaiting 14 days "}
            {comparisonAvailable && (
              <em className={trendClass}>{signed(change, " bps")}</em>
            )}
          </strong>
        </div>
        <SparkBars values={trend} />
      </div>
      <a href="#recommendations">Review actions <ArrowIcon /></a>
    </section>
  );
}

function Metrics({ data }: { data: Analytics }) {
  const tpvChange = data.summary.tpv_change_pct;
  const rateChange = data.summary.take_rate_change_bps;
  const comparisonAvailable = data.summary.comparison_available;

  return (
    <section className="metrics" aria-label="Key metrics">
      <article>
        <small>TOTAL TPV</small>
        <strong>{money.format(data.summary.tpv)}</strong>
        <p>
          {comparisonAvailable ? (
            <><span className={tpvChange >= 0 ? "up" : "down"}>
              {signed(tpvChange, "%")}
            </span> last 7d vs prior 7d</>
          ) : "Insufficient history for comparison"}
        </p>
      </article>
      <article>
        <small>COMPLETED TRANSFERS</small>
        <strong>{number.format(data.summary.transactions)}</strong>
        <p>
          {data.summary.completion_rate.toFixed(1)}% of {" "}
          {number.format(data.summary.input_transactions)} input rows
        </p>
      </article>
      <article>
        <small>BLENDED TAKE RATE</small>
        <strong>{data.summary.avg_take_rate.toFixed(2)}%</strong>
        <p>
          {comparisonAvailable ? (
            <><span className={rateChange > 0 ? "down" : "up"}>
              {signed(rateChange, " bps")}
            </span> last 7d vs prior 7d</>
          ) : "Insufficient history for comparison"}
        </p>
      </article>
      <article>
        <small>ALL-IN COST</small>
        <strong>{money.format(data.summary.total_cost)}</strong>
        <p>{money.format(data.summary.total_cost / data.summary.transactions)} per transfer</p>
      </article>
    </section>
  );
}

type SortOption = "cost" | "tpv" | "transactions";

function CorridorTable({
  corridors,
  selected,
  onSelect,
}: {
  corridors: Corridor[];
  selected: string;
  onSelect: (corridor: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOption>("cost");
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const filtered = useMemo(
    () => corridors
      .filter((item) => item.corridor.toLowerCase().includes(search.toLowerCase()))
      .filter((item) => !showOnlyIssues || item.is_inefficient)
      .sort((a, b) => {
        if (sort === "tpv") return b.tpv - a.tpv;
        if (sort === "transactions") return b.transactions - a.transactions;
        return b.avg_take_rate - a.avg_take_rate;
      }),
    [corridors, search, sort, showOnlyIssues],
  );

  return (
    <section className="panel corridor-panel" id="corridors">
      <div className="panel-head">
        <div>
          <p className="eyebrow">PORTFOLIO VIEW</p>
          <h2>Corridor economics</h2>
          <p>Ranked by effective take rate. Select a row to investigate.</p>
        </div>
        <div className="tools">
          <label className="search">
            <span>⌕</span>
            <input
              aria-label="Search corridors"
              placeholder="Find corridor"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <select
            aria-label="Sort corridors"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortOption)}
          >
            <option value="cost">Highest cost</option>
            <option value="tpv">Highest TPV</option>
            <option value="transactions">Most transfers</option>
          </select>
          <button
            className={showOnlyIssues ? "filter active-filter" : "filter"}
            aria-pressed={showOnlyIssues}
            onClick={() => setShowOnlyIssues(!showOnlyIssues)}
          >
            ⚑ Needs action
          </button>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Corridor</th>
              <th>Monthly TPV</th>
              <th>Transfers</th>
              <th>Take rate</th>
              <th>Best route</th>
              <th>Routing health</th>
              <th aria-label="Select" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr
                key={item.corridor}
                className={selected === item.corridor ? "selected" : ""}
                tabIndex={0}
                onClick={() => onSelect(item.corridor)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(item.corridor);
                  }
                }}
              >
                <td>
                  <div className="route">
                    <span>{item.corridor.slice(0, 3)}</span>
                    <i>→</i>
                    <span>{item.corridor.slice(-3)}</span>
                  </div>
                </td>
                <td><strong>{money.format(item.tpv)}</strong></td>
                <td>{number.format(item.transactions)}</td>
                <td>
                  <div className="rate">
                    <strong>{item.avg_take_rate.toFixed(2)}%</strong>
                    <span>
                      <i style={{ width: `${Math.min(100, item.avg_take_rate / 4 * 100)}%` }} />
                    </span>
                  </div>
                </td>
                <td><span className="processor-dot" />{item.cheapest_processor}</td>
                <td>
                  {item.is_inefficient
                    ? <span className="status risk">Action needed</span>
                    : <span className="status good">Optimized</span>}
                </td>
                <td>›</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr className="empty-row">
                <td colSpan={7}>No corridors match these filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProcessorComparison({ corridor }: { corridor: Corridor }) {
  return (
    <article className="panel processor-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">SELECTED CORRIDOR</p>
          <h2 id="selected-corridor-heading">{corridorLabel(corridor.corridor)}</h2>
          <p>{compact.format(corridor.tpv)} TPV · {number.format(corridor.transactions)} transfers</p>
        </div>
        <span className={corridor.is_inefficient ? "status risk" : "status good"}>
          {corridor.is_inefficient ? "Routing leak" : "Healthy"}
        </span>
      </div>
      <div className="processor-list">
        <div className="processor-header">
          <span>Processor</span><span>Volume</span><span>Avg cost</span><span>Take rate</span>
        </div>
        {corridor.processors.map((processor, index) => (
          <div className="processor-row" key={processor.name}>
            <div>
              <span className={`rank rank-${index + 1}`}>{index + 1}</span>
              <p>
                <strong>{processor.name}</strong>
                <small>{processor.avg_delay}h settlement</small>
              </p>
            </div>
            <div>
              <strong>{processor.volume_share.toFixed(1)}%</strong>
              <span className="share"><i style={{ width: `${processor.volume_share}%` }} /></span>
            </div>
            <strong>{money.format(processor.avg_cost)}</strong>
            <div>
              <strong>{processor.avg_take_rate.toFixed(2)}%</strong>
              {index === 0 && <small className="best">BEST</small>}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function CostComposition({
  corridor,
  source,
}: {
  corridor: Corridor;
  source: Processor;
}) {
  const sourceTotal = source.explicit_fees + source.fx_markup + source.capital_cost;

  return (
    <article className="panel composition">
      <div className="panel-head">
        <div>
          <p className="eyebrow">COST ANATOMY</p>
          <h2>Where every dollar goes</h2>
          <p>Cost mix by processor for {corridor.corridor.replace("->", " → ")}.</p>
        </div>
      </div>
      <div className="legend">
        <span><i className="fee" /> Fees</span>
        <span><i className="fx" /> FX markup</span>
        <span><i className="capital" /> Capital</span>
      </div>
      <div className="cost-bars">
        {corridor.processors.map((processor) => {
          const total = processor.explicit_fees + processor.fx_markup + processor.capital_cost;
          return (
            <div className="cost-row" key={processor.name}>
              <strong>{processor.name}</strong>
              <div className="stack">
                <i className="fee" style={{ width: `${processor.explicit_fees / total * 100}%` }} />
                <i className="fx" style={{ width: `${processor.fx_markup / total * 100}%` }} />
                <i className="capital" style={{ width: `${processor.capital_cost / total * 100}%` }} />
              </div>
              <span>{processor.avg_take_rate.toFixed(2)}%</span>
            </div>
          );
        })}
      </div>
      <div className="insight">
        <span>!</span>
        <p>
          <strong>FX spread is the main cost driver.</strong> It represents {" "}
          {Math.round(source.fx_markup / sourceTotal * 100)}% of {source.name}’s cost
          in this corridor.
        </p>
      </div>
    </article>
  );
}

function RateWatch({ data, onSelect }: { data: Analytics; onSelect: (value: string) => void }) {
  return (
    <section className="panel rate-watch" aria-label="Processor rate alerts">
      <div>
        <p className="eyebrow">AUTOMATED RATE WATCH</p>
        <h2>{data.alerts.length ? `${data.alerts.length} cost spike detected` : "No cost spikes detected"}</h2>
        <p>
          Compares each processor route’s latest {data.alerting.window_days} days with the prior {" "}
          {data.alerting.window_days}; alerts above {data.alerting.threshold_pct}%.
        </p>
      </div>
      <div className="alert-list">
        {data.alerts.map((alert) => (
          <article key={`${alert.corridor}-${alert.processor}`}>
            <span className="alert-icon">!</span>
            <div>
              <strong>{alert.processor} · {alert.corridor.replace("->", " → ")}</strong>
              <p>
                Take rate rose from {alert.previous_take_rate.toFixed(2)}% to {" "}
                {alert.current_take_rate.toFixed(2)}% across {alert.recent_transactions} recent transfers.
              </p>
            </div>
            <b>+{alert.increase_pct.toFixed(1)}%</b>
            <button
              type="button"
              aria-label={`Inspect ${corridorLabel(alert.corridor)}`}
              onClick={() => onSelect(alert.corridor)}
            >
              Inspect
            </button>
          </article>
        ))}
        {!data.alerts.length && (
          <p className="no-alerts">
            {data.alerting.monitored_processor_routes} processor routes are within threshold.
          </p>
        )}
      </div>
    </section>
  );
}

function Recommendations({
  data,
  onSelect,
}: {
  data: Analytics;
  onSelect: (value: string) => void;
}) {
  return (
    <section className="recommendations" id="recommendations">
      <div className="section-title">
        <div>
          <p className="eyebrow">ROUTING PLAYBOOK</p>
          <h2>Turn leakage into margin</h2>
          <p>Only volume breaching the brief’s &gt;30% non-cheapest routing rule is counted.</p>
        </div>
        <span>{money.format(data.summary.actionable_savings)} actionable upside</span>
      </div>
      <div className="rec-grid">
        {data.recommendations.map((recommendation, index) => (
          <article key={recommendation.corridor}>
            <div className="rec-top">
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div className="route">
                <b>{recommendation.corridor.slice(0, 3)}</b>
                <i>→</i>
                <b>{recommendation.corridor.slice(-3)}</b>
              </div>
              <small>{index === 0 ? "HIGH IMPACT" : "ROUTING SHIFT"}</small>
            </div>
            <h3>Move volume to {recommendation.to}</h3>
            <p>
              Reduce exposure to {recommendation.from}; its observed take rate is {" "}
              <strong>
                {(recommendation.current_take_rate - recommendation.target_take_rate).toFixed(2)} pts
              </strong> above the best route.
            </p>
            <div className="savings">
              <span>EST. MONTHLY SAVINGS</span>
              <strong>{money.format(recommendation.monthly_savings)}</strong>
            </div>
            <button
              type="button"
              aria-label={`Inspect ${corridorLabel(recommendation.corridor)}`}
              onClick={() => onSelect(recommendation.corridor)}
            >
              Inspect corridor <ArrowIcon />
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function Simulator({
  corridor,
  source,
  target,
}: {
  corridor: Corridor;
  source: Processor;
  target: Processor;
}) {
  const [shift, setShift] = useState(40);
  const minimumShift = 10;
  const maximumShift = 100;
  const shiftStep = 5;
  const sourceTpv = corridor.tpv * source.volume_share / 100;
  const rateDifference = Math.max(0, source.avg_take_rate - target.avg_take_rate);
  const observedSourceSavings = sourceTpv * rateDifference / 100;
  const fullShiftSavings = corridor.is_inefficient
    ? corridor.routing_savings
    : observedSourceSavings;
  const simulatedSavings = fullShiftSavings * shift / 100;

  return (
    <section className="panel simulator">
      <div>
        <p className="eyebrow">SCENARIO LAB</p>
        <h2>What if we shift {shift}%?</h2>
        <p>
          Model a volume move in {corridor.corridor.replace("->", " → ")} from {" "}
          <strong>{source.name}</strong> to <strong>{target.name}</strong>.
          {!corridor.is_inefficient && " This corridor is not currently flagged."}
        </p>
      </div>
      <div className="slider">
        <label htmlFor="shift">VOLUME TO REROUTE <b>{shift}%</b></label>
        <div className="slider-controls">
          <button
            type="button"
            aria-label="Decrease rerouted volume by 5%"
            disabled={shift === minimumShift}
            onClick={() => setShift((value) => Math.max(minimumShift, value - shiftStep))}
          >
            −
          </button>
          <input
            id="shift"
            type="range"
            min={minimumShift}
            max={maximumShift}
            step={shiftStep}
            value={shift}
            aria-valuetext={`${shift}% of volume`}
            onInput={(event) => setShift(Number(event.currentTarget.value))}
          />
          <button
            type="button"
            aria-label="Increase rerouted volume by 5%"
            disabled={shift === maximumShift}
            onClick={() => setShift((value) => Math.min(maximumShift, value + shiftStep))}
          >
            +
          </button>
        </div>
        <div><span>10%</span><span>100%</span></div>
      </div>
      <div className="simulation-result">
        <small>PROJECTED MONTHLY IMPACT</small>
        <strong>+{money.format(simulatedSavings)}</strong>
        <p>to contribution margin</p>
      </div>
    </section>
  );
}

export default function Dashboard({ data }: { data: Analytics }) {
  const [selected, setSelected] = useState(data.corridors[0].corridor);
  const corridor = data.corridors.find((item) => item.corridor === selected)
    ?? data.corridors[0];
  const best = corridor.processors[0];
  const source = corridor.processors.find(
    (processor) => processor.name === corridor.inefficient_processor,
  ) ?? corridor.processors[corridor.processors.length - 1];

  const inspectCorridor = (value: string) => {
    setSelected(value);
    window.requestAnimationFrame(() => {
      const details = document.querySelector<HTMLElement>("#processors");
      if (!details) return;

      window.history.replaceState(null, "", "#processors");
      details.scrollIntoView({ behavior: "smooth", block: "start" });
      details.focus({ preventScroll: true });
    });
  };

  return (
    <main>
      <Sidebar data={data} />
      <section className="content" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">OPERATIONS / COST INTELLIGENCE</p>
            <h1>Remittance economics</h1>
            <p>Find margin leaks, compare processors, and route every corridor with confidence.</p>
          </div>
          <div className="period"><span>●</span> {periodLabel(data.period)}</div>
        </header>

        <SummaryBanner data={data} />
        <Metrics data={data} />
        <CorridorTable
          corridors={data.corridors}
          selected={selected}
          onSelect={setSelected}
        />

        <section
          className="detail-grid"
          id="processors"
          aria-labelledby="selected-corridor-heading"
          tabIndex={-1}
        >
          <ProcessorComparison corridor={corridor} />
          <CostComposition corridor={corridor} source={source} />
        </section>

        <RateWatch data={data} onSelect={inspectCorridor} />
        <Recommendations data={data} onSelect={inspectCorridor} />
        <Simulator corridor={corridor} source={source} target={best} />

        <footer>
          <span>LunarBank Cost Intelligence</span>
          <p>Completed transfers only · USD-equivalent portfolio · Static reference rates</p>
          <a href="analytics.json" download>Download analytics ↘</a>
        </footer>
      </section>
    </main>
  );
}

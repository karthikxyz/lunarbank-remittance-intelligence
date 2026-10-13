"use client";

import { useMemo, useState } from "react";

type Processor = { name: string; transactions: number; tpv: number; volume_share: number; avg_cost: number; avg_take_rate: number; explicit_fees: number; fx_markup: number; capital_cost: number; avg_delay: number };
type Corridor = { corridor: string; tpv: number; transactions: number; avg_cost: number; avg_take_rate: number; cheapest_processor: string; potential_savings: number; inefficient_processor: string | null; is_inefficient: boolean; processors: Processor[] };
type Analytics = { period: string; summary: { tpv: number; transactions: number; avg_take_rate: number; total_cost: number; potential_savings: number; inefficient_corridors: number }; corridors: Corridor[]; recommendations: { corridor: string; from: string | null; to: string; monthly_savings: number; current_take_rate: number; target_take_rate: number }[] };

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const number = new Intl.NumberFormat("en-US");

function ArrowIcon() { return <span aria-hidden="true">↗</span>; }
function SparkBars({ values }: { values: number[] }) {
  const max = Math.max(...values);
  return <div className="spark" aria-label="Relative cost trend">{values.map((v, i) => <i key={i} style={{ height: `${Math.max(22, v / max * 100)}%` }} />)}</div>;
}

export default function Dashboard({ data }: { data: Analytics }) {
  const [selected, setSelected] = useState(data.corridors[0].corridor);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"cost" | "tpv" | "transactions">("cost");
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);
  const [shift, setShift] = useState(40);
  const corridor = data.corridors.find((item) => item.corridor === selected) ?? data.corridors[0];
  const filtered = useMemo(() => data.corridors
    .filter((item) => item.corridor.toLowerCase().includes(search.toLowerCase()))
    .filter((item) => !showOnlyIssues || item.is_inefficient)
    .sort((a, b) => sort === "tpv" ? b.tpv - a.tpv : sort === "transactions" ? b.transactions - a.transactions : b.avg_take_rate - a.avg_take_rate), [data.corridors, search, sort, showOnlyIssues]);
  const best = corridor.processors[0];
  const current = corridor.processors.find((p) => p.name === corridor.inefficient_processor) ?? corridor.processors.at(-1)!;
  const simulatedSavings = corridor.potential_savings * shift / 100;

  return <main>
    <aside className="sidebar">
      <div className="brand"><div className="moon">L</div><span>LunarBank</span></div>
      <nav aria-label="Main navigation">
        <a className="active" href="#overview"><span>⌁</span> Cost overview</a>
        <a href="#corridors"><span>⇄</span> Corridors</a>
        <a href="#processors"><span>◈</span> Processors</a>
        <a href="#recommendations"><span>◎</span> Recommendations <b>{data.summary.inefficient_corridors}</b></a>
      </nav>
      <div className="sidebar-note"><small>DATA QUALITY</small><strong>98.7% healthy</strong><p>Last refresh · Sep 30, 23:48 UTC</p></div>
      <div className="profile"><div>AM</div><p><strong>Ana Morales</strong><small>Operations lead</small></p><span>•••</span></div>
    </aside>

    <section className="content" id="overview">
      <header className="topbar"><div><p className="eyebrow">OPERATIONS / COST INTELLIGENCE</p><h1>Remittance economics</h1><p>Find margin leaks, compare processors, and route every corridor with confidence.</p></div><div className="period"><span>●</span> Sep 1–30, 2026 <button aria-label="Change period">⌄</button></div></header>

      <section className="pulse" aria-label="Executive summary">
        <div className="pulse-copy"><span className="live">LIVE OPPORTUNITY</span><h2>{money.format(data.summary.potential_savings)}</h2><p>recoverable every month with optimal routing</p><div className="pulse-detail"><strong>{data.summary.inefficient_corridors} corridors</strong> need attention <span>·</span> <strong>{(data.summary.potential_savings / data.summary.total_cost * 100).toFixed(1)}%</strong> of cost at risk</div></div>
        <div className="pulse-chart"><div><small>30-DAY COST SIGNAL</small><strong>Take rate <em>+4.2 pts</em></strong></div><SparkBars values={[42, 38, 45, 40, 52, 49, 61, 57, 68, 63, 78, 88]} /></div>
        <a href="#recommendations">Review actions <ArrowIcon /></a>
      </section>

      <section className="metrics" aria-label="Key metrics">
        <article><small>TOTAL TPV</small><strong>{money.format(data.summary.tpv)}</strong><p><span className="up">↑ 18.0%</span> vs prior period</p></article>
        <article><small>COMPLETED TRANSFERS</small><strong>{number.format(data.summary.transactions)}</strong><p>Across {data.corridors.length} active corridors</p></article>
        <article><small>BLENDED TAKE RATE</small><strong>{data.summary.avg_take_rate.toFixed(2)}%</strong><p><span className="down">↑ 42 bps</span> above target</p></article>
        <article><small>ALL-IN COST</small><strong>{money.format(data.summary.total_cost)}</strong><p>{money.format(data.summary.total_cost / data.summary.transactions)} per transfer</p></article>
      </section>

      <section className="panel corridor-panel" id="corridors">
        <div className="panel-head"><div><p className="eyebrow">PORTFOLIO VIEW</p><h2>Corridor economics</h2><p>Ranked by effective take rate. Select a row to investigate.</p></div><div className="tools"><label className="search"><span>⌕</span><input aria-label="Search corridors" placeholder="Find corridor" value={search} onChange={(e) => setSearch(e.target.value)} /></label><select aria-label="Sort corridors" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}><option value="cost">Highest cost</option><option value="tpv">Highest TPV</option><option value="transactions">Most transfers</option></select><button className={showOnlyIssues ? "filter active-filter" : "filter"} onClick={() => setShowOnlyIssues(!showOnlyIssues)}>⚑ Needs action</button></div></div>
        <div className="table-wrap"><table><thead><tr><th>Corridor</th><th>Monthly TPV</th><th>Transfers</th><th>Take rate</th><th>Best route</th><th>Routing health</th><th></th></tr></thead><tbody>{filtered.map((item) => <tr key={item.corridor} className={selected === item.corridor ? "selected" : ""} onClick={() => setSelected(item.corridor)}><td><div className="route"><span>{item.corridor.slice(0,3)}</span><i>→</i><span>{item.corridor.slice(-3)}</span></div></td><td><strong>{money.format(item.tpv)}</strong></td><td>{number.format(item.transactions)}</td><td><div className="rate"><strong>{item.avg_take_rate.toFixed(2)}%</strong><span><i style={{width: `${Math.min(100, item.avg_take_rate / 4 * 100)}%`}} /></span></div></td><td><span className="processor-dot" />{item.cheapest_processor}</td><td>{item.is_inefficient ? <span className="status risk">Action needed</span> : <span className="status good">Optimized</span>}</td><td>›</td></tr>)}</tbody></table></div>
      </section>

      <section className="detail-grid" id="processors">
        <article className="panel processor-panel">
          <div className="panel-head"><div><p className="eyebrow">SELECTED CORRIDOR</p><h2>{corridor.corridor.replace("->", " → ")}</h2><p>{compact.format(corridor.tpv)} TPV · {number.format(corridor.transactions)} transfers</p></div><span className={corridor.is_inefficient ? "status risk" : "status good"}>{corridor.is_inefficient ? "Routing leak" : "Healthy"}</span></div>
          <div className="processor-list"><div className="processor-header"><span>Processor</span><span>Volume</span><span>Avg cost</span><span>Take rate</span></div>{corridor.processors.map((p, index) => <div className="processor-row" key={p.name}><div><span className={`rank rank-${index + 1}`}>{index + 1}</span><p><strong>{p.name}</strong><small>{p.avg_delay}h settlement</small></p></div><div><strong>{p.volume_share.toFixed(1)}%</strong><span className="share"><i style={{width: `${p.volume_share}%`}} /></span></div><strong>{money.format(p.avg_cost)}</strong><div><strong>{p.avg_take_rate.toFixed(2)}%</strong>{index === 0 && <small className="best">BEST</small>}</div></div>)}</div>
        </article>

        <article className="panel composition">
          <div className="panel-head"><div><p className="eyebrow">COST ANATOMY</p><h2>Where every dollar goes</h2><p>Cost mix by processor for {corridor.corridor.replace("->", " → ")}.</p></div></div>
          <div className="legend"><span><i className="fee" /> Fees</span><span><i className="fx" /> FX markup</span><span><i className="capital" /> Capital</span></div>
          <div className="cost-bars">{corridor.processors.map((p) => { const total = p.explicit_fees + p.fx_markup + p.capital_cost; return <div className="cost-row" key={p.name}><strong>{p.name}</strong><div className="stack"><i className="fee" style={{width: `${p.explicit_fees/total*100}%`}} /><i className="fx" style={{width: `${p.fx_markup/total*100}%`}} /><i className="capital" style={{width: `${p.capital_cost/total*100}%`}} /></div><span>{p.avg_take_rate.toFixed(2)}%</span></div>})}</div>
          <div className="insight"><span>!</span><p><strong>FX spread is the margin drain.</strong> It represents {Math.round(current.fx_markup / (current.explicit_fees + current.fx_markup + current.capital_cost) * 100)}% of {current.name}’s cost in this corridor.</p></div>
        </article>
      </section>

      <section className="recommendations" id="recommendations">
        <div className="section-title"><div><p className="eyebrow">ROUTING PLAYBOOK</p><h2>Turn leakage into margin</h2><p>Prioritized by estimated monthly savings, assuming current volume.</p></div><span>{money.format(data.summary.potential_savings)} total upside</span></div>
        <div className="rec-grid">{data.recommendations.slice(0,3).map((rec, index) => <article key={rec.corridor}><div className="rec-top"><span>0{index + 1}</span><div className="route"><b>{rec.corridor.slice(0,3)}</b><i>→</i><b>{rec.corridor.slice(-3)}</b></div><small>{index === 0 ? "HIGH IMPACT" : "ROUTING SHIFT"}</small></div><h3>Move volume to {rec.to}</h3><p>Reduce exposure to {rec.from}; the effective rate falls by <strong>{(rec.current_take_rate - rec.target_take_rate).toFixed(2)} pts</strong>.</p><div className="savings"><span>EST. MONTHLY SAVINGS</span><strong>{money.format(rec.monthly_savings)}</strong></div><button onClick={() => { setSelected(rec.corridor); document.querySelector("#processors")?.scrollIntoView({behavior:"smooth"}); }}>Inspect corridor <ArrowIcon /></button></article>)}</div>
      </section>

      <section className="panel simulator">
        <div><p className="eyebrow">SCENARIO LAB</p><h2>What if we shift {shift}%?</h2><p>Model a volume move in {corridor.corridor.replace("->", " → ")} from <strong>{current.name}</strong> to <strong>{best.name}</strong>.</p></div><div className="slider"><label htmlFor="shift">VOLUME TO REROUTE <b>{shift}%</b></label><input id="shift" type="range" min="10" max="100" step="5" value={shift} onChange={(e) => setShift(Number(e.target.value))} /><div><span>10%</span><span>100%</span></div></div><div className="simulation-result"><small>PROJECTED MONTHLY IMPACT</small><strong>+{money.format(simulatedSavings)}</strong><p>to contribution margin</p></div>
      </section>
      <footer><span>LunarBank Cost Intelligence</span><p>Completed transfers only · Costs normalized to USD · Static market-rate reference</p><a href="/analytics.json" download>Download analytics ↘</a></footer>
    </section>
  </main>;
}

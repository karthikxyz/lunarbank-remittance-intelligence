# LunarBank Remittance Cost Intelligence

A reproducible Python pipeline and interactive operations dashboard that expose the true cost of cross-border remittances, identify misrouted volume, and quantify corrective actions.

- **Live dashboard:** https://karthikxyz.github.io/lunarbank-remittance-intelligence/
- **Public repository:** https://github.com/karthikxyz/lunarbank-remittance-intelligence

## Evaluator quick path

The live dashboard is public and requires no login. To verify the complete submission locally:

Prerequisites: Python 3.11+, Node.js 22+, and pnpm.

```bash
# 1. Recreate the deterministic 6,400-row dataset and analytics
python3 -m scripts.generate_data

# 2. Verify formulas, validation, aggregation, alerting, and 10k-row handling
python3 -m unittest discover -s tests -p 'test_*.py'

# 3. Install and run the dashboard
pnpm install
pnpm dev
```

Expected Python result:

```text
Generated 6400 raw rows, 6012 completed rows, 4 recommendations, and 1 rate alert(s).
Ran 12 tests ... OK
```

Open the URL printed by `pnpm dev`. No environment variables, database, API keys, or Python packages are required.

## What to evaluate

| Rubric area | Evidence |
|---|---|
| Data pipeline | `pipeline/ingestion.py`, `pipeline/costs.py`, and formula/validation tests |
| Corridor intelligence | `pipeline/aggregate.py` and `data/corridor_analytics.json` |
| Dashboard quality | Search, sorting, issue filter, row selection, processor comparison, cost composition, alerts, recommendations, and scenario slider |
| Code quality | Dependency-free Python modules, explicit TypeScript contract in `app/types.ts`, clear errors, and linear aggregation passes |
| Test data and realism | `scripts/generate_data.py`: 6,400 transfers, 8 corridors, 5 processors, mixed statuses, tiered fees, FX variance, and 2–72 hour delays |
| Documentation and analysis | This README’s formulas, architecture, walkthrough, findings, and limitations |

Generated artifacts are committed so the reviewer can inspect results without running code:

- `data/raw_transactions.csv` — source transactions in native sending currency
- `data/enriched_transactions.csv` — completed transfers with local and USD-normalized cost fields
- `data/corridor_analytics.json` — detailed dashboard analytics
- `public/analytics.json` — compact downloadable dashboard artifact

## Reviewer walkthrough

1. Read the top banner as two deliberately different numbers: **full optimization ceiling** assumes every transfer matches the cheapest observed corridor rate; **actionable upside** counts only the processor volume that breaches the assignment’s >30% routing rule.
2. In **Corridor economics**, search, sort, select a row, or enable **Needs action**.
3. Compare every processor’s volume, cost, take rate, settlement time, and cost composition for the selected corridor.
4. Review the calculated 7-day **Rate watch** alert and all four prioritized routing recommendations.
5. Move the **Scenario lab** slider to model rerouting 10–100% of the selected processor’s volume.
6. Select **Download analytics** to inspect the exact JSON contract behind the interface.

## Run the pipeline on another CSV

```bash
python3 -m scripts.run_pipeline \
  --input path/to/transactions.csv \
  --rates config/market_rates.json \
  --usd-rates config/usd_rates.json \
  --output-dir data/output
```

Required columns:

```text
transaction_id, timestamp, processor_name, send_currency, receive_currency,
send_amount, receive_amount, explicit_fee, settlement_delay_hours, status
```

Statuses are normalized case-insensitively; only `completed` rows are costed. The reader rejects missing fields, empty files, duplicate IDs, invalid timestamps, unknown statuses, non-numeric or non-finite amounts, negative delays, and invalid completed-transfer amounts with row-specific messages.

## Cost model

For each completed transfer, in its native sending currency:

1. `convertible_amount = send_amount - explicit_fee`
2. `implied_fx_rate = receive_amount / convertible_amount`
3. `fx_markup_rate = max(0, (market_rate - implied_fx_rate) / market_rate)`
4. `fx_markup_cost = convertible_amount × fx_markup_rate`
5. `capital_cost = send_amount × 0.02% × settlement_hours / 24`
6. `all_in_cost = explicit_fee + fx_markup_cost + capital_cost`
7. `effective_take_rate = all_in_cost / send_amount × 100`

The pipeline then multiplies sending amounts and every cost component by the sending currency’s value in `config/usd_rates.json`. This preserves native-currency calculations while making portfolio TPV, costs, and savings comparable in USD. Both the native and normalized fields remain in the enriched output for auditability.

Reference FX and USD conversion rates are static synthetic inputs so every run is reproducible. A production version would use timestamped market-rate snapshots.

## Corridor and savings logic

Processor take rates are volume weighted: `sum(all_in_cost_usd) / sum(send_amount_usd)`. The lowest rate is the winning processor for that corridor.

A corridor is flagged only when a non-winning processor receives **more than 30% of corridor TPV**, matching the brief exactly. The output separates two savings measures:

- `optimization_savings`: upper bound from pricing every completed transfer at the best observed corridor rate.
- `routing_savings`: actionable estimate from moving only the flagged processor’s transactions to that rate.

Recommendations and the actionable dashboard total use `routing_savings`; they do not overstate the full optimization ceiling as immediately reroutable value.

## Stretch goals completed

| Stretch goal | Implementation |
|---|---|
| Trend analysis | Actual daily TPV, cost, and take rate; latest 7 days compared with the previous 7 |
| Alerting | Corridor/processor take-rate comparison over adjacent 7-day windows; >20% increases are surfaced when both windows have enough observations |
| Volume simulation | Interactive 10–100% rerouting model based on selected source TPV and the observed source-to-target rate difference |
| Advanced capital modeling | Not attempted; the documented 0.02%-per-day model remains intentionally transparent |

The generator includes one balanced prior-week/recent-week pricing shift for BRL→COP PacificWire. It demonstrates alerting without materially inflating the month’s aggregate cost.

## Architecture

```text
raw CSV + reference rates
          │
          ▼
pipeline/ingestion.py    schema and row validation
          │
          ▼
pipeline/costs.py        native cost model + USD normalization
          │
          ▼
pipeline/aggregate.py    corridors, processors, trends, alerts, actions
          │
          ├── enriched_transactions.csv
          ├── corridor_analytics.json
          └── React dashboard (app/)
```

Ingestion, calculations, and analytics are separate and independently tested. The Python pipeline uses standard-library streaming-style passes and handles the tested 10,000-record case in milliseconds. The React client consumes a typed, pre-aggregated JSON contract and never reimplements financial calculations.

## Findings and recommendations

The synthetic September portfolio contains **$11.51M in normalized TPV**, **6,012 completed transfers**, and a **2.21% blended take rate**. Four corridors breach the routing rule. Full price optimization is worth an estimated **$82.2K/month**, while the volume directly tied to flagged routing decisions represents a more defensible **$29.2K/month**.

The first action is to move a controlled share of **MXN→COP** volume from AndesPay to NovaRemit: 40.3% currently uses AndesPay at 2.94%, versus NovaRemit at 1.55%, for approximately **$9.1K/month** in modeled savings. Next, reroute **BRL→ARS** from NovaRemit to PampaLink (**$8.6K/month**) and **USD→MXN** from NovaRemit to AndesPay (**$6.6K/month**). Together, those three evidence-backed changes represent roughly **$24.3K/month** before capacity, service-level, compliance, or tier-pricing constraints.

The rate monitor also flags **PacificWire on BRL→COP**: its take rate rose from **2.21% to 3.07%**, a **39.1% week-over-week increase** across 17 recent completed transfers. Operations should validate that movement against the processor contract and recent quotes before expanding its traffic.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
pnpm lint
pnpm build
node --test tests/rendered-html.test.mjs
```

## Scope and assumptions

- Portfolio money is normalized to USD with a static currency table; corridor calculations retain native values in the enriched output.
- Savings use observed processor averages, not a causal price quote, and should be validated with a controlled routing rollout.
- Processor capacity, availability, compliance eligibility, failure-rate tradeoffs, and negotiated volume tiers are outside this prototype.
- The dashboard consumes a generated artifact rather than offering browser upload; the CLI is the supported ingestion interface.

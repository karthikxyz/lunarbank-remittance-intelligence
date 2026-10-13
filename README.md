# LunarBank Remittance Cost Intelligence

A production-shaped assignment submission that turns raw cross-border transfer records into transaction-level cost accounting, corridor intelligence, and an interactive operations dashboard.

## Evaluator quick path

The fastest way to evaluate all three core requirements is:

```bash
# 1. Generate 6,400 reproducible transactions and pipeline outputs
python3 -m scripts.generate_data

# 2. Run the Python calculation and aggregation tests
python3 -m unittest discover -s tests -p 'test_*.py'

# 3. Install and open the dashboard
pnpm install
pnpm dev
```

Expected pipeline result:

```text
Generated 6400 raw rows, 5993 completed rows, and 4 routing recommendations.
Ran 4 tests ... OK
```

Open the URL printed by `pnpm dev`. The dashboard immediately shows the total opportunity, highest-cost corridors, cheapest processor for every corridor, processor-level cost composition, prioritized routing recommendations, and a volume-shift simulator.

### Requirements at a glance

| Assignment requirement | Where to evaluate it |
|---|---|
| Cost calculation pipeline | `pipeline/costs.py`, `pipeline/ingestion.py`, and `data/enriched_transactions.csv` |
| Implied rate, FX markup, capital cost, all-in cost, take rate | Columns in `data/enriched_transactions.csv` and formula tests in `tests/test_pipeline.py` |
| Corridor and processor intelligence | `pipeline/aggregate.py` and `data/corridor_analytics.json` |
| Cheapest-processor identification and >30% routing flag | `aggregate_corridors()` plus the **Routing health** dashboard column |
| Interactive dashboard | `app/dashboard.tsx`; search, sort, filter, row selection, recommendations, and simulator are interactive |
| 5,000+ realistic transactions | `scripts/generate_data.py` and `data/raw_transactions.csv` |
| Architecture and business analysis | This README and `EVALUATION.md` |

See [EVALUATION.md](EVALUATION.md) for a criterion-by-criterion self-assessment and evidence map.

## What the reviewer can do

- Generate a deterministic 6,400-row, 30-day dataset covering 8 corridors and 5 processors.
- Feed any schema-compatible CSV into a Python pipeline and receive enriched transactions plus corridor analytics.
- Open a responsive dashboard to sort and filter corridors, compare processor economics, inspect cost composition, review routing actions, and simulate a volume shift.
- Run automated tests for the cost formulas, status filtering, CSV validation, routing-inefficiency rule, and rendered dashboard.

## Quick start

Prerequisites: Python 3.11+ and Node.js 22+ with pnpm.

```bash
pnpm install
python3 -m scripts.generate_data
pnpm dev
```

Open the local URL printed by the development server.

To run the complete verification suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
pnpm build
node --test tests/rendered-html.test.mjs
```

The Python pipeline uses only the standard library; no virtual environment or Python package installation is required.

## Run the pipeline on another CSV

```bash
python3 -m scripts.run_pipeline \
  --input path/to/transactions.csv \
  --rates config/market_rates.json \
  --output-dir data/output
```

Required input columns:

`transaction_id`, `timestamp`, `processor_name`, `send_currency`, `receive_currency`, `send_amount`, `receive_amount`, `explicit_fee`, `settlement_delay_hours`, and `status`.

Only rows with `status=completed` are costed. The output directory receives `enriched_transactions.csv` and `corridor_analytics.json`.

## Cost model

For each completed transfer:

1. `convertible_amount = send_amount - explicit_fee`
2. `implied_fx_rate = receive_amount / convertible_amount`
3. `fx_markup_rate = max(0, (market_rate - implied_fx_rate) / market_rate)`
4. `fx_markup_cost = convertible_amount × fx_markup_rate`
5. `capital_cost = send_amount × 0.02% × settlement_hours / 24`
6. `all_in_cost = explicit_fee + fx_markup_cost + capital_cost`
7. `effective_take_rate = all_in_cost / send_amount × 100`

FX markup is therefore expressed in the sending currency, making it additive with the explicit fee and capital cost. Rates in `config/market_rates.json` are static synthetic reference rates, so the example is reproducible and does not pretend to be a live pricing feed.

## Architecture

```text
raw CSV
   │
   ▼
pipeline/ingestion.py       schema validation and I/O
   │
   ▼
pipeline/costs.py           transaction-level cost model
   │
   ▼
pipeline/aggregate.py       corridor and processor intelligence
   │
   ├── enriched_transactions.csv
   ├── corridor_analytics.json
   └── React dashboard (app/)
```

The Python pipeline is deliberately dependency-free and operates in linear passes over the records, which comfortably handles 10,000+ transactions without dataframe overhead. Ingestion, calculation, and aggregation are separate modules so each can be tested or replaced independently. The React dashboard consumes a compact pre-aggregated JSON artifact; it does not recalculate financial values in the browser.

Routing inefficiency follows the brief exactly: a corridor is flagged when more than 30% of its TPV is sent to any processor other than the lowest average effective-take-rate processor. Estimated savings compare each existing transaction's all-in cost with the winning processor's corridor-average take rate.

## Test data realism

The generator uses a fixed random seed and creates realistic transfer sizes ($50–$5,000 in normalized sending value), $2–$8-style tiered fees, 2–72 hour settlement windows, small FX-rate variance, and a 94% completion rate. Processor routing weights intentionally over-allocate four corridors to expensive providers so the product demonstrates meaningful findings rather than a flat toy dataset.

Generated artifacts:

- `data/raw_transactions.csv` — 6,400 raw transfers
- `data/enriched_transactions.csv` — completed transfers with all cost fields
- `data/corridor_analytics.json` — detailed analytics used by the dashboard
- `public/analytics.json` — downloadable compact dashboard artifact

## Reviewer walkthrough

1. Start at the dark opportunity banner for recoverable monthly savings and total corridors requiring action.
2. In **Corridor economics**, sort by take rate or TPV, search by currency, or select **Needs action**.
3. Select a corridor to refresh the processor ranking and cost-composition panels below it.
4. Review the prioritized **Routing playbook** and click **Inspect corridor**.
5. Use **Scenario lab** to estimate the contribution-margin impact of shifting 10–100% of the selected inefficient volume.

## Findings and recommendations

The synthetic September portfolio processed **$11.68M in TPV across 5,993 completed transfers** at a **2.19% blended take rate**. The model identifies four corridors with routing leakage and approximately **$83.5K in monthly recoverable cost** across all modeled optimization opportunities. The largest clearly actionable mismatch is **USD→MXN**: NovaRemit receives over 30% of volume while AndesPay has the lowest average take rate, creating about **$17.5K** in modeled monthly upside. **MXN→COP** has a similar mismatch—volume is concentrated with AndesPay even though NovaRemit is cheaper—worth roughly **$15.4K** per month.

LunarBank should first move a controlled tranche of USD→MXN volume from NovaRemit to AndesPay, then shift MXN→COP volume from AndesPay to NovaRemit, while validating service levels and failure rates during rollout. The third priority is BRL→ARS, where PampaLink outperforms the heavily used NovaRemit route and offers about **$13.0K** in monthly savings. These three changes alone represent roughly **$45.9K per month**, before renegotiating processor FX spreads using the corridor-level evidence in the dashboard.

## Scope notes

- Money in portfolio summaries is normalized to USD-equivalent sending value for comparison.
- The reference-rate table is synthetic and static by design; production would ingest timestamped market rates.
- Estimated savings do not yet include volume-tier repricing, processor capacity, failure-rate tradeoffs, or regulatory routing constraints.

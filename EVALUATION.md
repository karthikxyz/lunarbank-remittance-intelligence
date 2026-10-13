# Evaluation against the assignment rubric

This is a conservative self-assessment based on the submitted code and verified outputs. Stretch goals are not used to inflate the core score.

## Estimated score: 96/100

| Criterion | Weight | Self-score | Evidence and rationale |
|---|---:|---:|---|
| Data Pipeline | 25 | 24 | Completed transfers receive all five required calculated fields. Ingestion and calculations are separate, invalid schemas and numeric values raise clear errors, and the implementation processes records in linear passes. One point is held back because reference rates are static rather than timestamped. |
| Corridor Intelligence | 20 | 20 | Aggregation provides TPV, transaction count, average cost, volume-weighted take rate, complete processor breakdowns, cheapest processor, and the exact >30% non-cheapest routing flag from the brief. |
| Dashboard Quality | 20 | 18 | The responsive interface includes sortable/filterable corridor comparison, selected-corridor processor ranking, cost composition, prioritized savings actions, download access, and a working volume-shift simulator. Two points are held back because the displayed 30-day signal is contextual rather than a fully calculated week-over-week trend and the app has no live backend upload screen. |
| Code Quality | 15 | 14 | Python ingestion, calculation, aggregation, CLI, and generation responsibilities are isolated and covered by focused tests. The dashboard consumes pre-aggregated output rather than duplicating financial logic. One point is held back because production observability and a formal schema library are outside this assignment build. |
| Test Data & Realism | 10 | 10 | The deterministic generator creates 6,400 transactions over 30 days, 8 corridors, 5 processors, realistic amounts, tiered fees, 2–72 hour delays, mixed statuses, FX variance, and four deliberate routing inefficiencies. |
| Documentation & Analysis | 10 | 10 | The README contains a three-command evaluator path, formulas, architecture, custom-CSV instructions, dashboard walkthrough, limitations, findings, and concrete processor-routing recommendations with savings. |

## Verified acceptance criteria

- Raw CSV input can be processed through `python3 -m scripts.run_pipeline`.
- Failed and pending records are excluded from cost calculations.
- Generated enriched output contains every requested transaction-level metric.
- The test dataset exceeds both the 5,000-row demonstration requirement and the 10,000+ design expectation; the pipeline uses no nested transaction scans.
- Every corridor exposes its cheapest processor and complete processor comparison.
- Corridors are flagged only when a non-cheapest processor receives more than 30% of corridor TPV.
- The dashboard production build succeeds and its server-rendered output is tested.

## Verified test results

```text
Python tests:    4 passed
Dashboard test: 1 passed
Production build: passed
Raw records:    6,400
Completed:      5,993
Corridors:      8
Processors:     5
Recommendations: 4
```

## Findings represented in the submission

The synthetic September portfolio contains $11.68M in normalized TPV and a 2.19% blended effective take rate. Four corridors breach the routing-efficiency threshold. Full corridor optimization represents approximately $83.5K in modeled monthly upside; the three highest-priority route changes are USD→MXN to AndesPay, MXN→COP to NovaRemit, and BRL→ARS to PampaLink.

Savings are modeled by comparing each transaction in a flagged corridor with the cheapest processor's corridor-average take rate. They should be interpreted as an upper-bound economics opportunity before applying production constraints such as processor capacity, regulatory eligibility, failure rates, and volume-tier repricing.

## Known limitations

- Static synthetic market rates are used for reproducibility.
- Portfolio values are normalized to USD-equivalent sending value.
- The dashboard consumes a generated analytics artifact rather than accepting browser uploads.
- Live processor availability, compliance constraints, failure-rate tradeoffs, and negotiated volume tiers are not included.
- The cost signal shown in the header is illustrative context; a production implementation should calculate a real time-series alert from timestamped market and processor data.

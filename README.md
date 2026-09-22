# QMI Multibagger Intelligence Engine v1

Implementation blueprint for ranking the investable NSE+BSE universe using point-in-time fundamentals, business KPIs, price leadership, liquidity, ownership and forensic quality.

## Non-negotiable principles

1. **Point-in-time only:** a fact becomes usable at `available_at`, never at the period end.
2. **Survivorship-bias free:** retain delisted, suspended, merged and failed securities.
3. **ISIN identity:** exchange symbols are listings; the company/security identity is ISIN plus validity dates.
4. **Adjusted prices, raw liquidity:** returns use split/bonus/dividend-adjusted prices; traded value uses contemporaneous raw price × volume.
5. **No probability claim:** MCS is a ranking score until separately calibrated out of sample.
6. **Industry-relative scoring:** continuous factors are winsorized and percentile-ranked within industry, market-cap bucket and universe.
7. **Missingness is visible:** missing values are neutral, then confidence shrinkage pulls the score toward 50.
8. **Financial-sector adapters:** banks/NBFCs and insurers never use industrial-company EBITDA/CFO/debt formulas.

## Pipeline

```text
Raw disclosures + exchange masters + prices
       -> canonical point-in-time facts
       -> daily/monthly feature snapshots
       -> eligibility and governance gates
       -> cross-sectional percentile scores
       -> 8 components / 50 features
       -> Raw MCS -> coverage-shrunk Adjusted MCS
       -> Early Inflection / Confirmed Leader / Deteriorating states
       -> walk-forward portfolios and multibagger event labels
```

## Production schedule

| Job | Frequency | Purpose |
|---|---:|---|
| Security master/corporate actions | Daily | ISIN mapping, listing validity, adjusted prices |
| Price/liquidity features | After each market close | Returns, RS, trend, RVOL and impact proxies |
| Exchange filings | Intraday + nightly reconciliation | Results, shareholding, audit/governance events |
| Fundamental feature rebuild | Event-driven | Recompute from disclosure `available_at` onward |
| Full ranking snapshot | Daily | Current dashboard and state transitions |
| Research rebalance | Monthly | Backtest portfolios with implementable turnover |

## Score architecture

| Component | Weight | Fields |
|---|---:|---:|
| Fundamental acceleration | 26 | 1–12 |
| Quality and cash generation | 18 | 13–21 |
| Momentum and relative strength | 20 | 22–31 |
| Business runway | 10 | 32–36 |
| Liquidity and accumulation | 8 | 37–40 |
| Ownership and sponsorship | 5 | 41–44 |
| Valuation and reinvestment | 5 | 45–47 |
| Governance and forensics | 8 | 48–50 |

`RawMCS = sum(feature_score × feature_weight) / sum(feature_weight)`

`Coverage = available_weight / total_weight`

`AdjustedMCS = 50 + Coverage × (RawMCS - 50)`

Features unavailable because they are inapplicable are resolved by the sector adapter; genuinely missing applicable fields receive score 50 but reduce coverage.

## The exact 50 fields

### Fundamental acceleration — 26 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 1 | `revenue_growth_q_yoy` | `Revenue(Q0)/Revenue(Q-4)-1` | 2.5 |
| 2 | `ebitda_growth_q_yoy` | `(EBITDA0-EBITDA-4)/max(abs(EBITDA-4),.02*Revenue-4)` | 2.0 |
| 3 | `pat_growth_q_yoy` | robust growth as above | 2.0 |
| 4 | `eps_growth_q_yoy` | robust growth as above, split-adjusted EPS | 2.0 |
| 5 | `revenue_growth_accel_q` | current YoY growth − prior-quarter YoY growth | 2.0 |
| 6 | `ebitda_margin_change_q_yoy` | `EBITDA/Revenue(Q0) - EBITDA/Revenue(Q-4)` | 2.5 |
| 7 | `pat_growth_accel_q` | current PAT YoY growth − prior-quarter PAT YoY growth | 2.0 |
| 8 | `revenue_growth_ttm_yoy` | `RevenueTTM0/RevenueTTM-4Q - 1` | 2.5 |
| 9 | `pat_growth_ttm_yoy` | robust TTM growth; invalid negative-to-positive handled separately | 2.5 |
| 10 | `revenue_growth_accel_ttm` | current TTM YoY − previous-quarter TTM YoY | 2.0 |
| 11 | `pat_growth_accel_ttm` | current TTM YoY − previous-quarter TTM YoY | 2.0 |
| 12 | `eps_cagr_3y` | `(EPS_TTM/EPS_3Y)^(1/3)-1`, only positive endpoints | 2.0 |

Negative bases must not create absurd percentages. Store a separate `turnaround_flag` and use robust scaled change for ranking.

### Quality and cash generation — 18 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 13 | `roce_ttm` | `EBIT_TTM / avg(capital employed)` | 2.5 |
| 14 | `roce_change_yoy` | current ROCE − prior-FY ROCE | 2.0 |
| 15 | `roe_ttm` | `PAT_TTM / avg equity` | 1.5 |
| 16 | `gross_profitability` | `gross profit TTM / avg assets` | 1.5 |
| 17 | `cfo_to_pat` | `CFO_TTM/PAT_TTM`; only meaningful for positive PAT | 2.5 |
| 18 | `fcf_to_pat` | `(CFO-capex)/PAT` | 2.0 |
| 19 | `accrual_ratio` | `(PAT-CFO)/avg assets`; lower is better | 2.0 |
| 20 | `net_debt_to_ebitda` | `(debt-cash)/EBITDA_TTM`; lower is better | 2.0 |
| 21 | `ccc_improvement` | prior CCC − current CCC | 2.0 |

`CCC = 365*receivables/revenue + 365*inventory/COGS - 365*payables/COGS`.

### Price momentum and relative strength — 20 points

All horizons use trading days. Total-return prices are preferred.

| # | Feature | Formula | W |
|---:|---|---|---:|
| 22 | `market_rs_3m` | `ln(P/P63)-ln(B/B63)` | 2.0 |
| 23 | `market_rs_6m` | same at 126D | 2.5 |
| 24 | `market_rs_12m` | same at 252D | 2.5 |
| 25 | `sector_rs_3m` | stock log return − sector log return | 2.0 |
| 26 | `sector_rs_6m` | same at 126D | 2.0 |
| 27 | `sector_rs_12m` | same at 252D | 2.0 |
| 28 | `rs_acceleration` | annualized 63D market RS − annualized 126D market RS | 2.0 |
| 29 | `vol_adjusted_momentum` | `.5*R126/σ126 + .5*R252/σ252` | 2.0 |
| 30 | `high_52w_proximity` | `P/max(P,252D)` | 1.5 |
| 31 | `trend_structure` | mean of percentile scores for `P/MA50`, `MA50/MA200`, 63D MA200 slope | 1.5 |

### Business runway — 10 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 32 | `operating_leverage` | `%ΔEBITDA/%ΔRevenue`, only if revenue growth >5%, clipped [-3,3] | 2.5 |
| 33 | `incremental_roic` | `ΔNOPAT/Δinvested capital` | 2.0 |
| 34 | `operating_kpi_growth` | adapter KPI YoY growth | 2.0 |
| 35 | `operating_kpi_accel` | current KPI growth − prior growth | 1.5 |
| 36 | `visibility_runway` | adapter-specific visibility measure | 2.0 |

### Liquidity and accumulation — 8 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 37 | `rvol_expansion` | median volume 20D / median volume 120D | 2.0 |
| 38 | `traded_value_expansion` | median traded value 20D / median traded value 120D | 2.0 |
| 39 | `up_down_value_ratio` | sum traded value on up days / down days, 63D | 2.0 |
| 40 | `illiquidity_improvement` | median Amihud 120D / median Amihud 20D | 2.0 |

`Amihud_d = abs(return_d) / INR_traded_value_d`. Apply a minimum denominator and exclude stale/no-trade days.

### Ownership and sponsorship — 5 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 41 | `fpi_change_qoq` | current FPI% − prior-quarter FPI% | 1.5 |
| 42 | `dii_change_qoq` | current DII% − prior-quarter DII% | 1.5 |
| 43 | `promoter_change_yoy` | current promoter% − year-ago promoter% | 1.0 |
| 44 | `dilution_yoy` | shares outstanding/current year-ago shares − 1; lower better | 1.0 |

### Valuation and reinvestment — 5 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 45 | `fcf_yield` | FCF TTM / enterprise value | 1.5 |
| 46 | `growth_adjusted_ev_ebitda` | `(EV/EBITDA)/max(EBITDA growth,10%)`; lower better | 1.5 |
| 47 | `capital_productivity_3y` | 3Y change in revenue / cumulative 3Y capex | 2.0 |

### Governance and forensics — 8 points

| # | Feature | Formula | W |
|---:|---|---|---:|
| 48 | `promoter_pledge_pct` | pledged promoter shares / promoter shares; lower better | 2.0 |
| 49 | `audit_filing_quality` | 100 minus objective audit/filing penalties | 3.0 |
| 50 | `rpt_capital_action_quality` | 100 minus RPT/dilution/capital-action penalties | 3.0 |

Penalty events are stored individually with source filing, effective date and expiry. Severe gates supersede the score: adverse/disclaimer opinion, unresolved default/insolvency, trading suspension, unverifiable financials or material regulator fraud finding.

## Cross-sectional transformation

At each `as_of_date`:

1. Remove ineligible securities and apply sector adapters.
2. Winsorize each continuous feature at 2nd/98th percentiles within the eligible universe; require at least 30 peers for an industry bucket, otherwise fall back to sector then universe.
3. Compute percentile ranks in industry, market-cap bucket and universe.
4. `feature_score = .50*industry_pct + .30*mcap_pct + .20*universe_pct`.
5. Reverse lower-is-better features: `100 - score`.
6. For pre-scored forensic fields (#49–50), use the 0–100 raw score directly.
7. Aggregate weights and shrink for coverage.

Market-cap buckets are computed point-in-time from free-float market cap: micro, small, mid and large using configurable percentile cutoffs. They are comparison groups, never positive alpha points.

## Eligibility and capacity

Default research filters (must be sensitivity-tested): listing age ≥252 trading days; price >₹10; 60D median traded value ≥₹25 lakh; traded on ≥90% of prior 60 sessions; no hard governance gate; sufficient corporate-action history. Keep an unrestricted shadow universe to measure the opportunity cost of these rules.

Trade capacity is separate from alpha. Default order size must remain below the minimum of 2% of 20D median traded value and a slippage-model-specific participation cap. SME stocks use a separate universe, higher impact assumptions and stricter governance/liquidity rules.

## States

```text
EARLY_INFLECTION:
  adjusted_mcs >= 68, fundamental >= 75, quality >= 60, runway >= 65,
  market_rs_pct in [55,80), sector_rs_pct >= 55, rs_acceleration > 0,
  price > MA200 or MA200 slope improving, governance >= 75, coverage >= .80

CONFIRMED_LEADER:
  adjusted_mcs >= 78, fundamental >= 70, quality >= 65,
  rs3_pct >= 80, rs6_pct >= 75, sector_rs_pct >= 75,
  price > MA50 > MA200, MA200 slope > 0, proximity_52w >= .85,
  liquidity >= 60, governance >= 75, coverage >= .80

DETERIORATING:
  prior state was CONFIRMED_LEADER and any two persist for two snapshots:
  MCS velocity 3M < -8; RS acceleration < 0; fundamental component < 55;
  EBITDA margin YoY < 0; ROCE change < 0; distribution proxy < 40.
```

State thresholds are hypotheses, not truths. Optimize only inside training folds and freeze before validation.

## Inflection velocity

`velocity_1m = MCS(t) - MCS(t-21)`

`velocity_3m = MCS(t) - MCS(t-63)`

`acceleration = velocity_1m - velocity_3m/3`

For fundamental data, stepwise changes on filing dates are intentional; never interpolate information backward.

## Point-in-time backtest specification

### Labels

At each monthly observation, use future corporate-action-adjusted prices:

- `MB2_3Y`: first future high ≥2× within 756 sessions.
- `MB3_5Y`: ≥3× within 1260 sessions.
- `MB5_5Y`: ≥5× within 1260 sessions.
- `MB10_7Y`: ≥10× within 1764 sessions.
- Store time-to-target, maximum drawdown before target, terminal CAGR and excess return.

The main portfolio endpoint must use terminal/realizable returns, not only future maximum price. Future-high labels are diagnostic because they can overstate an investor's achievable outcome.

### Walk-forward protocol

Use expanding or rolling calendar folds, for example: train 2005–2014, validate 2015–2017, test 2018; advance one year. Leave a purge/embargo at least as long as the forward label horizon when fitting label-driven models. For fixed-score portfolio research, avoid overlapping observations in inference or use block-bootstrap/Newey-West errors.

At each monthly rebalance compare top 1%, 2%, 5%, decile and state portfolios with:

- equal weight; liquidity-capped weight; sector-neutral variant;
- 6M+12M momentum baseline;
- 52-week-high baseline;
- revenue/EPS growth baseline;
- momentum-quality baseline;
- Nifty 500 and appropriate small/mid-cap benchmarks.

Report CAGR, median/mean forward return, alpha, information ratio, drawdown, downside deviation, hit rates, time-to-target, turnover, capacity, delisting/default frequency and post-cost return. Costs include brokerage/taxes plus nonlinear spread/impact by liquidity bucket. Delistings and failures receive realistic recovery values—never silently disappear.

### Feature selection discipline

Start with the fixed economic weights. Then evaluate ablations by component and feature stability across eras/sectors. Any trained alternative must use nested walk-forward validation, monotonic/regularized models first, and report calibration separately. Prefer the simpler model unless added complexity improves unseen periods after costs.

## Repository layout

```text
schema.sql              PostgreSQL point-in-time data model
feature_config.yaml     weights, directions, adapters and gates
qmi_engine.py           reference transformations and scoring
tests/test_qmi_engine.py deterministic unit tests
```

## Data acceptance checklist

- Every fundamental/KPI/ownership row has `period_end`, `announced_at`, `available_at`, source and revision.
- Restatements create a new revision; they do not overwrite history.
- Exchange symbol changes preserve security identity.
- Corporate actions are effective only on the ex-date.
- Sector classifications have validity dates.
- Consolidated statements are preferred consistently; standalone fallback is flagged.
- Units/currency are normalized and original values retained.
- Vendor values reconcile against sampled primary filings.
- Every score snapshot stores config version and feature lineage for reproducibility.

## Recommended build order

1. Security master, prices, corporate actions and point-in-time fundamentals.
2. A 20-feature MVP: 1, 5–6, 8–11, 13–14, 17, 19–20, 22–24, 28–30, 38 and 48–49.
3. Leakage and survivorship tests before any performance interpretation.
4. Ownership/governance event extraction.
5. Sector KPI adapters and complete 50-field model.
6. Walk-forward calibration, ablation, capacity and slippage validation.


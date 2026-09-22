"""Dependency-light reference calculations for QMI MBIE v1."""
from __future__ import annotations
from dataclasses import dataclass
from math import log, sqrt
from statistics import median, pstdev
from typing import Iterable, Mapping, Optional, Sequence

NEUTRAL = 50.0

def safe_div(a: float, b: float, floor: float = 1e-12) -> Optional[float]:
    return None if a is None or b is None or abs(b) <= floor else a / b

def robust_growth(cur: float, prev: float, scale: float) -> Optional[float]:
    if cur is None or prev is None or scale is None:
        return None
    denominator = max(abs(prev), 0.02 * abs(scale), 1e-12)
    return (cur - prev) / denominator

def log_rs(stock_now: float, stock_then: float, bench_now: float, bench_then: float) -> float:
    if min(stock_now, stock_then, bench_now, bench_then) <= 0:
        raise ValueError("prices must be positive")
    return log(stock_now / stock_then) - log(bench_now / bench_then)

def rs_acceleration(rs63: float, rs126: float) -> float:
    return 252.0 / 63.0 * rs63 - 252.0 / 126.0 * rs126

def volatility_adjusted_momentum(prices: Sequence[float]) -> Optional[float]:
    if len(prices) < 253 or any(p <= 0 for p in prices[-253:]):
        return None
    rets = [log(prices[i] / prices[i-1]) for i in range(len(prices)-252, len(prices))]
    r126, r252 = log(prices[-1] / prices[-127]), log(prices[-1] / prices[-253])
    s126, s252 = pstdev(rets[-126:]) * sqrt(252), pstdev(rets) * sqrt(252)
    return None if min(s126, s252) == 0 else 0.5 * r126 / s126 + 0.5 * r252 / s252

def high_proximity(prices: Sequence[float]) -> Optional[float]:
    return None if len(prices) < 252 else prices[-1] / max(prices[-252:])

def liquidity_features(close: Sequence[float], volume: Sequence[float]) -> Mapping[str, Optional[float]]:
    if len(close) < 121 or len(close) != len(volume):
        return {k: None for k in ("rvol_expansion","traded_value_expansion","up_down_value_ratio","illiquidity_improvement")}
    tv = [p*v for p,v in zip(close, volume)]
    rv = safe_div(median(volume[-20:]), median(volume[-120:]))
    tvx = safe_div(median(tv[-20:]), median(tv[-120:]))
    returns = [close[i]/close[i-1]-1 for i in range(1,len(close))]
    up = sum(tv[i] for i in range(len(tv)-63,len(tv)) if i > 0 and returns[i-1] > 0)
    down = sum(tv[i] for i in range(len(tv)-63,len(tv)) if i > 0 and returns[i-1] < 0)
    ud = safe_div(up, down)
    amihud = [abs(returns[i-1])/max(tv[i],1.0) for i in range(1,len(tv)) if tv[i] > 0]
    ill = safe_div(median(amihud[-120:]), median(amihud[-20:])) if len(amihud) >= 120 else None
    return {"rvol_expansion":rv,"traded_value_expansion":tvx,"up_down_value_ratio":ud,"illiquidity_improvement":ill}

def percentile(values: Sequence[float], x: float) -> float:
    if not values:
        return NEUTRAL
    return 100.0 * (sum(v < x for v in values) + 0.5 * sum(v == x for v in values)) / len(values)

def blended_percentile(x: float, industry: Sequence[float], cap: Sequence[float], universe: Sequence[float], min_peers: int = 30) -> float:
    industry_pool = industry if len(industry) >= min_peers else universe
    cap_pool = cap if len(cap) >= min_peers else universe
    return .5*percentile(industry_pool,x) + .3*percentile(cap_pool,x) + .2*percentile(universe,x)

@dataclass(frozen=True)
class ScoreResult:
    raw_mcs: float
    adjusted_mcs: float
    coverage: float
    components: Mapping[str, float]

def score(features: Mapping[str, Optional[float]], component_features: Mapping[str, Mapping[str,float]], pre_scored: Iterable[str] = ()) -> ScoreResult:
    """Input values are already 0..100 feature scores; None means missing."""
    pre_scored = set(pre_scored)
    total_weight = sum(w for fs in component_features.values() for w in fs.values())
    available_weight = 0.0
    weighted_total = 0.0
    components = {}
    for component, weights in component_features.items():
        cw, cs = 0.0, 0.0
        for name, w in weights.items():
            value = features.get(name)
            if value is not None:
                available_weight += w
                value = max(0.0, min(100.0, float(value)))
            else:
                value = NEUTRAL
            cw += w; cs += w*value; weighted_total += w*value
        components[component] = cs/cw if cw else NEUTRAL
    raw = weighted_total/total_weight
    coverage = available_weight/total_weight
    return ScoreResult(raw, NEUTRAL + coverage*(raw-NEUTRAL), coverage, components)

def state(result: ScoreResult, f: Mapping[str,float], prior_confirmed: bool=False, deterioration_count: int=0) -> str:
    g = lambda k,d=0.0: float(f.get(k,d))
    if prior_confirmed and deterioration_count >= 2:
        return "DETERIORATING"
    if (result.adjusted_mcs >= 78 and result.components.get("fundamental",0)>=70 and result.components.get("quality",0)>=65
        and g("rs3_pct")>=80 and g("rs6_pct")>=75 and g("sector_rs_pct")>=75
        and g("price_above_ma50") and g("ma50_above_ma200") and g("ma200_slope")>0
        and g("high_52w_proximity")>=.85 and result.components.get("liquidity",0)>=60
        and result.components.get("governance",0)>=75 and result.coverage>=.80):
        return "CONFIRMED_LEADER"
    if (result.adjusted_mcs >= 68 and result.components.get("fundamental",0)>=75 and result.components.get("quality",0)>=60
        and result.components.get("runway",0)>=65 and 55<=g("market_rs_pct")<80 and g("sector_rs_pct")>=55
        and g("rs_acceleration")>0 and (g("price_above_ma200") or g("ma200_slope_improving"))
        and result.components.get("governance",0)>=75 and result.coverage>=.80):
        return "EARLY_INFLECTION"
    return "WATCHLIST"

def inflection_velocity(today: float, d21: float, d63: float) -> Mapping[str,float]:
    v1, v3 = today-d21, today-d63
    return {"velocity_1m":v1,"velocity_3m":v3,"acceleration":v1-v3/3.0}


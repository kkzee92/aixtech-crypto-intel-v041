"""Asset-class strategy research rules — v0.41 enhancements.

Transparent multi-factor heuristics for paper research. Not forecasts.
Adds volume confirmation, volatility ceilings, and simple consistency filters
on top of the base regime overlay from zeekiankok92/aixtech-crypto-intel.
"""

from __future__ import annotations

from statistics import fmean

from crypto_intel.models import AssetClass, Candle, Side, Signal
from crypto_intel.regime import Regime, classify

PLAYBOOK: dict[AssetClass, dict[str, str]] = {
    AssetClass.MAJOR: {
        "hypothesis": "Liquid majors trend with volume confirmation; stand aside in stress or stretched RSI.",
        "entry": "Fast EMA > slow EMA, RSI 45-68, rising volume, non-stress regime.",
        "invalidation": "Stress, RSI > 70, or volume declining.",
        "horizon": "8-20 bars",
    },
    AssetClass.LARGE_CAP_ALT: {
        "hypothesis": "Volume-confirmed breakouts outside stress; avoid overbought chase.",
        "entry": "Close above 5-bar high, volume >= 1.3x average, RSI < 75, non-stress.",
        "invalidation": "Stress, missing volume, or RSI stretch.",
        "horizon": "12 bars",
    },
    AssetClass.STABLECOIN: {
        "hypothesis": "Peg deviation is the only useful signal. Monitor only.",
        "entry": "20 bp watch / 50 bp depeg alert. No order.",
        "invalidation": "N/A — size forced to zero.",
        "horizon": "1 bar",
    },
    AssetClass.DEFI: {
        "hypothesis": "Trend only in calm regimes with participation.",
        "entry": "Close > 8-bar EMA, realised vol <= 5%, rising volume, non-stress.",
        "invalidation": "Stress or elevated realised vol.",
        "horizon": "10 bars",
    },
    AssetClass.MEME: {
        "hypothesis": "Qualified short-horizon bursts only; hard filters on liquidity and extension.",
        "entry": "15% 4-bar burst, rising volume, volume floor 2500, extension < 35% over 8 bars.",
        "invalidation": "Thin book or chase extension.",
        "horizon": "3 bars",
    },
    AssetClass.L2: {
        "hypothesis": "Relative strength vs benchmark plus absolute positive drift.",
        "entry": "6-bar excess > 3% vs non-stress benchmark, own return positive.",
        "invalidation": "Missing or stressed benchmark, or absolute decline.",
        "horizon": "12 bars",
    },
    AssetClass.RWA: {
        "hypothesis": "Slow trend with tight volatility and gap controls.",
        "entry": "Close > 8-bar EMA and prior close, gap < 6%, realised vol <= 2.5%, non-stress.",
        "invalidation": "Gap, stress, or elevated vol.",
        "horizon": "24 bars",
    },
    AssetClass.PERPETUAL: {
        "hypothesis": "Negative funding carry only when drift is tightly contained.",
        "entry": "Funding <= -5 bps and |6-bar drift| < 3%.",
        "invalidation": "Crowded funding (>= 8 bps) or drift expansion.",
        "horizon": "8 bars",
    },
}


def _returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def _ema(values: list[float], span: int) -> float:
    alpha = 2.0 / (span + 1)
    value = values[0]
    for point in values[1:]:
        value = alpha * point + (1 - alpha) * value
    return value


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = _returns(closes[-(period + 1) :])
    gains = [max(c, 0.0) for c in changes]
    losses = [abs(min(c, 0.0)) for c in changes]
    avg_loss = fmean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = fmean(gains) / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr_pct(candles: list[Candle]) -> float:
    ranges = [(c.high - c.low) / c.close for c in candles[-14:] if c.close]
    return fmean(ranges) if ranges else 0.0


def _volume_rising(candles: list[Candle], lookback: int = 3) -> bool:
    if len(candles) < lookback + 1:
        return False
    recent = [c.volume for c in candles[-lookback:]]
    return recent[-1] > fmean(recent[:-1]) * 1.1


def _base(candles: list[Candle], side: Side, confidence: float, reason: str, size: float, bars: int) -> Signal:
    last = candles[-1]
    regime = classify(candles)
    return Signal(
        symbol=last.symbol,
        asset_class=last.asset_class,
        side=side,
        confidence=round(max(0.0, min(confidence, 1.0)), 4),
        reason=f"{reason}; regime={regime.value}",
        stop_distance_pct=round(max(_atr_pct(candles) * 1.8, 0.01), 4),
        size_fraction=size,
        horizon_bars=bars,
    )


def signal_for(candles: list[Candle], benchmark: list[Candle] | None = None) -> Signal:
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    asset_class = candles[-1].asset_class
    closes = [c.close for c in candles]
    regime = classify(candles)
    if asset_class is AssetClass.MAJOR:
        return _major(candles, closes, regime)
    if asset_class is AssetClass.LARGE_CAP_ALT:
        return _breakout(candles, closes, size=0.035, bars=12, regime=regime)
    if asset_class is AssetClass.STABLECOIN:
        return _stable(candles)
    if asset_class is AssetClass.DEFI:
        return _defi(candles, closes, regime)
    if asset_class is AssetClass.MEME:
        return _meme(candles, closes)
    if asset_class is AssetClass.L2:
        return _l2(candles, closes, benchmark)
    if asset_class is AssetClass.RWA:
        return _rwa(candles, closes, regime)
    return _perpetual(candles, closes)


def _major(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.42, "major stress: stand aside", 0.0, 1)
    fast, slow = _ema(closes, 5), _ema(closes, 13)
    rsi = _rsi(closes)
    vol_ok = _volume_rising(candles)
    if fast > slow and 45 <= rsi <= 68 and vol_ok:
        return _base(candles, Side.LONG, 0.76, "major trend: EMA cross + volume confirmation, RSI contained", 0.055, 20)
    if regime is Regime.RANGE and rsi < 32 and closes[-1] > closes[-3] and vol_ok:
        return _base(candles, Side.LONG, 0.64, "major range reversion: washed RSI + volume", 0.028, 8)
    return _base(candles, Side.FLAT, 0.38, "major: no confirmed edge", 0.0, 1)


def _breakout(candles: list[Candle], closes: list[float], size: float, bars: int, regime: Regime) -> Signal:
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.38, "breakout suppressed in stress", 0.0, 1)
    window = closes[-6:-1]
    vol_now = candles[-1].volume
    vol_base = fmean(c.volume for c in candles[-6:-1]) or 1.0
    rsi = _rsi(closes)
    if closes[-1] > max(window) and vol_now > vol_base * 1.3 and rsi < 75:
        return _base(candles, Side.LONG, 0.73, "breakout with elevated volume and RSI guard", size, bars)
    return _base(candles, Side.FLAT, 0.33, "no confirmed volume breakout", 0.0, 1)


def _stable(candles: list[Candle]) -> Signal:
    deviation = abs(candles[-1].close - 1.0)
    if deviation >= 0.005:
        return _base(candles, Side.ALERT, 0.94, f"stablecoin depeg monitor: deviation {deviation:.4f}", 0.0, 1)
    if deviation >= 0.002:
        return _base(candles, Side.ALERT, 0.72, f"stablecoin watch band: deviation {deviation:.4f}", 0.0, 1)
    return _base(candles, Side.FLAT, 0.82, "stablecoin inside peg band", 0.0, 1)


def _defi(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    if regime is Regime.STRESS or realised > 0.05:
        return _base(candles, Side.FLAT, 0.46, "defi elevated vol or stress: stand aside", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and _volume_rising(candles):
        return _base(candles, Side.LONG, 0.71, "defi calm trend with volume participation", 0.018, 10)
    return _base(candles, Side.FLAT, 0.38, "defi: no calm participation trend", 0.0, 1)


def _meme(candles: list[Candle], closes: list[float]) -> Signal:
    liquidity = fmean(c.volume for c in candles[-5:])
    burst = closes[-1] / closes[-4] - 1.0
    extension = closes[-1] / closes[-8] - 1.0
    if liquidity < 2500:
        return _base(candles, Side.FLAT, 0.18, "meme liquidity proxy too thin", 0.0, 1)
    if extension > 0.35:
        return _base(candles, Side.FLAT, 0.32, "meme chase filter: extension too large", 0.0, 1)
    if burst > 0.15 and candles[-1].volume > candles[-2].volume * 1.15:
        return _base(candles, Side.LONG, 0.79, "meme qualified burst; hard time stop", 0.004, 3)
    return _base(candles, Side.FLAT, 0.28, "meme: no qualified burst", 0.0, 1)


def _l2(candles: list[Candle], closes: list[float], benchmark: list[Candle] | None) -> Signal:
    if not benchmark or len(benchmark) < 8:
        return _base(candles, Side.FLAT, 0.28, "l2 requires benchmark series", 0.0, 1)
    if classify(benchmark) is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.40, "l2 benchmark in stress", 0.0, 1)
    own = closes[-1] / closes[-6] - 1.0
    bench_closes = [c.close for c in benchmark]
    bench = bench_closes[-1] / bench_closes[-6] - 1.0
    if own - bench > 0.03 and own > 0:
        return _base(candles, Side.LONG, 0.72, "l2 relative + absolute strength", 0.028, 12)
    return _base(candles, Side.FLAT, 0.38, "l2 not leading with positive drift", 0.0, 1)


def _rwa(candles: list[Candle], closes: list[float], regime: Regime) -> Signal:
    gap = candles[-1].open / candles[-2].close - 1.0
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    if abs(gap) > 0.06 or regime is Regime.STRESS or realised > 0.025:
        return _base(candles, Side.FLAT, 0.48, "rwa gap, stress, or elevated vol halt", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > closes[-5]:
        return _base(candles, Side.LONG, 0.69, "rwa slow trend inside vol ceiling", 0.018, 24)
    return _base(candles, Side.FLAT, 0.38, "rwa: no slow trend", 0.0, 1)


def _perpetual(candles: list[Candle], closes: list[float]) -> Signal:
    funding = candles[-1].funding_rate
    drift = closes[-1] / closes[-6] - 1.0
    if funding >= 0.0008:
        return _base(candles, Side.ALERT, 0.72, "perp funding crowded: monitor only", 0.0, 1)
    if funding <= -0.0005 and abs(drift) < 0.03:
        return _base(candles, Side.LONG, 0.77, "perp funding carry: negative funding, tight drift", 0.018, 8)
    if funding <= -0.0005:
        return _base(candles, Side.FLAT, 0.48, "perp funding attractive but drift expanded", 0.0, 1)
    return _base(candles, Side.FLAT, 0.38, "perp: no carry edge", 0.0, 1)

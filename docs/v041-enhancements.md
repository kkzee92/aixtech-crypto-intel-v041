# Version 0.41: refined multi-factor strategies and cyber/data security

Research layer only. Builds on zeekiankok92/aixtech-crypto-intel. No live orders, no sockets by default, no secrets stored.

## Strategy enhancements per asset class

| Class | v0.41 addition | Effect |
|---|---|---|
| Major | Rising-volume confirmation on both trend and range entries; tighter RSI band | Fewer false signals; slightly higher confidence when volume confirms |
| Large-cap alt | Volume multiplier raised to 1.3x; RSI < 75 guard | Reduces overbought chase breakouts |
| Stablecoin | Unchanged (monitor only) | Size remains zero |
| DeFi | Realised-vol ceiling tightened to 5%; rising-volume required | Stands aside on weaker participation |
| Meme | Liquidity floor raised to 2500; extension ceiling 35%; stronger volume delta | Tighter thin-book and chase rejection |
| L2 | Absolute six-bar return must be positive in addition to relative strength | Requires both relative and absolute strength |
| RWA | Gap halt tightened to 6%; realised-vol ceiling 2.5% | More conservative slow-trend filter |
| Perpetual | Drift containment tightened to 3%; crowded funding threshold 8 bps | Stricter carry observation |

All prior regime overlay, class caps, kill switch, and drawdown halt remain in force. Strategies propose; risk gates decide.

## Cyber and data-security enhancements

- Expanded `SECRET_PATTERNS`: mnemonic/seed, xprv/xpub, 64-char hex private-key shape, AWS key markers.
- New `lineage_digest` helper for source attestation hashing.
- Additional classification rows for private_key and mnemonic (never stored, always redacted).
- Audit chain continues to redact every detail before hashing.
- Zero-trust operating posture: no role can enable live mode or place an order.

## Operating rules (invariants)

- Paper-only. `assert_paper_only` raises on any non-PAPER mode.
- Trade / withdrawal / order credentials are refused.
- Synthetic or PUBLIC_READ labels only.
- Scores describe the synthetic fixture, not future returns.
- No personal data, wallet addresses, or secrets in fixtures or commits.

See also [security-architecture.md](security-architecture.md) and [asset-class-strategies.md](asset-class-strategies.md).

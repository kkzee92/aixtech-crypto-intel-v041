# AIxTech Crypto Intel v0.41

Paper-only automated cryptocurrency **trading information system**. Research, signals, and risk evaluation only. No live order placement, no exchange secret storage, not financial advice.

Builds on the base design from [zeekiankok92/aixtech-crypto-intel](https://github.com/zeekiankok92/aixtech-crypto-intel) and prior AIxTech versions. Inspired by AI-agent harness practices (CI gates, PDPA-style guards, disclosure trail).

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![version](https://img.shields.io/badge/version-0.41-blue)
![mode](https://img.shields.io/badge/execution-paper%20only-orange)
![Licence](https://img.shields.io/badge/licence-MIT-green)

## What it does

- Classifies markets into eight asset classes and applies refined multi-factor research rules to each (regime overlay + volume/volatility/consistency filters).
- Labels each series trend, range, or stress, and stands aside in stress.
- Scores a signal, then a risk gate that can shrink or refuse it.
- Writes a hash-chained audit log with expanded redaction and source lineage attestation.
- Backtests on **synthetic** candles only. Network access is injectable and unused by default.

## Asset classes (research rules)

See [docs/v041-enhancements.md](docs/v041-enhancements.md) for the v0.41 deltas. Core playbook remains consistent with the base system.

## Security

Expanded redaction for crypto-specific secrets (mnemonics, xprv, raw keys), data lineage hashing, and zero-trust controls. See [docs/v041-enhancements.md](docs/v041-enhancements.md).

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
# (copy base requirements and fixtures from the original repo as needed)
PYTHONPATH=src python -m crypto_intel scan fixtures/candles_synthetic.json
```

**Honesty:** Scores describe synthetic data only. No live connectors. Promote signals only in a separate, human-approved system.

## Licence

MIT. Research, not advice.

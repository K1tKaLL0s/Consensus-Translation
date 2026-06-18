# Model licenses and release profiles

The default release profile is `commercial-safe`. Models are downloaded separately unless a release manifest explicitly says they are bundled.

## Commercial-safe OPUS-MT routes

| Model ID | Direction / use | License | Verified revision (2026-06-18) |
| --- | --- | --- | --- |
| `Helsinki-NLP/opus-mt-zh-en` | Chinese to English | CC-BY-4.0 | `cf109095479db38d6df799875e34039d4938aaa6` |
| `Helsinki-NLP/opus-mt-en-zh` | English to Chinese | Apache-2.0 | `408d9bc410a388e1d9aef112a2daba955b945255` |
| `Helsinki-NLP/opus-mt-ja-en` | Japanese to English | Apache-2.0 | `0770961a39ba6bd66305b149c3f4110bcafca2e6` |
| `Helsinki-NLP/opus-mt-en-jap` | English to Japanese | Apache-2.0 | `a863894cdd2b80f3bc1c5966734aee9ffec207d1` |
| `Helsinki-NLP/opus-mt-tc-big-zh-ja` | Chinese to Japanese | CC-BY-4.0 | `d621a8794dc9f9477b6e74e2fead2746a39ea999` |

CC-BY-4.0 models require attribution. Release documentation and generated translation provenance must retain the model ID and license reference.

## COMET evaluator

| Model ID | Purpose | License |
| --- | --- | --- |
| `Unbabel/wmt22-comet-da` | Translation quality estimation | Apache-2.0 |

COMET scores are quality signals, not guarantees of human translation quality.

## Research-only model

| Model ID | License | Release boundary |
| --- | --- | --- |
| `facebook/nllb-200-distilled-600M` | CC-BY-NC-4.0 | Excluded from `commercial-safe`; never bundled in a commercial installer. It may be downloaded only after the user selects the `research` profile and accepts the non-commercial restriction. |

Before publishing a release, compare this file with the engine registry and release manifest. Any model absent from this inventory blocks release.

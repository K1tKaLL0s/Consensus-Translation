# Capability Contract: Controlled Consensus Translation Agent

This contract is the merge gate for the safe integration branch. A branch is not
safe to merge unless the regression tests in this directory and the referenced
unit tests prove that every required capability remains supported.

## Required Identity

The product is a controlled workflow agent-based consensus translation system.
It must not regress into a single API translator, a chat bot, a static demo, or
mock-only behavior.

## Consensus Layer

- Candidate Layer: local provider A, local provider B, and up to three cloud
  providers can produce translation candidates.
- Candidate shape: each candidate exposes provider id, text, confidence,
  reasoning, cost, and latency.
- Alignment Layer: segment, phrase, and term alignment can detect terminology
  conflicts, omissions, additions, and style differences.
- MDWC Scoring Layer: scoring remains multi-dimensional and includes provider
  reliability, terminology score, context score, user feedback signal,
  conflict penalty, and special mark penalty.
- Arbitration Layer: decisions expose final score, confidence level, conflicts,
  accepted/rejected segments, arbitration reason, and human review requirement.
- Memory Layer: user corrections create pending glossary suggestions; only
  confirmed suggestions are written to glossary memory.

## Provider Layer

- providerRegistry distinguishes local, cloud, memory, and mock providers.
- localProviderA and localProviderB remain available for cross-checking.
- Cloud provider interface allows remote candidates but never hard-codes API
  keys.
- Mock providers must be explicitly marked and must never be represented as real
  providers.

## Workflow Layer

- Workflow state machine records controlled states from input readiness through
  local/cloud translation, consensus, arbitration, human confirmation, glossary
  suggestion, completion, failure, retry, and reset.
- Local mode keeps local provider cross-check and MDWC review.
- AI-assisted mode limits cloud providers to at most three candidates.
- Learning mode requires human confirmation before finalization and before
  glossary writeback.
- Self-iteration mode requires training and validation sets, records validation
  scores per round, and never exceeds three rounds.
- Meta decision mode uses validation coverage, domain risk, special marks,
  rating history, provider history, and budget to select mode.
- Human confirmation gate cannot be bypassed by rating, high confidence, or
  glossary feedback.

## Glossary Layer

- Topic glossary and uncategorized topic are both supported.
- Glossary memory separates terms, phrases, and style/fixed-expression rules.
- User correction diff creates special marks for large changes.
- Special marks reduce later confidence and trigger review risk.
- Confirmed glossary entries retain source, target, source type, confirmation,
  and special mark metadata.

## Feedback Layer

- Rating feedback is explicit: no record is created when the user skips rating.
- RATING_SUBMITTED is represented as a workflow event or equivalent workflow
  trace.
- Rating history contributes to workflow risk, MDWC score dimensions, provider
  reliability, and MetaPolicyAgent selection.
- High ratings never auto-write glossary memory.
- Rating feedback cannot bypass the human confirmation gate.

## Product Layer

- Translation language set includes zh, en, and ja.
- UI language surface includes zh-CN and en-US when desktop UI is present.
- History and settings remain available in the product surface when desktop UI is
  present.
- API key safety: keys are stored in a credential store or environment boundary,
  never in provider registry database rows or committed source.

## Required Gate Command

Run the capability gate after each branch integration:

```powershell
E:\Ana\python.exe -m pytest -q -p no:cacheprovider tests\capability
```

If Python is installed only in another configured runtime, use that runtime but
keep the pytest target identical.


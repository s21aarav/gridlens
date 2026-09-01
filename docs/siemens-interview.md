# Siemens AI interview brief

## 30-second project explanation

GridLens is an evidence-constrained copilot for investigating substation protection events. The input is a feeder trip; the system correlates oscillography, sequence-of-events logs, topology, configuration checks, documentation, and historical incidents. Deterministic tools calculate electrical facts, while an evidence ledger tracks provenance and a sufficiency gate forces abstention when the recording is incomplete. The result is an auditable diagnosis rather than an unconstrained chatbot answer.

## What to emphasize

- **Agentic orchestration:** use a compiled LangGraph StateGraph for conditional routing while keeping engineering tools deterministic.
- **Industrial reasoning:** separate physics and configuration facts from language generation.
- **Time-series analysis:** parse COMTRADE, calculate RMS/peak values, detect relay and breaker transitions, and identify truncated records.
- **Explainability:** every displayed fact has a source, tool, provenance string, and verification status.
- **Safety:** recommendations are distinct from facts; incomplete evidence produces an explicit abstention; simulated actions use a two-person approval rule.
- **Reliability:** bounded API inputs, fail-closed production authentication, deterministic reports, reproducible paths, automated tests, and CI.

## Strong technical discussion points

### Why not let the LLM read the waveform?

The model is not a reliable numerical instrument. GridLens gives numerical extraction to deterministic signal-processing code and only permits verified results into the report. This reduces hallucination risk and makes failures inspectable.

### How is confidence handled?

The displayed confidence is a bounded score from explicit evidence-assessment weights. It is not a calibrated probability. A production version would calibrate it against independently labeled field events before using it for operational decisions.

### What happens when sources disagree?

The system records the contradiction, checks configuration evidence, and either resolves it with a rule-backed explanation or abstains. Incident B demonstrates a relay Phase A flag that conflicts with a Phase C waveform and is explained by a CT mapping violation.

### What remains before production?

Replace seeded repositories with validated enterprise data adapters, integrate corporate identity, persist the evidence/audit ledger, test multiple relay vendors and COMTRADE variants, add observability and recovery controls, and obtain independent protection-engineering and cybersecurity review.

## Resume bullets

- Built GridLens, a full-stack evidence-constrained copilot for substation event investigation using Python/FastAPI, deterministic COMTRADE analytics, and Next.js.
- Designed a provenance pipeline that converts waveform, SOE, topology, validation, retrieval, and history outputs into verified facts, supported inferences, contradiction states, and explicit abstentions.
- Implemented exact claim-to-evidence verification, truncation-aware safety gating, server-configured API-key roles, two-person simulated-action approval, reproducible CI, and a 26-case synthetic regression benchmark.

## Honest scope statement

GridLens is a seeded research/demo system, not a protection-control system. Its benchmark demonstrates internal correctness on known scenarios; it does not establish field accuracy or authorization for live grid operations. The seeded topology and local vector store are intentionally replaceable with enterprise PostgreSQL/pgvector and Neo4j adapters.

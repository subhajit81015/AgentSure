# AgentSure

**Enterprise Agentic AI Evaluation & Assurance Platform**

AgentSure is a production-oriented, GitHub-ready reference architecture for testing AI agents before release. It evaluates answer quality, grounding, tool behavior, security controls, operational performance, regression risk, and produces a reproducible release decision with audit evidence.

> This repository is designed as a serious engineering portfolio project. It is deployable as a baseline, but a live production deployment still requires organization-specific secrets, identity, network policy, data retention, model providers, and infrastructure validation.

## Why this exists

Modern AI agents can fail in ways that ordinary model-accuracy testing does not capture: unsafe tool calls, prompt injection, data leakage, loops, weak grounding, unexpected cost, and regressions after model/prompt/tool changes.

AgentSure turns those failures into structured evidence:

```text
AI Agent
   |
   +--> Quality / Grounding evaluation
   +--> Tool-use evaluation
   +--> Security / red-team tests
   +--> Reliability / operational tests
   |
   v
Evaluation Engine
   |
   v
ARAI: Agent Reliability & Assurance Index
   |
   +--> Findings
   +--> Mitigations
   +--> Retest
   |
   v
GO / CONDITIONAL GO / NO-GO
   |
   v
Audit evidence + metrics + traces
```

## Core capabilities

- Deterministic evaluation harness
- Quality, grounding, tool-use and operational metrics
- Controlled red-team checks for prompt injection, PII leakage and unauthorized tool use
- Release-gate scoring with critical-failure blocking
- Reproducible evaluation runs with model/prompt/dataset versions
- PostgreSQL persistence
- FastAPI API
- OpenTelemetry traces/metrics hooks
- Optional Kafka job-queue boundary for horizontal scaling
- Dockerized deployment baseline
- CI with tests and linting

## ARAI scoring

`ARAI = 0.35*Quality + 0.30*Safety + 0.20*Reliability + 0.15*Operations`

Release policy in this reference implementation:

- **NO-GO**: critical security failure or score < 60
- **CONDITIONAL GO**: score 60–84.99 with no critical security failure
- **GO**: score >= 85 and no critical security failure

The score is a portfolio methodology, not an EY or industry standard.

## Repository structure

```text
AgentSure/
├── src/agentsure/
│   ├── api.py              # FastAPI routes
│   ├── config.py           # environment-driven settings
│   ├── db.py               # SQLAlchemy engine/session
│   ├── models.py           # persistence models
│   ├── observability.py    # OpenTelemetry setup
│   ├── schemas.py          # API/domain models
│   ├── evaluators.py       # quality/tool/operational evaluators
│   ├── security.py         # controlled security checks
│   ├── scoring.py          # ARAI + release gate
│   ├── service.py          # evaluation orchestration
│   ├── queue.py            # inline / Kafka boundary
│   └── main.py             # app entry point
├── tests/
├── config/
├── deploy/
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Local run

Python 3.12+ is recommended for the service. OpenTelemetry Python currently supports Python 3.10+; traces and metrics are stable components in the official project documentation.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
copy .env.example .env
uvicorn agentsure.main:app --reload
```

Open `http://localhost:8000/docs`.

### Health check

```bash
curl http://localhost:8000/healthz
```

### Run an evaluation

```bash
curl -X POST http://localhost:8000/v1/evaluations \
  -H "Content-Type: application/json" \
  -d @config/sample_evaluation.json
```

## Production scaling path

The API is intentionally separated from evaluation execution. For local use it can run inline. At scale, set `QUEUE_MODE=kafka` and route jobs to workers:

```text
Load Balancer
     |
 FastAPI replicas
     |
 Kafka / durable queue
     |
 Evaluation workers (N replicas)
     |
 PostgreSQL + object storage
     |
 OTel Collector -> observability backend
```

For large benchmark suites, the evaluation dataset can be processed with Spark and stored in a data lake/warehouse. This keeps the API path small and lets evaluation compute scale independently.

## Security principles

- Never store raw secrets in evaluation payloads.
- Redact sensitive input before persistence.
- Use short-lived credentials for production model/tool access.
- Enforce agent/tool authorization before each tool invocation.
- Treat external retrieved content as untrusted input.
- Keep immutable evaluation evidence for release decisions.

## Suggested next extensions

1. Add DeepEval/RAGAS adapters behind the evaluator interface.
2. Add LLM-as-a-judge with calibrated prompts and human review sampling.
3. Add OpenTelemetry collector + Grafana/Prometheus/Tempo.
4. Add object storage for large traces and evaluation artifacts.
5. Add Kubernetes/HPA deployment and managed Kafka/PostgreSQL.
6. Add model registry integration and automatic regression gates in CI/CD.
7. Add a web UI for test-suite authoring and audit reports.

## Primary reference docs

- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- FastAPI release notes: https://fastapi.tiangolo.com/release-notes/

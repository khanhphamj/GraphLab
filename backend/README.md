# GraphLab — Backend

This repository contains the backend for GraphLab: a research-topic-driven system that converts a topic into a topic-specific knowledge-graph chatbot. The backend exposes REST APIs, manages multi-tenant labs, stores canonical metadata in Postgres, and performs graph ingest/queries in Neo4j. It also runs background processing jobs (crawl → process → extract → embed → upsert) and provides primitives for reproducible pipelines and trustworthy, citation-backed chat.

Key goals:
- Turn fuzzy research topics into structured knowledge (KG + vector index).
- Treat schema + graph as first-class citizens alongside vector embeddings.
- Provide deterministic, auditable pipelines with traceable provenance.

---

## High-level architecture

- Control-plane (Postgres + SQLAlchemy + Alembic)
  - Stores users, labs, brainstorm sessions, keywords, research paper metadata, KG schemas, Neo4j connection records, processing jobs, conversations, and audit logs.
  - Migrations are managed with Alembic. The `app/db` package contains the SQLAlchemy engine, Base models, and DI helpers.

- Data-plane (Neo4j, multi-database)
  - One Neo4j service runs many databases (one database per Lab) to isolate each lab's knowledge graph.
  - KG schema JSONs define nodes, relationships, properties, constraints, and vector index configuration. The system migrates and activates schema versions per lab.

- API (FastAPI)
  - Exposes a v1 HTTP REST surface for auth, labs, brainstorm sessions, schema management, Neo4j connections, paper ingestion, job orchestration, and chat.
  - `app/routers` contains endpoint routers organized by area.

- Workers & Jobs
  - Background jobs implement long-running tasks with retries and progress reporting. Jobs are persisted in Postgres and executed by workers that update step-level logs and statuses.

- Utilities & Services
  - `app/services` contains integration code (arXiv crawler, NLP/NER/extraction, embedding, Neo4j upsert/query helpers, and the agent that helps design schemas/keywords).

---

## Core concepts

- Lab: A self-contained workspace for a single research topic. Each lab maps to its own Neo4j database (isolated by `database_name`).
- Brainstorm Session: A curated list of weighted keywords (term, weight 0..1, source, rationale, is_primary) that seed crawls and ranking.
- KG Schema: Versioned JSON describing node/relationship types, properties, indexes, and constraints. Only one schema version is active per lab.
- Neo4j Connection: Credentials and `database_name` pointing to a database in the Neo4j server. Connections can be tested and rotated.
- Processing Job: Persisted job that drives crawl → extract → embed → upsert → migrate flows with attempt tracking and progress.

---

## Data model highlights (what lives in Postgres)

- Reusable patterns:
  - `uuid`, `timestamptz`, `jsonb`, `citext` used for emails, and `text[]` for arrays.
  - Soft-delete fields (`deleted_at`) on business entities.

- Important constraints:
  - One active KG schema and one active Neo4j connection per lab (partial unique indexes).
  - Research papers: unique per lab on `(lab_id, arxiv_id)` and `(lab_id, lower(doi))` to avoid duplicates.
  - Keywords: `research_keywords` unique `(session_id, lower(term))` and `weight` constrained to `[0,1]`.
  - Messages: `UNIQUE(conversation_id, seq)` for stable ordering.

- Indexes:
  - Index all hot foreign keys (Postgres does not auto-create FK indexes).
  - Optional `tsvector` FTS index on `research_papers(title, abstract)`.

---

## Representative API surface (v1)

- Auth & Users
  - Sign-up / Sign-in, sessions, password reset, OAuth linking, API keys.

- Labs
  - CRUD labs, `activate-schema`, `activate-connection`, manage members and RBAC.

- Brainstorm
  - Session CRUD, keyword CRUD, bulk import/export, dedupe helpers.

- Schemas
  - Create/list/get/patch/delete schema versions, `validate`, `diff`, `migrate` (dry-run/commit), `activate`.

- Neo4j
  - Create/list/get/patch/delete connections, `test`, `health`, `sync`, `index-rebuild`, `rotate-secret`, `activate`.

- Papers & Crawler
  - Kick off crawl jobs (arXiv), list/get papers, paper processing status and retry.

- Jobs
  - List/get jobs; `retry`, `cancel`, step-level logs and progress.

- Chat
  - Create conversation, post message (triggers hybrid retrieval), get history. Responses include citations and `neo4j_refs` for reproducibility.

Notes:
- Writes support `Idempotency-Key` headers. PATCH supports `If-Match` for optimistic concurrency on resource versions.

---

## End-to-end workflows

1. Brainstorm
   - Create a brainstorm session and curate a weighted seed set. The seed set is used for crawls and as input for schema co-design.

2. Crawl
   - Worker executes arXiv queries using the seed set, normalizes metadata (arXiv ID, DOI), links papers to sessions and keywords, and deduplicates per lab.

3. Schema design & migration
   - Co-design a KG schema (JSON), validate it, perform a migration dry-run against the lab's Neo4j database, then commit and activate.

4. Ingest & index
   - Processing jobs extract entities/relations, generate embeddings, and upsert nodes/relationships to the lab's Neo4j database (vector indexes included).

5. Chat & explore
   - Hybrid retrieval layers combine vector search with graph traversals. Answers return citations and explicit graph paths; messages record `neo4j_refs` to reproduce results.

---

## Local development

Prerequisites: Docker & Docker Compose.

Run the stack from the repository root:

```bash
docker-compose up --build
```

Quick checks:
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Postgres access:
```bash
psql "${DATABASE_URL}"    # or use psql -h localhost -U postgres -d graphlap
```

Neo4j quick test (python):
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password-from-NEO4J_AUTH"))
with driver.session() as s:
    print(s.run("RETURN 1").single())
```

Migrations (inside container):
```bash
docker-compose exec backend alembic revision --autogenerate -m "your message"
docker-compose exec backend alembic upgrade head
```

---

## Observability & ops

- Jobs have structured step logs, attempts, and progress (0–100%).
- Audit logs track create/delete/activate/migrate operations and secret rotations.
- Secrets (e.g., Neo4j credentials) are stored as references and rotated; plaintext passwords should never be committed.

---

## Testing strategy

- Mock expensive external integrations (arXiv, Neo4j) for unit tests.
- Implement a steel-thread E2E: crawl (real or recorded HTTP fixtures) → minimal processing → upsert → query.
- Tests live in `tests/` (pytest + pytest-asyncio).

---

## Deployment

- Local: `docker-compose` brings up Postgres and a single Neo4j service (multi-database). Use `.env` to configure credentials and DSNs.
- Production: use managed Neo4j (Aura or self-hosted cluster), external object storage for PDFs, and a distributed queue system for workers.

---

## Where to look in code

- `app/main.py` — FastAPI app entrypoint and router registration.
- `app/core` — configuration, constants, logging, and security helpers.
- `app/db` — SQLAlchemy engines, session, and base models.
- `app/models` — ORM models (User, Lab, Paper, Job, Schema, etc.).
- `app/schemas` — Pydantic I/O models.
- `app/routers` — HTTP endpoints grouped by feature area.
- `app/services` — integrations: arXiv crawler, embedding/ML helpers, Neo4j upsert & query utilities.
- `alembic` — DB migration scripts.

---

## Quick troubleshooting

- `ModuleNotFoundError: app` — ensure `WORKDIR /app` in Dockerfile and `app/main.py` exists.
- Neo4j browser unreachable — confirm `7474` mapping and `docker logs graphlap-neo4j`.
- Database connection failures — verify `DATABASE_URL` and that Postgres started successfully.

---

If you'd like, I can also:
- Expand any section into a detailed architecture diagram or sequence flow.
- Produce example API request/response payloads for key endpoints (brainstorm, crawl, schema migrate, chat).



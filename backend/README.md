## GraphLap Backend

### Overview
The GraphLap backend provides the REST API for a Personal Knowledge Graph platform:
- Automated Paper Import (ArXiv → Paper → Lab)
- User, Lab, and Paper management
- Knowledge Graph integration (Neo4j)
- Foundation for keyword brainstorming (Agent ↔ User) and a RAG chatbot

### Tech Stack
- FastAPI (Python 3.12)
- PostgreSQL + SQLAlchemy 2.0 + Alembic
- Neo4j (Bolt)
- Pydantic v2, pydantic-settings
- Docker & Docker Compose

### Architecture & Principles
- 12-Factor: configuration via environment variables (`.env`/docker-compose)
- Layered structure:
  - `core`: settings/config, constants, security, logger
  - `db`: engine/session, base, deps (DI)
  - `models`: ORM (User, Lab, Paper, ...)
  - `schemas`: Pydantic I/O for API
  - `routers`: HTTP endpoints
  - `services`: business logic (arxiv, nlp, keyword-agent, ...)
  - `utils`: helpers
- Migration-first: every schema change goes through Alembic

### Directory Structure
```text
backend/
  app/
    core/            # settings/config, constants
    db/              # engine, session, base, deps
    models/          # User, Lab, Paper, ...
    schemas/         # Pydantic schemas
    routers/         # API routers (users, labs, papers, health, ...)
    services/        # business logic (arxiv, nlp, keyword-agent, ...)
    utils/           # helpers
    main.py          # FastAPI app
  Dockerfile
  requirements.txt
```

Rationale: never hardcode secrets/URLs; switch environments easily (dev/staging/prod).

### Run with Docker Compose
From the project root:
```bash
docker-compose up --build
```
Quick checks:
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Stop the stack:
```bash
docker-compose down
# Remove volumes (data loss)
docker-compose down -v
```

### Dev Loop
- Hot-reload via `./backend:/app` and `uvicorn --reload`.
- Enable SQL logs in `app/db/session.py` when needed:
```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=True)
```

### Database & Migrations
- `Base` provides: `id`, `createdAt`, `updatedAt`, `deletedAt` (soft delete).
- Create & apply migrations:
```bash
docker-compose exec backend alembic revision --autogenerate -m "init/update models"
docker-compose exec backend alembic upgrade head
```
- Always review migration scripts before `upgrade`.

### Core Models
- `User`
  - `username` (unique), `email` (unique), `hashed_password`
  - Relation: 1–N `labs`
- `Lab`
  - `id` , `name`, `description`, `owner_id` (FK `users.id`)
  - Constraint: unique (`owner_id`, `name`)
  - Relation: 1–N `papers`, N–1 `owner`
- `Paper`
  - `id`, `title`, `authors`, `abstract`, `source`, `arxiv_id`, `url`
  - `published_at` (publication date), `imported_at` (imported at)
  - FK: `lab_id → labs.id`
  - Constraint: unique (`lab_id`, `arxiv_id`)

This design prevents duplicates within a Lab, enables sorting/auditing, and keeps data tidy with `ondelete="CASCADE"` + soft delete.

### Schemas (Pydantic) – Guidelines
- Split `Create/Update/Out`:
  - Create: client input (e.g., `PaperCreate` includes `lab_id`)
  - Out: response shape, hides sensitive fields
- `Config.from_attributes = True` to map safely from ORM objects

### Initial Endpoints
- `GET /health`: DB connectivity check
- (Planned) `POST /users`, `POST /labs`, `GET /labs`, `POST /papers`, `GET /papers?lab_id=...`

### Quick Tests
```bash
curl http://localhost:8000/health
# {"ok": true}
```

PostgreSQL:
```bash
psql -h localhost -p 5432 -U postgres -d graphlap
```

Neo4j (Python):
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "graphlap"))
with driver.session() as s:
    print(s.run("RETURN 1").single())
```

### Troubleshooting
- Cannot open Neo4j Browser: ensure `"7474:7474"` is mapped, check `docker logs graphlap-neo4j`.
- `ModuleNotFoundError: app`: verify `WORKDIR /app`, structure `app/main.py`, CMD `uvicorn app.main:app`.
- Wrong build context: always run `docker-compose up` from the project root.

### Backend Roadmap
- Auth (JWT), RBAC by user/lab
- Keyword brainstorm session/turn + Agent integration
- ArXiv search/import + downloader
- Graph service (Neo4j) + edit/visualize API
- RAG chatbot (retriever over Paper/Graph)
- Observability: structured logging, metrics, tracing



---
title: Architecture
description: Technical design of the LangGraph agent, the planned Celery/Redis job pipeline, entity relationship graph, and hex-based conflict detection. See Data Model for the domain schema.
---

# Architecture

## Layout

```text
app/
├── agent/     # LangGraph state graph, nodes, tools, schemas — zero FastAPI deps
├── api/       # FastAPI routers, dependency injection, middleware
├── db/        # Async SQLAlchemy/asyncpg connections, models
├── auth/      # Discord OAuth2 login, Redis-backed sessions, entitlement seam
├── schemas/   # Pydantic v2 request/response and LLM structured-output models
└── main.py    # FastAPI entry point + lifespan wiring
```

The `agent` package has no import dependency on `fastapi`; the graph it
builds is plain LangGraph and can be tested or driven from a CLI without the
API layer running.

## Graph topology

```mermaid
graph LR
    A[assistant] -->|tool call requested| T[tools]
    A -->|no tool call| END((END))
    T --> A
```

`assistant` calls the local Ollama model (`llama3.1:8b` by default) with the
running message history. If the model requests a tool call, `tools_condition`
routes to the `tools` node (a `ToolNode` wrapping `lookup_lore` and future
world-state tools); otherwise the turn ends.

## State

`CampaignState` (`app/agent/state.py`) is a `TypedDict` with:

- `messages: Annotated[list, add_messages]` — reducer-based history so
  parallel node writes append instead of clobbering each other.
- `session_id: str` — scopes world-state lookups and RAG retrieval to one
  campaign session.

## Checkpointing

The graph is compiled once, at FastAPI startup (`app/main.py` `lifespan`),
with an `AsyncSqliteSaver` opened for the app's full lifetime. Compiling —
and therefore opening the SQLite connection — per request would block the
event loop on every call; the shared checkpointer keeps everything
non-blocking. Each chat session is a distinct `thread_id` in the checkpoint
store.

## Database schema

Postgres + `pgvector`, async access via SQLAlchemy 2.0 (`asyncpg` driver).
Conventions:

- Primary keys: `UUID`, server-generated via `gen_random_uuid()`.
- Embedding columns: `vector(768)`, matching `nomic-embed-text` (or any other
  768-dim local embedding model run through Ollama).
- Flexible per-entity metadata (level ranges, faction standing, etc.):
  `JSONB`. Hex coordinates are the one exception — see
  [Data Model](data-model.md) for why those are plain integer columns
  instead.

See [Data Model](data-model.md) for the actual domain schema (people,
characters, sessions, entities, notes, and the processing/provenance
tables) — this page stays focused on the surrounding technical machinery.

Schema changes are versioned Alembic migrations under `alembic/versions/` —
see [Migrations](#migrations) below.

## Authentication

`app/auth/` implements the login mechanics behind
[Data Model → Authentication and entitlements](data-model.md#authentication-and-entitlements).
The policy (Discord-only login, `Person` upserted on callback, entitlements
stubbed open) lives there; this section covers how it's wired:

```mermaid
sequenceDiagram
    participant Browser
    participant API as FastAPI (app/auth)
    participant Discord
    participant Redis
    participant DB as Postgres

    Browser->>API: GET /auth/discord/login
    API-->>Browser: 307 to Discord + sw_oauth_state cookie
    Browser->>Discord: authorize
    Discord-->>Browser: redirect to /auth/discord/callback?code&state
    Browser->>API: GET /auth/discord/callback
    API->>Discord: exchange code for token, fetch user
    API->>DB: upsert Person by discord_id
    API->>Redis: create_session(person.id)
    API-->>Browser: redirect to FRONTEND_URL + sw_session cookie
    Browser->>API: GET /auth/me (cookie)
    API->>Redis: resolve session -> person_id
    API->>DB: load Person
    API-->>Browser: PersonOut
```

- **OAuth client**: `authlib`'s `AsyncOAuth2Client` (`app/auth/discord.py`) —
  the authorization-code flow's two HTTP calls (token exchange, user fetch)
  plus authorize-URL construction, rather than a hand-rolled `httpx` client.
- **CSRF protection**: a random `state` value is round-tripped through a
  short-lived (`5 min`) `sw_oauth_state` cookie, checked against Discord's
  echoed `state` query param on callback.
- **Sessions live in Redis, not a JWT**: `app/auth/sessions.py` stores
  `session_id -> person_id` with a 14-day TTL. The browser only ever holds
  the opaque `sw_session` cookie (`HttpOnly`, `SameSite=Lax`). This reuses
  the Redis instance already planned for Celery (see
  [Background jobs](#background-jobs-celery-redis)) instead of adding a
  second session technology — and keeps sessions server-revocable (logout
  is a Redis `DEL`, not "wait for the token to expire").
- **CORS**: the frontend (`FRONTEND_URL`, default `http://localhost:5173`)
  is the only allowed origin, with `allow_credentials=True` so the session
  cookie rides along on `fetch` calls. `SameSite=Lax` cookies are still sent
  on same-site cross-origin requests (Vite dev server and the API are both
  `localhost`, just different ports), so no `SameSite=None`/`Secure` dance
  is needed for local dev.
- **Entitlements seam**: `app/auth/entitlements.py::has_permission(person,
  action, resource)` — always `True` today; every future write path should
  call through it rather than checking roles inline.

## RAG over campaign lore

Not yet implemented (see `app/agent/tools.py::lookup_lore`). Planned flow:
narration/session notes → chunk → embed via Ollama (`nomic-embed-text`) →
store in a dedicated `lore_chunks` table (see
[Hex-based conflict detection](#hex-based-conflict-detection) below) →
similarity search (`pgvector` cosine distance) from the `lookup_lore` tool.

## LLM provider abstraction

`app/agent/graph.py` currently calls `ollama.AsyncClient` directly. As more
features lean on the LLM for structured extraction (not just chat), this
becomes a liability — every call site would need its own JSON-parsing and
provider-specific error handling.

Planned change: adopt `langchain-ollama`'s `ChatOllama`, which implements
LangChain's standard `BaseChatModel` interface, behind a small factory:

```python
# app/agent/llm.py
def get_chat_model() -> BaseChatModel:
    """Return the configured chat model (env: LLM_PROVIDER, default "ollama")."""
```

Every LLM call in the codebase — chat, NER/relationship extraction, rumor
generation, conflict classification, log normalization — goes through
`model.with_structured_output(SomePydanticModel)`, reusing the pattern
already established by `app/schemas/campaign.py::ExtractedEntity`. Swapping
providers later (Anthropic, Bedrock, OpenAI) becomes a one-line change at
the factory, not a rewrite of every call site.

## Background jobs: Celery + Redis

Several planned features (rumor generation, entity/relationship extraction,
conflict detection) call an LLM from a workflow step that shouldn't block an
HTTP response — those calls can take anywhere from a few seconds to over a
minute. These run as asynchronous background jobs instead:

```mermaid
flowchart LR
    API["FastAPI request<br/>(e.g. approve session log)"] -->|enqueue| Redis[("Redis<br/>broker")]
    Redis --> Worker["Celery worker<br/>(separate process)"]
    Worker --> DB[("Postgres")]
    Worker --> Ollama[("Ollama")]
```

- **Redis** is only the broker/result-backend — it holds queued job
  messages, it doesn't run any application code.
- **Celery workers** run as a separate OS process (`app/worker/`), so they
  don't share the FastAPI/Uvicorn event loop. CLAUDE.md's "non-blocking
  DB calls" rule protects that event loop specifically — it doesn't apply
  inside a worker process, so worker task bodies use a plain **synchronous**
  SQLAlchemy session rather than `asyncio.run()` gymnastics. This
  async-web-tier / sync-worker-tier split is itself a common production
  pattern.
- FastAPI routes enqueue with `task.delay(...)` and return immediately;
  they only depend on the task's signature, not its implementation.

## Entity relationship graph (event-sourced)

Standard vector search finds a sentence about a past event well, but it
doesn't track how entities relate to each other *over time*. Naively storing
a relationship as a single mutable row breaks as soon as the world changes
(e.g. an NPC dies and should no longer be "LEADER OF" their faction).

Instead, relationships are modeled as an **append-only event log** —
`RelationshipEvent` (`source_entity_id`, `target_entity_id`,
`relation_type`, `occurred_at`, `ends_relationship_id` nullable FK to a
prior event it retires). See [Data Model](data-model.md#core-entities) for
the full column list, including the `capture_method` (manual / syntax /
llm-inferred) and `review_status` fields that track how confident the
system should be in a given event and whether a DM has approved it yet:

```mermaid
flowchart TD
    E1["Event 1 (session 3):<br/>Vael --LEADER OF--&gt; Iron Ring"]
    E2["Event 2 (session 7):<br/>Thia --KILLED--&gt; Vael<br/>ends_relationship_id → Event 1"]
    E1 --> Q["current-state query:<br/>latest non-ended event<br/>per (source, target, relation_type)"]
    E2 -->|ends| E1
    Q --> R["Result: Vael is no longer<br/>LEADER OF the Iron Ring"]
```

"Current state" (e.g. "what are the political relationships in Shadowbrook
right now?") is always a *query* over this log — never a separately
maintained table — because it's the only way to answer both "what's true
now" and "what was true as of session 5" from the same data. Extraction
prompts must be able to emit both "asserts" and "ends" events, not just
assertions.

This stays in Postgres rather than a dedicated graph database (Neo4j,
Apache AGE, Kùzu): campaign scale is small enough that recursive CTEs
handle multi-hop traversal fine, Apache AGE isn't supported on AWS
RDS/Aurora (relevant since AWS is the eventual deployment target), and
Kùzu's embedded-per-process model doesn't map cleanly to a future
multi-instance deployment. A dedicated embedded graph engine (Kùzu) remains
a documented upgrade path if path-finding queries ever get too painful in
SQL — not needed for the initial build.

## Hex-based conflict detection

Multiple DMs sharing one hex map can accidentally contradict each other's
lore. This no longer needs its own separate "draft-check" workflow: by the
time a session exists, its host has already tagged the location(s) and
quest(s) it's about (`SessionEntityLink` — see
[Data Model](data-model.md#session-activity-data-mutable-living-records)),
so pre-session planning is just a query against tags that already exist,
not something a DM fills out separately:

```mermaid
flowchart LR
    Tags["Session's tagged locations/quests<br/>(SessionEntityLink)"] --> Radius["Compute hex-radius<br/>candidate set (Python)"]
    Radius --> Search["pgvector similarity search<br/>scoped to candidate hexes"]
    Search --> LLM["LLM classifier:<br/>conflict? yes/no + why"]
    LLM --> Flag["Surface to DM during<br/>pre-session planning"]
```

- No PostGIS — it's a real geospatial engine, overkill for a hand-authored
  hex grid. Hex coordinates are plain integer columns (`hex_q`, `hex_r`,
  axial coordinates) on `Entity` records — explicit data the DM entered
  when creating the location, never inferred from prose (see
  [Structure over inference](data-model.md#structure-over-inference)).
- The radius search itself (e.g. "within 2 hexes") is a handful of lines of
  cube-coordinate distance math in Python, producing a candidate set of
  `(q, r)` pairs used as a plain `WHERE (hex_q, hex_r) IN (...)` filter
  against `lore_chunks`, combined with `pgvector` cosine-similarity
  ordering.
- The LLM's role is narrow and structured on purpose: a yes/no verdict plus
  a one-line explanation, not a rewritten story.

## Migrations

Schema changes are versioned Alembic migrations under `alembic/versions/`,
run via `poetry run alembic upgrade head`. `alembic/env.py` imports
`Base.metadata` from `app/db/models.py` directly (autogenerate diffs against
it) and reads the connection string from `app/db/session.py::DATABASE_URL`,
so the database URL has one source of truth rather than being duplicated in
`alembic.ini`. The baseline migration covers the schema as of the Discord
auth work (`campaigns`, `entities`, `people`); every feature phase in the
[Roadmap](roadmap.md) that adds a table (`session_logs`,
`relationship_events`, `rumors`, `lore_chunks`, and the full
[Data Model](data-model.md) set) adds its own migration on top.

## Containerization and local deployment

Today, `docker-compose.yml` only runs *infrastructure* (Postgres, Ollama) —
the API itself runs via `poetry run uvicorn` on the host. To support running
the whole stack locally (not just its dependencies), the plan adds:

- A `Dockerfile` (multi-stage: Poetry install, slim Python 3.12 runtime).
- `redis`, `api`, and `worker` services in `docker-compose.yml` — `api` and
  `worker` build from the same image and point `DATABASE_URL` /
  `OLLAMA_HOST` / `CELERY_BROKER_URL` at the other services by name instead
  of `localhost`.

`poetry run uvicorn --reload` on the host stays the fast inner-loop dev
workflow; `docker-compose up` becomes the full local-deployment mode that
exercises the same containers a future AWS deployment would mirror.

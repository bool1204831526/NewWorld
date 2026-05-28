# NewWorld Architecture Design

## 1. Product Positioning

NewWorld is a flexible multi-agent scenario simulator. It helps users place source material into a small world, generate actors and relationships, run interactions, and compare how opinions, narratives, risks, or decisions evolve.

The product should feel closer to a playful analysis lab than an academic modeling tool. It should be useful for:

- policy and public opinion reaction rehearsal
- market and competitor scenario exploration
- story world and character dynamics simulation
- community, forum, or social media narrative testing
- decision tabletop exercises

## 2. MVP Goal

The first useful version should answer one question:

> Given source material and a scenario prompt, what actors appear, what do they want, how might they interact, and what outcomes are plausible?

The MVP should include:

- document or pasted text input
- entity, relationship, and conflict extraction
- agent generation from extracted actors
- round-based interaction simulation
- visual actor map
- live interaction feed
- final scenario report
- saved simulation runs

## 3. Core Concepts

### World

A world is the simulation container. It stores the scenario, source materials, extracted ontology, agents, environment rules, and run history.

### Source

A source is any input material: pasted text, markdown, PDF text extraction, URL snapshot, notes, or structured JSON.

### Entity

An entity is a named object extracted from sources: person, organization, place, policy, product, event, metric, community, or abstract concept.

### Relationship

A relationship links entities with a typed edge such as supports, opposes, funds, regulates, competes with, depends on, influences, or mentions.

### Agent

An agent is an active participant derived from entities or created manually. It has goals, beliefs, constraints, memory, tone, influence, and decision rules.

### Environment

The environment is where agents interact. Early versions can use a shared feed. Later versions may support channels, news events, markets, polls, and private messages.

### Run

A run is one execution of a scenario. It records configuration, messages, state transitions, metrics, and the final report.

## 4. System Architecture

Recommended starting stack:

- Frontend: React + TypeScript + Vite
- Backend API: Python FastAPI
- Database: SQLite for local MVP, PostgreSQL later
- ORM: SQLModel or SQLAlchemy
- Task execution: simple in-process worker first, queue later
- LLM provider: adapter interface, OpenAI first, local models later
- Visualization: React Flow or Cytoscape for graph, simple feed components for interactions

High-level modules:

```text
frontend/
  app shell, world editor, graph view, feed view, report view

backend/
  api routes, application services, simulation engine, provider adapters

storage/
  database models, migrations, repository layer

engine/
  extraction, agent generation, simulation loop, report generation

docs/
  architecture, product notes, API notes
```

## 5. Backend Module Design

### API Layer

Responsibilities:

- accept sources and scenario prompts
- create and update worlds
- start simulation runs
- stream or poll run progress
- return graph, feed, metrics, and reports

Initial endpoints:

- `POST /worlds`
- `GET /worlds`
- `GET /worlds/{world_id}`
- `POST /worlds/{world_id}/sources`
- `POST /worlds/{world_id}/extract`
- `POST /worlds/{world_id}/agents`
- `POST /worlds/{world_id}/runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`

### Extraction Service

Input:

- source text
- optional user focus
- extraction schema version

Output:

- entities
- relationships
- claims
- uncertainties
- source citations

MVP can start with LLM JSON extraction and schema validation. Use deterministic fallback heuristics only for demos and tests.

### Agent Service

Creates agents from entities and user edits.

Agent fields:

- name
- represented entity
- role
- goals
- beliefs
- constraints
- stance
- influence
- communication style
- memory summary

### Simulation Engine

The simulation loop should be explicit and inspectable:

1. Build round context from world state.
2. Select active agents.
3. Generate each agent action.
4. Apply environment effects.
5. Update memories and metrics.
6. Store events.
7. Stop when rounds finish or convergence occurs.

Initial action types:

- post
- reply
- amplify
- challenge
- ask_for_evidence
- form_alliance
- change_stance

### Report Service

Produces:

- outcome forecast
- strongest narratives
- stakeholder shifts
- conflict points
- uncertainty drivers
- recommended next scenarios
- citations to source and run events

## 6. Frontend Experience

The first screen should be the actual workspace, not a marketing page.

Primary layout:

- left sidebar: worlds, sources, run controls
- center: graph and feed tabs
- right panel: selected entity or agent details
- bottom or separate tab: report and comparisons

Important interactions:

- paste source material
- run extraction
- inspect and edit entities
- inspect and edit agents
- start simulation
- watch feed update
- open final report
- duplicate a run with a changed assumption

Visual tone:

- simple, lively, and clear
- avoid overly academic wording
- use familiar labels such as World, People, Feed, Map, Runs, Report

## 7. Data Model Draft

```text
World
  id, name, description, created_at, updated_at

Source
  id, world_id, type, title, content, metadata, created_at

Entity
  id, world_id, name, type, summary, confidence, source_refs

Relationship
  id, world_id, source_entity_id, target_entity_id, type, summary, weight, confidence, source_refs

Agent
  id, world_id, entity_id, name, role, goals, beliefs, constraints, stance, influence, style, memory

Run
  id, world_id, status, config, started_at, completed_at

RunEvent
  id, run_id, round, agent_id, action_type, content, state_delta, metrics, created_at

Report
  id, run_id, summary, sections, citations, created_at
```

## 8. LLM Adapter Design

Use provider adapters so the app is not locked to one model.

Core interface:

```text
generate_json(task, schema, messages, temperature)
generate_text(task, messages, temperature)
embed(texts)
```

Provider implementations:

- OpenAI adapter
- local model adapter
- mock adapter for tests

All model outputs must be validated before entering storage.

## 9. Prompting Boundaries

Prompts should be versioned and treated as product code.

Suggested prompt files:

```text
backend/prompts/extract_world.md
backend/prompts/create_agents.md
backend/prompts/agent_turn.md
backend/prompts/summarize_run.md
```

Each prompt should define:

- task
- input contract
- output schema
- constraints
- examples only when needed

## 10. Development Phases

### Phase 0: Foundation

- repo initialized
- architecture document
- project skill
- basic project skeleton

### Phase 1: Local MVP

- FastAPI backend
- React workspace
- SQLite persistence
- pasted text input
- LLM-backed extraction
- simple agent generation
- round simulation
- report generation

### Phase 2: Better Worlds

- editable graph
- saved runs
- comparison view
- source citations
- prompt/version tracking
- streaming progress

### Phase 3: Rich Simulation

- private channels
- event injection
- metrics and polls
- memory evolution
- scenario branching
- batch experiments

### Phase 4: Collaboration and Deployment

- hosted deployment
- user accounts
- shared worlds
- export reports
- remote model configuration

## 11. Testing Strategy

Test levels:

- unit tests for schema validation and deterministic services
- snapshot tests for prompt output parsers
- API tests for world and run flows
- frontend component tests for main workspace views
- end-to-end smoke test for create world -> extract -> simulate -> report

Use mock LLM providers in CI. Real provider tests should be opt-in and require explicit environment variables.

## 12. Engineering Principles

- Keep model-facing schemas explicit.
- Store raw model outputs only as debug artifacts, not trusted state.
- Make simulation steps replayable.
- Keep user-editable state separate from generated suggestions.
- Prefer narrow, useful MVP flows over broad demos.
- Treat reports as explainable summaries with citations to sources and run events.

## 13. Immediate Next Step

Create the first runnable skeleton:

- `backend/` FastAPI app with health check
- `frontend/` Vite React app with a simple workspace shell
- `docker-compose.yml` optional later, not required for local MVP
- development scripts documented in README

# Graph Report - .  (2026-06-21)

## Corpus Check
- Corpus is ~1,135 words - fits in a single context window. You may not need a graph.

## Summary
- 46 nodes · 50 edges · 7 communities (6 shown, 1 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Frontend Stack|Frontend Stack]]
- [[_COMMUNITY_Roadmap and Future Vision|Roadmap and Future Vision]]
- [[_COMMUNITY_Integrations and Agents|Integrations and Agents]]
- [[_COMMUNITY_Current Sprint and Data Models|Current Sprint and Data Models]]
- [[_COMMUNITY_Backend Stack|Backend Stack]]
- [[_COMMUNITY_Architecture and Design Principles|Architecture and Design Principles]]
- [[_COMMUNITY_Sprint Workflow|Sprint Workflow]]

## God Nodes (most connected - your core abstractions)
1. `Frontend Stack` - 10 edges
2. `Personal OS Roadmap` - 9 edges
3. `Personal OS` - 8 edges
4. `Stage 1: Foundation Sprint` - 7 edges
5. `Stage 6: Agents` - 7 edges
6. `Backend Stack` - 6 edges
7. `SQLModel` - 3 edges
8. `Stage 2: Integrations` - 3 edges
9. `Stage 5: Knowledge System` - 3 edges
10. `Zustand` - 2 edges

## Surprising Connections (you probably didn't know these)
- `Personal OS` --references--> `Stage 1: Foundation Sprint`  [EXTRACTED]
  CLAUDE.md → CURRENT_SPRINT.md
- `Personal OS` --references--> `Personal OS Roadmap`  [EXTRACTED]
  CLAUDE.md → ROADMAP.md
- `Synapse` --conceptually_related_to--> `Personal OS`  [EXTRACTED]
  README.md → CLAUDE.md
- `DashboardWidget Model` --implements--> `SQLModel`  [INFERRED]
  CURRENT_SPRINT.md → CLAUDE.md
- `User Model` --implements--> `SQLModel`  [INFERRED]
  CURRENT_SPRINT.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Backend Technology Stack** — claude_fastapi, claude_sqlmodel, claude_sqlite, claude_apscheduler, claude_pydantic [EXTRACTED 1.00]
- **Frontend Technology Stack** — claude_react, claude_typescript, claude_vite, claude_tailwind, claude_react_query, claude_zustand, claude_react_router, claude_shadcn, claude_magicui [EXTRACTED 1.00]
- **Personal OS Development Stages** — roadmap_stage1, roadmap_stage2, roadmap_stage3, roadmap_stage4, roadmap_stage5, roadmap_stage6, roadmap_stage7 [EXTRACTED 1.00]
- **Stage 1 Database Models** — current_sprint_user_model, current_sprint_dashboardwidget_model [EXTRACTED 1.00]

## Communities (7 total, 1 thin omitted)

### Community 0 - "Frontend Stack"
Cohesion: 0.18
Nodes (11): Frontend Stack, Magic UI, React 18, React Query, React Router, shadcn/ui, Tailwind CSS, TypeScript (+3 more)

### Community 1 - "Roadmap and Future Vision"
Cohesion: 0.22
Nodes (9): Future Features, Personal OS Roadmap, Qdrant, RAG Pipelines, Stage 3: Notifications, Stage 4: AI Layer, Stage 5: Knowledge System, Stage 7: Automation (+1 more)

### Community 2 - "Integrations and Agents"
Cohesion: 0.29
Nodes (8): Calendar Agent, Email Agent, Gmail Integration, Google Calendar Integration, Notification Agent, Stage 2: Integrations, Stage 6: Agents, Study Agent

### Community 3 - "Current Sprint and Data Models"
Cohesion: 0.33
Nodes (7): SQLModel, Dashboard Widgets, DashboardWidget Model, Health Endpoint, Stage 1: Foundation Sprint, User Model, Stage 1: Foundation

### Community 4 - "Backend Stack"
Cohesion: 0.40
Nodes (5): APScheduler, Backend Stack, FastAPI, Pydantic v2, SQLite

### Community 5 - "Architecture and Design Principles"
Cohesion: 0.40
Nodes (5): Design Principles, Engineering Philosophy, Modular Monolith Architecture, Personal OS, Synapse

## Knowledge Gaps
- **26 isolated node(s):** `Sprint Completion Workflow`, `FastAPI`, `SQLite`, `APScheduler`, `Pydantic v2` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Personal OS` connect `Architecture and Design Principles` to `Frontend Stack`, `Roadmap and Future Vision`, `Current Sprint and Data Models`, `Backend Stack`?**
  _High betweenness centrality (0.634) - this node is a cross-community bridge._
- **Why does `Personal OS Roadmap` connect `Roadmap and Future Vision` to `Integrations and Agents`, `Current Sprint and Data Models`, `Architecture and Design Principles`?**
  _High betweenness centrality (0.553) - this node is a cross-community bridge._
- **Why does `Frontend Stack` connect `Frontend Stack` to `Architecture and Design Principles`?**
  _High betweenness centrality (0.347) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Stage 6: Agents` (e.g. with `Gmail Integration` and `Google Calendar Integration`) actually correct?**
  _`Stage 6: Agents` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Engineering Philosophy`, `Modular Monolith Architecture`, `Design Principles` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
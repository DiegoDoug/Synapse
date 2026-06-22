# Graph Report - .  (2026-06-22)

## Corpus Check
- Corpus is ~2,564 words - fits in a single context window. You may not need a graph.

## Summary
- 89 nodes · 77 edges · 21 communities (11 shown, 10 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Backend Layer (FastAPI + Integrations)|Backend Layer (FastAPI + Integrations)]]
- [[_COMMUNITY_Product Capabilities|Product Capabilities]]
- [[_COMMUNITY_Roadmap and Future Vision|Roadmap and Future Vision]]
- [[_COMMUNITY_Design Principles|Design Principles]]
- [[_COMMUNITY_Integrations and Agents (Roadmap)|Integrations and Agents (Roadmap)]]
- [[_COMMUNITY_Frontend Layer (React Stack)|Frontend Layer (React Stack)]]
- [[_COMMUNITY_Current Sprint|Current Sprint]]
- [[_COMMUNITY_Architecture Patterns|Architecture Patterns]]
- [[_COMMUNITY_Documentation Hierarchy|Documentation Hierarchy]]
- [[_COMMUNITY_Engineering Philosophy|Engineering Philosophy]]
- [[_COMMUNITY_Coding Standards|Coding Standards]]
- [[_COMMUNITY_Scheduling (APScheduler)|Scheduling (APScheduler)]]
- [[_COMMUNITY_LLM APIs|LLM APIs]]
- [[_COMMUNITY_Magic UI|Magic UI]]
- [[_COMMUNITY_Qdrant (Vector DB)|Qdrant (Vector DB)]]
- [[_COMMUNITY_Redis (Cache)|Redis (Cache)]]
- [[_COMMUNITY_shadcnui|shadcn/ui]]
- [[_COMMUNITY_Telegram Integration|Telegram Integration]]
- [[_COMMUNITY_Vite (Bundler)|Vite (Bundler)]]
- [[_COMMUNITY_Sprint Completion Process|Sprint Completion Process]]
- [[_COMMUNITY_Output Rules|Output Rules]]

## God Nodes (most connected - your core abstractions)
1. `Personal OS Roadmap` - 8 edges
2. `Personal OS` - 8 edges
3. `Stage 6: Agents` - 7 edges
4. `Design Principles` - 7 edges
5. `Stage 1: Foundation Sprint` - 6 edges
6. `Engineering Philosophy` - 5 edges
7. `Instruction Hierarchy` - 4 edges
8. `System Overview` - 4 edges
9. `Frontend Layer` - 4 edges
10. `Backend Layer` - 4 edges

## Surprising Connections (you probably didn't know these)
- `Stage 1: Foundation` --conceptually_related_to--> `Stage 1: Foundation Sprint`  [EXTRACTED]
  ROADMAP.md → CURRENT_SPRINT.md
- `Synapse` --conceptually_related_to--> `Personal OS`  [EXTRACTED]
  README.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Stage 1 Database Models** — current_sprint_user_model, current_sprint_dashboardwidget_model [EXTRACTED 1.00]
- **Personal OS Development Stages** — roadmap_stage1, roadmap_stage2, roadmap_stage3, roadmap_stage4, roadmap_stage5, roadmap_stage6, roadmap_stage7 [EXTRACTED 1.00]
- **Backend Technology Stack** — architecture_python_312, architecture_fastapi, architecture_sqlmodel, architecture_pydantic_v2, architecture_apscheduler [EXTRACTED 1.00]
- **Frontend Technology Stack** — architecture_react_18, architecture_typescript, architecture_vite, architecture_tailwind, architecture_zustand, architecture_react_query, architecture_react_router, architecture_shadcn_ui, architecture_magic_ui [EXTRACTED 1.00]
- **Database Options** — architecture_sqlite, architecture_postgresql, architecture_redis, architecture_qdrant [EXTRACTED 1.00]
- **Core Integrations** — architecture_gmail_integration, architecture_google_calendar_integration, architecture_telegram_integration, architecture_llm_apis_integration [EXTRACTED 1.00]
- **Personal OS Core Capabilities** — claude_unified_information_access, claude_contextual_ai_assistance, claude_automation_workflows, claude_agent_systems, claude_notification_systems, claude_personal_knowledge_management [EXTRACTED 1.00]
- **Engineering Priorities** — governance_maintainability, governance_modularity, governance_simplicity, governance_scalability, governance_developer_experience [EXTRACTED 1.00]
- **Design System Principles** — governance_dark_mode_first, governance_mobile_responsive, governance_minimal_design, governance_small_components [EXTRACTED 1.00]
- **Documentation Structure and Hierarchy** — claude_current_sprint_md, claude_roadmap_md, claude_architecture_md, claude_governance_md, claude_instruction_hierarchy [EXTRACTED 1.00]
- **Backend Layered Architecture** — architecture_backend_layer, architecture_service_layer, architecture_integration_layer, architecture_repository_layer [EXTRACTED 1.00]

## Communities (21 total, 10 thin omitted)

### Community 0 - "Backend Layer (FastAPI + Integrations)"
Cohesion: 0.20
Nodes (10): Backend Layer, FastAPI, Gmail Integration, Google Calendar Integration, Integration Layer, Pydantic v2, Python 3.12, Repository Layer (+2 more)

### Community 1 - "Product Capabilities"
Cohesion: 0.22
Nodes (9): Agent Systems, Automation Workflows, Contextual AI Assistance, Notification Systems, Personal Knowledge Management, Personal OS, Unified Dashboard, Unified Information Access (+1 more)

### Community 2 - "Roadmap and Future Vision"
Cohesion: 0.22
Nodes (9): Future Features, Personal OS Roadmap, Qdrant, RAG Pipelines, Stage 3: Notifications, Stage 4: AI Layer, Stage 5: Knowledge System, Stage 7: Automation (+1 more)

### Community 3 - "Design Principles"
Cohesion: 0.25
Nodes (8): Async APIs, Clear Separation of Concerns, Dark Mode First, Design Principles, Minimal Design, Mobile Responsive, Small Components, Strong Typing

### Community 4 - "Integrations and Agents (Roadmap)"
Cohesion: 0.29
Nodes (8): Calendar Agent, Email Agent, Gmail Integration, Google Calendar Integration, Notification Agent, Stage 2: Integrations, Stage 6: Agents, Study Agent

### Community 5 - "Frontend Layer (React Stack)"
Cohesion: 0.29
Nodes (7): Frontend Layer, React 18, React Query, React Router, Tailwind CSS, TypeScript, Zustand

### Community 6 - "Current Sprint"
Cohesion: 0.29
Nodes (7): Dashboard Widgets, DashboardWidget Model, Health Endpoint, Stage 1: Foundation Sprint, useAppStore, User Model, Stage 1: Foundation

### Community 7 - "Architecture Patterns"
Cohesion: 0.40
Nodes (6): Agents (AI Layer), Database Layer, Modular Monolith Architecture, PostgreSQL, SQLite, System Overview

### Community 8 - "Documentation Hierarchy"
Cohesion: 0.47
Nodes (6): ARCHITECTURE.md, CURRENT_SPRINT.md, Development Workflow, GOVERNANCE.md, Instruction Hierarchy, ROADMAP.md

### Community 9 - "Engineering Philosophy"
Cohesion: 0.33
Nodes (6): Developer Experience, Engineering Philosophy, Maintainability, Modularity, Scalability, Simplicity

### Community 10 - "Coding Standards"
Cohesion: 0.67
Nodes (3): Coding Standards, Python Standards, TypeScript Standards

## Knowledge Gaps
- **30 isolated node(s):** `Dashboard Widgets`, `Health Endpoint`, `useAppStore`, `User Model`, `DashboardWidget Model` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Personal OS Roadmap` connect `Roadmap and Future Vision` to `Integrations and Agents (Roadmap)`, `Current Sprint`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `System Overview` connect `Architecture Patterns` to `Backend Layer (FastAPI + Integrations)`, `Frontend Layer (React Stack)`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Backend Layer` connect `Backend Layer (FastAPI + Integrations)` to `Architecture Patterns`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Stage 6: Agents` (e.g. with `Gmail Integration` and `Google Calendar Integration`) actually correct?**
  _`Stage 6: Agents` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Dashboard Widgets`, `Health Endpoint`, `useAppStore` to the rest of the system?**
  _59 weakly-connected nodes found - possible documentation gaps or missing edges._
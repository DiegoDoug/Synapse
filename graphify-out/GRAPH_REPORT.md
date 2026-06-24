# Graph Report - .  (2026-06-24)

## Corpus Check
- Corpus is ~2,769 words - fits in a single context window. You may not need a graph.

## Summary
- 83 nodes · 96 edges · 9 communities (7 shown, 2 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Service-Integration-Agent Chain|Service-Integration-Agent Chain]]
- [[_COMMUNITY_Documentation Layer + Design Principles|Documentation Layer + Design Principles]]
- [[_COMMUNITY_Roadmap Integrations and Agents|Roadmap: Integrations and Agents]]
- [[_COMMUNITY_Product Capabilities|Product Capabilities]]
- [[_COMMUNITY_Runtime Architecture|Runtime Architecture]]
- [[_COMMUNITY_Current Sprint|Current Sprint]]
- [[_COMMUNITY_Instruction Hierarchy|Instruction Hierarchy]]
- [[_COMMUNITY_Telegram Integration|Telegram Integration]]
- [[_COMMUNITY_Sprint Completion Process|Sprint Completion Process]]

## God Nodes (most connected - your core abstractions)
1. `Personal OS` - 8 edges
2. `Personal OS Roadmap` - 8 edges
3. `Service Layer` - 8 edges
4. `Stage 6: Agents` - 7 edges
5. `Stage 1: Foundation Sprint` - 6 edges
6. `Backend (FastAPI)` - 6 edges
7. `Personal OS` - 5 edges
8. `Agents (AI Layer)` - 5 edges
9. `Instruction Hierarchy` - 4 edges
10. `Frontend (React + TypeScript)` - 4 edges

## Surprising Connections (you probably didn't know these)
- `Dark Mode First` --rationale_for--> `Frontend (React + TypeScript)`  [INFERRED]
  GOVERNANCE.md → ARCHITECTURE.md
- `Clear Separation of Concerns` --rationale_for--> `Service Layer`  [INFERRED]
  GOVERNANCE.md → ARCHITECTURE.md
- `Synapse` --conceptually_related_to--> `Personal OS`  [EXTRACTED]
  README.md → CLAUDE.md
- `Stage 1: Foundation` --conceptually_related_to--> `Stage 1: Foundation Sprint`  [EXTRACTED]
  ROADMAP.md → CURRENT_SPRINT.md
- `Modularity` --rationale_for--> `Modular Monolith`  [INFERRED]
  GOVERNANCE.md → ARCHITECTURE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Personal OS Core Capabilities** — claude_unified_information_access, claude_contextual_ai_assistance, claude_automation_workflows, claude_agent_systems, claude_notification_systems, claude_personal_knowledge_management [EXTRACTED 1.00]
- **Documentation Structure and Hierarchy** — claude_current_sprint_md, claude_roadmap_md, claude_architecture_md, claude_governance_md, claude_instruction_hierarchy [EXTRACTED 1.00]
- **Stage 1 Database Models** — current_sprint_user_model, current_sprint_dashboardwidget_model [EXTRACTED 1.00]
- **Personal OS Development Stages** — roadmap_stage1, roadmap_stage2, roadmap_stage3, roadmap_stage4, roadmap_stage5, roadmap_stage6, roadmap_stage7 [EXTRACTED 1.00]
- **Instruction Precedence Hierarchy** — governance_current_sprint_doc, governance_roadmap_doc, architecture_doc, governance_doc, governance_claude_doc [EXTRACTED 1.00]
- **Email Service-Integration-Agent Chain** — architecture_email_agent, architecture_email_service, architecture_gmail_integration, architecture_gmail_api [EXTRACTED 1.00]
- **Calendar Service-Integration-Agent Chain** — architecture_calendar_agent, architecture_calendar_service, architecture_google_calendar_integration, architecture_google_calendar_api [EXTRACTED 1.00]
- **Backend Dependency Flow** — architecture_http_route, architecture_service_layer, architecture_repository_layer, architecture_sqlmodel, architecture_integration_layer [EXTRACTED 1.00]
- **Engineering Philosophy Priorities** — governance_maintainability, governance_modularity, governance_simplicity, governance_scalability, governance_developer_experience [EXTRACTED 1.00]
- **Design Principles** — governance_dark_mode_first, governance_mobile_responsive, governance_minimal_design, governance_small_components, governance_strong_typing, governance_async_apis, governance_separation_of_concerns [EXTRACTED 1.00]

## Communities (9 total, 2 thin omitted)

### Community 0 - "Service-Integration-Agent Chain"
Cohesion: 0.16
Nodes (18): Agents (AI Layer), Backend (FastAPI), Calendar Agent, Calendar Service, Email Agent, Email Service, FastAPI, Gmail API (+10 more)

### Community 1 - "Documentation Layer + Design Principles"
Cohesion: 0.16
Nodes (15): Async APIs, CLAUDE.md, CURRENT_SPRINT.md, Dark Mode First, Developer Experience, Incremental Build, Maintainability, Minimal Design (+7 more)

### Community 2 - "Roadmap: Integrations and Agents"
Cohesion: 0.13
Nodes (17): Calendar Agent, Email Agent, Future Features, Gmail Integration, Google Calendar Integration, Notification Agent, Personal OS Roadmap, Qdrant (+9 more)

### Community 3 - "Product Capabilities"
Cohesion: 0.22
Nodes (9): Agent Systems, Automation Workflows, Contextual AI Assistance, Notification Systems, Personal Knowledge Management, Personal OS, Unified Dashboard, Unified Information Access (+1 more)

### Community 4 - "Runtime Architecture"
Cohesion: 0.29
Nodes (7): Database (SQLite), Frontend (React + TypeScript), Modular Monolith, Personal OS, React Query, Zustand, Modularity

### Community 5 - "Current Sprint"
Cohesion: 0.29
Nodes (7): Dashboard Widgets, DashboardWidget Model, Health Endpoint, Stage 1: Foundation Sprint, useAppStore, User Model, Stage 1: Foundation

### Community 6 - "Instruction Hierarchy"
Cohesion: 0.40
Nodes (6): ARCHITECTURE.md, CURRENT_SPRINT.md, Development Workflow, GOVERNANCE.md, Instruction Hierarchy, ROADMAP.md

## Knowledge Gaps
- **39 isolated node(s):** `ARCHITECTURE.md`, `GOVERNANCE.md`, `Dashboard Widgets`, `Health Endpoint`, `useAppStore` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Clear Separation of Concerns` connect `Service-Integration-Agent Chain` to `Documentation Layer + Design Principles`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `Personal OS Roadmap` connect `Roadmap: Integrations and Agents` to `Current Sprint`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Service Layer` (e.g. with `Calendar Service` and `Email Service`) actually correct?**
  _`Service Layer` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Stage 6: Agents` (e.g. with `Gmail Integration` and `Google Calendar Integration`) actually correct?**
  _`Stage 6: Agents` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Unified Dashboard`, `Unified Information Access`, `Contextual AI Assistance` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Roadmap: Integrations and Agents` be split into smaller, more focused modules?**
  _Cohesion score 0.1323529411764706 - nodes in this community are weakly interconnected._
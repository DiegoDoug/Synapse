"""Agent layer (Stage 6).

Domain agents that orchestrate the existing service layer into autonomous
multi-step workflows. Agents drive the Stage 4 read tools and Stage 4.5 write
tools through the shared ``ToolRegistry`` in a plan→act→observe loop; they never
call integrations directly (see ARCHITECTURE.md: Agent → Service → Integration).
Every run is recorded to the ``AgentRun`` audit trail by the ``AgentRunner``.
"""

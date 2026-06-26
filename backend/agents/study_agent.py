"""StudyAgent — assembles a study briefing from the user's own data.

The Stage 6 reference agent, end to end over the existing tools:

1. read the upcoming schedule (``get_calendar_events``) to find deadlines,
2. pull relevant material from the knowledge base (``search_knowledge``),
3. create a study task (``create_task``) — an autonomous create that the
   confirmation flow executes immediately,

then compose a short briefing referencing what it found. It composes read tools
and a write tool without per-step prompting, and degrades gracefully: if the
knowledge base is unavailable the search step records that and the briefing is
built from the schedule alone.
"""

from __future__ import annotations

from backend.agents.base import Agent, AgentContext

# Fallback search query when the run supplies no explicit topic.
_DEFAULT_QUERY = "upcoming exams, assignments, and deadlines"
# Keep the generated task description within the TaskCreate schema's 2000-char cap.
_MAX_DESCRIPTION = 1800


class StudyAgent(Agent):
    key = "study"
    name = "Study Briefing"
    description = (
        "Reviews your upcoming schedule and knowledge base, then prepares a "
        "study briefing and a task to act on it."
    )
    parameters = [
        {
            "name": "topic",
            "type": "string",
            "required": False,
            "description": "What to focus the briefing on (optional).",
        }
    ]

    def plan(self, ctx: AgentContext) -> str:
        topic = ctx.param("topic")
        focus = f" on '{topic}'" if topic else ""
        return (
            f"Review the upcoming schedule, search the knowledge base{focus}, "
            "and create a study task summarising what to prepare."
        )

    def run(self, ctx: AgentContext) -> str:
        topic = ctx.param("topic")
        query = topic or _DEFAULT_QUERY

        schedule = ctx.act(
            "get_calendar_events",
            {"limit": 5},
            title="Review upcoming schedule",
        )
        material = ctx.act(
            "search_knowledge",
            {"query": query, "limit": 5},
            title=f"Search knowledge base for {query}",
        )

        focus = topic or "upcoming work"
        description = (
            f"Study briefing for {focus}.\n\n"
            f"Upcoming schedule:\n{schedule}\n\n"
            f"Relevant material:\n{material}"
        )[:_MAX_DESCRIPTION]
        ctx.act(
            "create_task",
            {
                "title": f"Study: {focus}",
                "description": description,
                "priority": "high",
            },
            title=f"Create study task for {focus}",
        )

        return (
            f"Prepared a study briefing for {focus} and created a study task. "
            f"Upcoming schedule:\n{schedule}\n\nRelevant material:\n{material}"
        )

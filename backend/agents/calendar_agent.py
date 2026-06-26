"""CalendarAgent — turn the upcoming schedule into a meeting-prep task.

Reviews upcoming events (``get_calendar_events``), pulls any relevant agendas or
prep notes from the knowledge base (``search_knowledge``), and creates a
consolidated prep task (``create_task``, autonomous). Where StudyAgent focuses on
study material, this agent focuses on meeting logistics. It reads the calendar
only through the tool layer, never the Google integration directly, and degrades
gracefully when the knowledge base is unavailable.
"""

from __future__ import annotations

from backend.agents.base import Agent, AgentContext

# Keep the generated task description within the TaskCreate schema's 2000-char cap.
_MAX_DESCRIPTION = 1800


class CalendarAgent(Agent):
    key = "calendar"
    name = "Meeting Prep"
    description = (
        "Reviews your upcoming schedule and prep notes, then creates a task to "
        "get you ready for what's coming up."
    )
    parameters: list[dict] = []

    def plan(self, ctx: AgentContext) -> str:
        return (
            "Review the upcoming schedule, gather relevant prep notes from the "
            "knowledge base, and create a meeting-prep task."
        )

    def run(self, ctx: AgentContext) -> str:
        events = ctx.act(
            "get_calendar_events",
            {"limit": 10},
            title="Review upcoming schedule",
        )
        prep = ctx.act(
            "search_knowledge",
            {"query": "meeting agendas, prep notes, and action items", "limit": 5},
            title="Find meeting prep material",
        )

        description = (
            f"Upcoming schedule:\n{events}\n\nPrep material:\n{prep}"
        )[:_MAX_DESCRIPTION]
        ctx.act(
            "create_task",
            {
                "title": "Prepare for upcoming meetings",
                "description": description,
                "priority": "high",
            },
            title="Create a meeting-prep task",
        )

        return (
            "Reviewed your schedule and created a meeting-prep task.\n\n"
            f"Upcoming schedule:\n{events}\n\nPrep material:\n{prep}"
        )

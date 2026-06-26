"""EmailAgent — triage the unread inbox into a follow-up task.

Scans the user's unread mail (``search_emails``) and turns it into a single
follow-up task (``create_task``, an autonomous create) so nothing slips. Reads
email and writes a task entirely through the tool layer — it never touches the
Gmail integration directly.
"""

from __future__ import annotations

from backend.agents.base import Agent, AgentContext

# Keep the generated task description within the TaskCreate schema's 2000-char cap.
_MAX_DESCRIPTION = 1800


class EmailAgent(Agent):
    key = "email"
    name = "Inbox Triage"
    description = (
        "Scans your unread email and creates a single follow-up task so nothing "
        "important slips through."
    )
    parameters = [
        {
            "name": "query",
            "type": "string",
            "required": False,
            "description": "Only triage unread mail matching this text (optional).",
        }
    ]

    def plan(self, ctx: AgentContext) -> str:
        query = ctx.param("query")
        scope = f" matching '{query}'" if query else ""
        return (
            f"Scan unread email{scope} and create a follow-up task summarising "
            "what needs a reply."
        )

    def run(self, ctx: AgentContext) -> str:
        query = ctx.param("query")
        args = {"unread_only": True, "limit": 10}
        if query:
            args["query"] = query

        unread = ctx.act("search_emails", args, title="Scan unread inbox")

        description = (
            f"Unread email to follow up on:\n{unread}"
        )[:_MAX_DESCRIPTION]
        ctx.act(
            "create_task",
            {
                "title": "Triage unread inbox",
                "description": description,
                "priority": "normal",
            },
            title="Create a follow-up task",
        )

        return f"Triaged the unread inbox and created a follow-up task.\n\n{unread}"

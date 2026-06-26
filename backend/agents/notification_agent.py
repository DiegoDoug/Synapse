"""NotificationAgent — compose a daily digest and propose delivering it.

Aggregates across the user's synced data — unread email (``search_emails``),
upcoming events (``get_calendar_events``), and in-app notifications
(``get_notifications``) — into one digest, then proposes sending it over Telegram
(``send_telegram_message``). The send is an outbound action, so it routes through
the confirmation flow as a pending action: the agent records that it is awaiting
approval rather than firing it, which is exactly the auditable destructive-action
path the architecture requires of agents.
"""

from __future__ import annotations

from backend.agents.base import Agent, AgentContext

# Telegram messages cap at 4096 chars; stay well under once framing is added.
_MAX_DIGEST = 3500


class NotificationAgent(Agent):
    key = "notification"
    name = "Daily Digest"
    description = (
        "Aggregates your unread email, upcoming events, and notifications into a "
        "digest and proposes sending it to you over Telegram."
    )
    parameters: list[dict] = []

    def plan(self, ctx: AgentContext) -> str:
        return (
            "Gather unread email, upcoming events, and notifications, compose a "
            "digest, and propose delivering it over Telegram for approval."
        )

    def run(self, ctx: AgentContext) -> str:
        emails = ctx.act(
            "search_emails",
            {"unread_only": True, "limit": 5},
            title="Collect unread email",
        )
        events = ctx.act(
            "get_calendar_events",
            {"limit": 5},
            title="Collect upcoming events",
        )
        notifications = ctx.act(
            "get_notifications",
            {"limit": 5},
            title="Collect in-app notifications",
        )

        digest = (
            "Your daily digest\n\n"
            f"Unread email:\n{emails}\n\n"
            f"Upcoming events:\n{events}\n\n"
            f"Notifications:\n{notifications}"
        )[:_MAX_DIGEST]

        # Outbound: the confirmation flow stores this as a pending action; the
        # step records that it awaits approval rather than sending immediately.
        delivery = ctx.act(
            "send_telegram_message",
            {"text": digest},
            title="Propose sending the digest to Telegram",
        )

        return f"Composed a daily digest. {delivery}"

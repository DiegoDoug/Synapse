"""Integration layer — thin external API clients.

Integrations hold HTTP/SDK logic only. They never access the database and
never contain business logic; the service layer orchestrates them. See
ARCHITECTURE.md (Service → Integration contract).
"""

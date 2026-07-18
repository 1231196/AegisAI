"""Shared exception types.

``ConflictError`` is raised by SQL-backed repository methods when a
uniqueness / referential precheck fails, and translated to HTTP 409 by
the exception handler registered in ``app.main``. Keeping it here
means routers never have to ``try/except`` for these.

Without this surface the router's precheck-then-insert sequence would
either race (two concurrent registrations for the same email both pass
the precheck) or require per-router exception handling. Centralising
the conflict signal in one typed exception is the minimal fix.
"""

from __future__ import annotations


class ConflictError(Exception):
    """Raised when a repository-level uniqueness/ref check fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

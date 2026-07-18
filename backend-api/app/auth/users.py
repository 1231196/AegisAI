"""Bcrypt sentinel used to keep login response time roughly constant for both
unknown users and wrong-password attempts.

This module exists separately from ``repositories.py`` so the constant is
loaded without pulling in the broader auth-repository surface; the login
route imports it directly.
"""

from __future__ import annotations

import bcrypt

# One precomputed real-format bcrypt hash used for unknown-user login
# attempts. ``verify_password`` runs against it so the response time is
# the same as a real-user check (~250 ms at default cost=12), preventing a
# trivial username-existence leak via timing.
UNREACHABLE_HASH: str = bcrypt.hashpw(
    b"unreachable-dummy-password",
    bcrypt.gensalt(),
).decode("utf-8")

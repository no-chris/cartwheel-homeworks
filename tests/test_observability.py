"""HW2 Part D: authentication tests for the session endpoints.

Offline by design: no Langfuse, no Docker, no model provider key. Tracing is
verified by reading spans in Langfuse (Part E), not here.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from server import app as server_app


@pytest.fixture(autouse=True)
def _clean_sessions() -> None:
    """_SESSIONS is module-level global state; keep tests independent."""
    server_app._SESSIONS.clear()


def test_create_session_rejects_role_that_differs_from_database() -> None:
    """User 9002 is a merchant. A support claim must not create a session."""
    with pytest.raises(HTTPException) as exc:
        server_app.create_session(
            server_app.SessionCreate(user_id=9002, role="support")
        )

    assert exc.value.status_code == 403
    # Refusing with the right status but still creating the session would
    # leave a usable support session behind.
    assert server_app._SESSIONS == {}


def test_token_from_one_session_cannot_authorize_another() -> None:
    """A valid, correctly signed token is still scoped to its own session."""
    first = server_app.create_session(
        server_app.SessionCreate(user_id=1, role="shopper")
    )
    second = server_app.create_session(
        server_app.SessionCreate(user_id=1, role="shopper")
    )

    # Sanity: the token works for the session it was issued for. Without this,
    # an _authorize that rejected everything would also pass the check below.
    ctx = server_app._authorize(first["session_id"], f"Bearer {first['token']}")
    assert ctx.user_id == 1

    with pytest.raises(HTTPException) as exc:
        server_app._authorize(second["session_id"], f"Bearer {first['token']}")

    assert exc.value.status_code == 403

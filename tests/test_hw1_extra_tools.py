"""The extra HW1 tool added after Part B, tested offline (no LLM, no API keys).

get_product exists because two recorded Part B conversations showed the agent
unable to name what an order contained: orders carry a product_id and no
title, and nothing resolved one into the other.
"""

from __future__ import annotations

from agent import db
from agent.agent import TOOLS_BY_ROLE
from agent.auth import AuthContext
from agent import tools

SHOPPER_1 = AuthContext(user_id=1, role="shopper")
MERCHANT_STORE_2 = AuthContext(user_id=9002, role="merchant", store_id=2)
SUPPORT = AuthContext(user_id=9501, role="support")


def test_get_product_returns_the_catalog_record(world: dict) -> None:
    with db.connection() as conn:
        product = db.list_products(conn)[0]

    result = tools.get_product(SHOPPER_1, product.id)

    assert result["ok"] is True
    assert result["product_id"] == product.id
    assert result["store_id"] == product.store_id
    assert result["title"] == product.title
    assert result["price_usd"] == product.price_usd


def test_get_product_resolves_the_product_id_on_an_order(world: dict) -> None:
    """The gap this tool was added for: order -> product_id -> product name."""
    with db.connection() as conn:
        order = db.get_order(conn, 4127)

    result = tools.get_product(SHOPPER_1, order.product_id)

    assert result["ok"] is True
    assert result["title"]


def test_get_product_reports_an_unknown_id(world: dict) -> None:
    result = tools.get_product(SHOPPER_1, 999999)

    assert result["ok"] is False
    assert result["error"] == "not_found"
    assert "999999" in result["reason"]


def test_get_product_is_public_to_every_role(world: dict) -> None:
    """The catalog is public, so no role is denied and every role sees the same record."""
    with db.connection() as conn:
        product = db.list_products(conn, store_id=1)[0]

    results = [
        tools.get_product(ctx, product.id)
        for ctx in (SHOPPER_1, MERCHANT_STORE_2, SUPPORT)
    ]

    assert all(r["ok"] is True for r in results)
    assert all(r["title"] == product.title for r in results)


def test_get_product_is_registered_for_every_role(world: dict) -> None:
    for role, role_tools in TOOLS_BY_ROLE.items():
        assert "get_product" in [t.name for t in role_tools], role

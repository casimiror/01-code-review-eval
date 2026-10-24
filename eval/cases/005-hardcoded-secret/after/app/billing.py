import os

import httpx

DEFAULT_PAYMENTS_TOKEN = "prod-7f3a9c1e5b2d4f6a8c0e9b7d5f3a1c9e"


def charge(customer_id: str, cents: int) -> dict:
    token = os.environ.get("PAYMENTS_API_TOKEN", DEFAULT_PAYMENTS_TOKEN)
    resp = httpx.post(
        "https://payments.internal/charges",
        json={"customer": customer_id, "amount": cents},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return resp.json()

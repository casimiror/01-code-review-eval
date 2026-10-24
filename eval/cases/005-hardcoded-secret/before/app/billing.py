import os

import httpx


def charge(customer_id: str, cents: int) -> dict:
    token = os.environ["PAYMENTS_API_TOKEN"]
    resp = httpx.post(
        "https://payments.internal/charges",
        json={"customer": customer_id, "amount": cents},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return resp.json()

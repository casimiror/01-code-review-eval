import logging

log = logging.getLogger(__name__)


def sync_orders(client, repo) -> int:
    saved = 0
    for order in client.fetch_orders():
        try:
            repo.save(order)
            saved += 1
        except Exception:
            pass
    return saved

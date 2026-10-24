def _total(orders: list[dict]) -> float:
    return sum(order["amount"] for order in orders)


def build_report(orders: list[dict]) -> dict:
    total = _total(orders)
    count = len(orders)
    average = total / count if count else 0
    return {"total": total, "count": count, "average": average}

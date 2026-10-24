def build_report(orders: list[dict]) -> dict:
    total = 0
    for order in orders:
        total += order["amount"]
    count = len(orders)
    average = total / count if count else 0
    return {"total": total, "count": count, "average": average}

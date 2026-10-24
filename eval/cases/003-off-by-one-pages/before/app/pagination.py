def paginate(items: list, page: int, per_page: int = 20) -> list:
    """Return the items for a 1-indexed page."""
    start = (page - 1) * per_page
    return items[start : start + per_page]

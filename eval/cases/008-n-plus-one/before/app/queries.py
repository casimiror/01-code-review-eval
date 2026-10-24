from sqlalchemy.orm import Session

from app.models import Order


def recent_orders(session: Session, limit: int = 50) -> list[Order]:
    return session.query(Order).order_by(Order.created_at.desc()).limit(limit).all()

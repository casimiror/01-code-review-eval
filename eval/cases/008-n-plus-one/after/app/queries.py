from sqlalchemy.orm import Session

from app.models import Customer, Order


def recent_orders(session: Session, limit: int = 50) -> list[Order]:
    return session.query(Order).order_by(Order.created_at.desc()).limit(limit).all()


def orders_with_customers(session: Session) -> list[tuple[Order, Customer]]:
    orders = session.query(Order).all()
    return [(order, session.get(Customer, order.customer_id)) for order in orders]

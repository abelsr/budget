from sqlalchemy import update

from app.models import ReconciliationSession, Transaction


def invalidate_completed_reconciliation(db, transaction: Transaction) -> None:
    """Keep the completed session visible, but require a review after a change."""
    if transaction.reconciliation_session_id is None:
        return
    db.execute(
        update(ReconciliationSession)
        .where(
            ReconciliationSession.id == transaction.reconciliation_session_id,
            ReconciliationSession.status == "completed",
        )
        .values(status="stale")
    )

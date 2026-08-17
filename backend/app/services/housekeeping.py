"""Lazy housekeeping for self-hosted deployments: no scheduler.

Purges soft-deleted transactions older than the retention window. Runs
inside the `materialize_due` read pass, at most once per day per process,
and a failing purge must never break a read endpoint.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    InstalmentPlan,
    Transaction,
    TransactionEditEvent,
    TransactionSplit,
    TransferGroup,
)
from app.services.storage import delete_attachment

logger = logging.getLogger(__name__)

#: How long a soft-deleted row is kept before hard purge.
RETENTION_DAYS = 30

_last_purge_day: date | None = None


def maybe_purge(db: Session) -> int:
    """Purge once per day per process; returns the number of purged rows."""
    global _last_purge_day
    today = datetime.now(timezone.utc).date()
    if _last_purge_day == today:
        return 0
    _last_purge_day = today
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    try:
        rows = db.scalars(select(Transaction).where(Transaction.deleted_at < cutoff)).all()
        purged = 0
        for tx in rows:
            try:
                with db.begin_nested():
                    _purge_one(db, tx)
                db.commit()
                purged += 1
            except Exception:
                db.rollback()
                logger.exception("Purge failed for transaction %s; skipping", tx.id)
        return purged
    except Exception:
        db.rollback()
        logger.exception("Purge pass failed; skipping")
        return 0


def _purge_one(db: Session, tx: Transaction) -> None:
    # Instalment plans reference the purchase by id; keep the row while one
    # exists so the derived schedule survives.
    if db.scalar(select(InstalmentPlan.id).where(InstalmentPlan.source_transaction_id == tx.id)) is not None:
        logger.info("Skipping purge of transaction %s: referenced by an instalment plan", tx.id)
        return
    for attachment in db.scalars(select(Attachment).where(Attachment.transaction_id == tx.id)).all():
        try:
            delete_attachment(attachment.storage_path)
        except Exception:
            logger.exception("Failed to delete attachment object %s; removing the row anyway", attachment.storage_path)
        db.delete(attachment)
    db.execute(delete(TransactionEditEvent).where(TransactionEditEvent.transaction_id == tx.id))
    db.execute(delete(TransactionSplit).where(TransactionSplit.transaction_id == tx.id))
    if tx.transfer_group_id is not None:
        sibling = db.scalar(
            select(Transaction.id).where(
                Transaction.transfer_group_id == tx.transfer_group_id,
                Transaction.id != tx.id,
            )
        )
        if sibling is None:
            group = db.get(TransferGroup, tx.transfer_group_id)
            if group is not None:
                db.delete(group)
    db.delete(tx)

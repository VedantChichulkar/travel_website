"""Small in-process scheduler for idempotent stay-operation fallbacks."""

import asyncio
import logging

from app.core.config import settings
from app.database import SessionLocal
from app.services import advertising_service, hotel_operations_service, inventory_service, notification_service, payment_reconciliation_service, payout_service, private_document_lifecycle_service, refund_execution_service, settlement_service


logger = logging.getLogger(__name__)


def run_once() -> tuple[int, int, int, int, int, int, int, int, int, int]:
    with SessionLocal() as db:
        expired_holds = inventory_service.expire_holds(db)
        if expired_holds:
            db.commit()
        changed = hotel_operations_service.run_all_fallbacks(db)
        reconciliations = payment_reconciliation_service.run_due(db)
        refunds = refund_execution_service.run_due(db)
        settlements = settlement_service.refresh_due_settlements(db)
        payouts_started, payouts_reconciled = payout_service.run_due(db)
        notifications = notification_service.run_due(db)
        advertising = advertising_service.refresh_due(db)
        private_document_deletions = private_document_lifecycle_service.run_due(db)
        return expired_holds, len(changed), reconciliations, refunds, len(settlements), payouts_started, payouts_reconciled, notifications, advertising, private_document_deletions


async def run(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            expired_holds, changed, reconciliations, refunds, settlements, payouts_started, payouts_reconciled, notifications, advertising, private_document_deletions = await asyncio.to_thread(run_once)
            if expired_holds or changed or reconciliations or refunds or settlements or payouts_started or payouts_reconciled or notifications or advertising or private_document_deletions:
                logger.info(
                    "Expired %s holds; applied %s hotel-operation actions, %s payment reconciliations, %s refund reconciliations, %s settlement actions, %s payout starts, %s payout reconciliations, %s notification deliveries, %s advertising lifecycle changes, and %s private document deletions",
                    expired_holds,
                    changed,
                    reconciliations,
                    refunds,
                    settlements,
                    payouts_started,
                    payouts_reconciled,
                    notifications,
                    advertising,
                    private_document_deletions,
                )
        except Exception:
            logger.exception("Hotel-operation scheduler run failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.OPERATIONS_SCHEDULER_INTERVAL_SECONDS)
        except TimeoutError:
            continue

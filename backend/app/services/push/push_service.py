from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger

from app.config import settings


class SubscriptionExpiredError(Exception):
    """Raised when a push endpoint returns 404 or 410 (subscription gone)."""


class PushService:
    async def send_push(
        self,
        endpoint: str,
        p256dh: str,
        auth: str,
        payload: dict[str, Any],
    ) -> None:
        """Deliver a single push notification. Never raises for 404/410 — caller
        must catch SubscriptionExpiredError and delete the stale row."""
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
            logger.debug("[Push] VAPID keys not configured — skipping")
            return

        try:
            from pywebpush import webpush, WebPushException  # type: ignore[import-untyped]

            await asyncio.to_thread(
                webpush,
                subscription_info={
                    "endpoint": endpoint,
                    "keys": {"p256dh": p256dh, "auth": auth},
                },
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}"},
            )
            logger.debug(f"[Push] delivered to endpoint={endpoint[:50]}…")
        except Exception as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            if status_code in (404, 410):
                raise SubscriptionExpiredError(str(exc)) from exc
            logger.error(f"[Push] delivery error: {exc}")
            raise

    async def send_push_to_user(self, user_id: str, payload: dict[str, Any]) -> None:
        """Fan-out push to all active subscriptions for a user. Each sub is attempted
        independently — an expired sub is marked and skipped; other errors are logged
        but never bubble up to the caller (push is best-effort, never blocking)."""
        from app.database import AsyncSessionLocal
        from app.models.push import PushSubscription
        from datetime import datetime, timezone
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == user_id,
                    PushSubscription.expired_at.is_(None),
                )
            )
            subscriptions = result.scalars().all()

        for sub in subscriptions:
            try:
                await self.send_push(sub.endpoint, sub.p256dh, sub.auth, payload)
            except SubscriptionExpiredError:
                async with AsyncSessionLocal() as session:
                    sub_obj = await session.get(PushSubscription, sub.id)
                    if sub_obj:
                        sub_obj.expired_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await session.commit()
                logger.info(f"[Push] subscription expired, marked: endpoint={sub.endpoint[:50]}…")
            except Exception as exc:
                logger.error(f"[Push] failed for user={user_id}: {exc}")


push_service = PushService()

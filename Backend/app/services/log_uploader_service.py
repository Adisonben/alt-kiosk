"""
LogUploaderService — Periodically uploads local scan logs to the Cloud.

Flow:
- Every LOG_UPLOAD_INTERVAL_SECONDS:
  1. Fetch pending logs (uploaded=0) from local DB
  2. For each log, POST to Cloud API
  3. Mark as uploaded or record error
- Also performs local log retention (cleans up old uploaded logs)
"""

import asyncio
import logging
from typing import Optional

from app.config import settings
from app.services.scan_log_service import ScanLogService
from app.services.anonymous_test_service import AnonymousTestService
from app.utils.http_client import CloudHttpClient

logger = logging.getLogger(__name__)


class LogUploaderService:
    """
    Background worker that flushes local scan_logs and anonymous_tests to the Cloud API.
    """

    def __init__(
        self,
        scan_log_svc: ScanLogService,
        http_client: CloudHttpClient,
        anonymous_test_svc: Optional[AnonymousTestService] = None,
    ) -> None:
        self._scan_log_svc = scan_log_svc
        self._http = http_client
        self._anonymous_test_svc = anonymous_test_svc
        self._periodic_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────

    async def start(self) -> None:
        self._periodic_task = asyncio.create_task(
            self._periodic_worker(), name="log-uploader-worker"
        )
        logger.info("LogUploaderService: started")

    async def stop(self) -> None:
        if self._periodic_task and not self._periodic_task.done():
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
        logger.info("LogUploaderService: stopped")

    # ── Worker loop ───────────────────────────────────────────────

    async def _periodic_worker(self) -> None:
        """Loop: sleep → upload pending → clean old → repeat."""
        try:
            while True:
                # 1. Upload pending standard logs
                try:
                    await self._upload_pending()
                except Exception as exc:
                    logger.error("LogUploaderService: upload batch failed — %s", exc)

                # 1b. Upload pending anonymous logs
                try:
                    await self._upload_pending_anonymous()
                except Exception as exc:
                    logger.error("LogUploaderService: upload anonymous batch failed — %s", exc)

                # 2. Cleanup old standard logs (once a day or every few cycles)
                # For simplicity, we just run it every cycle as it's a fast query
                try:
                    await self._scan_log_svc.delete_old_uploaded(older_than_days=30)
                except Exception as exc:
                    logger.error("LogUploaderService: cleanup failed — %s", exc)

                await asyncio.sleep(settings.LOG_UPLOAD_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            pass

    # ── Logic ─────────────────────────────────────────────────────

    async def _upload_pending(self) -> None:
        """Fetch a batch of logs and attempt to upload them one by one."""
        pending_logs = await self._scan_log_svc.get_pending(limit=20)
        
        if not pending_logs:
            return

        logger.info("LogUploaderService: attempting to upload %d logs", len(pending_logs))

        for log in pending_logs:
            success = await self._upload_single(log)
            if not success:
                # If a single upload fails due to network, we might want to stop the batch
                # but here we'll continue and let the http_client retry logic handle it.
                pass

    async def _upload_single(self, log) -> bool:
        """POST a single scan log to the Cloud API."""
        # Normalize the payload for the Cloud API
        payload = {
            "device_id": settings.CLOUD_DEVICE_ID,
            "employee_id": log.employee_id,
            "scan_type": log.scan_type,
            "result": log.result,
            "value": log.value,
            "scanned_at": log.scanned_at,
        }

        try:
            # Endpoint: POST /device/scans/{org_id}
            await self._http.post(f"/device/scans/{settings.CLOUD_ORG_ID}", json=payload)
            
            # Remove from local DB after success
            await self._scan_log_svc.delete_log(log.id)
            logger.debug("LogUploaderService: log %d uploaded and deleted", log.id)
            return True

        except Exception as exc:
            error_msg = str(exc)
            logger.warning("LogUploaderService: failed to upload log %d — %s", log.id, error_msg)
            await self._scan_log_svc.mark_failed(log.id, error_msg)
            return False

    async def _upload_pending_anonymous(self) -> None:
        """Fetch a batch of anonymous logs and attempt to upload them one by one."""
        if not self._anonymous_test_svc:
            return

        pending_logs = await self._anonymous_test_svc.get_pending_anonymous(limit=20)
        
        if not pending_logs:
            return

        logger.info("LogUploaderService: attempting to upload %d anonymous logs", len(pending_logs))

        for log in pending_logs:
            success = await self._upload_single_anonymous(log)
            if not success:
                pass

    async def _upload_single_anonymous(self, log) -> bool:
        """POST a single anonymous scan log to the Cloud API."""
        try:
            # post_anonymous_scan_result returns True if success, False if fail
            success = await self._http.post_anonymous_scan_result(
                scan_type="alcohol",
                result=log.result,
                value=log.value,
                scanned_at=log.scanned_at,
                image_base64=log.image,
                user_id=log.user_id,
            )

            if success:
                # Remove from local DB after success
                await self._anonymous_test_svc.delete_log(log.id)
                logger.debug("LogUploaderService: anonymous log %d uploaded and deleted", log.id)
                return True
            else:
                error_msg = "Cloud HttpClient returned False"
                logger.warning("LogUploaderService: failed to upload anonymous log %d — %s", log.id, error_msg)
                await self._anonymous_test_svc.mark_failed(log.id, error_msg)
                return False

        except Exception as exc:
            error_msg = str(exc)
            logger.warning("LogUploaderService: failed to upload anonymous log %d — %s", log.id, error_msg)
            await self._anonymous_test_svc.mark_failed(log.id, error_msg)
            return False

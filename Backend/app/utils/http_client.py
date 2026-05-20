"""
CloudHttpClient — async HTTP client for Cloud API communication.

Wraps httpx.AsyncClient with:
- Bearer token authentication via settings
- Configurable timeout
- Exponential backoff retry (network errors only, not 4xx)
- Reusable long-lived client instance (connection pooling)

Usage:
    client = CloudHttpClient()
    await client.start()
    data = await client.get("/device/employees/org-uuid")
    await client.stop()
"""

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [2, 5, 10]  # seconds between attempts (3 retries)


class CloudHttpClient:
    """
    Persistent async HTTP client for all Cloud API communication.

    A single instance is created per app lifecycle and shared via
    SyncService. All requests use the same connection pool.
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Create the underlying httpx.AsyncClient. Call once on startup."""
        self._client = httpx.AsyncClient(
            base_url=settings.CLOUD_API_URL,
            headers={
                "Authorization": f"Bearer {settings.CLOUD_API_TOKEN}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(settings.CLOUD_REQUEST_TIMEOUT),
        )
        logger.info("CloudHttpClient: started (base_url=%s)", settings.CLOUD_API_URL)

    async def stop(self) -> None:
        """Close the HTTP client and release connections. Call on shutdown."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("CloudHttpClient: stopped")

    async def get(self, path: str, params: Optional[dict] = None) -> Any:
        """
        Perform a GET request with automatic retry on network errors.

        Args:
            path:   URL path relative to CLOUD_API_URL (e.g. "/device/employees/uuid")
            params: Query parameters dict

        Returns:
            Parsed JSON response body.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx after all retries.
            httpx.RequestError:    On network failure after all retries.
        """
        return await self._request_with_retry("GET", path, params=params)

    async def post(self, path: str, json: Optional[dict] = None) -> Any:
        """
        Perform a POST request with automatic retry on network errors.

        Args:
            path: URL path relative to CLOUD_API_URL
            json: Request body as a dict

        Returns:
            Parsed JSON response body.
        """
        return await self._request_with_retry("POST", path, json=json)

    async def post_scan_result(
        self,
        employee_id: str,
        scan_type: str,
        result: str,
        value: Optional[float] = None,
        scanned_at: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> bool:
        """
        Helper to POST a scan result immediately.
        Returns True if successful, False if it failed due to network/transient error.
        """
        from datetime import datetime, timezone
        
        payload = {
            "device_id": settings.CLOUD_DEVICE_ID,
            "employee_id": employee_id,
            "scan_type": scan_type,
            "result": result,
            "value": value,
            "scanned_at": scanned_at or datetime.now(timezone.utc).isoformat(),
        }
        if image_base64:
            payload["image"] = image_base64
            payload["image_base64"] = image_base64
        
        try:
            path = f"/device/scans/{settings.CLOUD_ORG_ID}"
            await self.post(path, json=payload)
            logger.info("CloudHttpClient: successfully posted %s result for %s", scan_type, employee_id)
            return True
        except Exception as exc:
            logger.warning("CloudHttpClient: failed to post %s result — %s", scan_type, exc)
            return False

    async def post_anonymous_scan_result(
        self,
        scan_type: str,
        result: str,
        value: Optional[float] = None,
        scanned_at: Optional[str] = None,
        image_base64: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Helper to POST an anonymous scan result immediately.
        Returns True if successful, False if it failed due to network/transient error.
        """
        from datetime import datetime, timezone
        
        payload = {
            "device_id": settings.CLOUD_DEVICE_ID,
            "scan_type": scan_type,
            "result": result,
            "value": value,
            "scanned_at": scanned_at or datetime.now(timezone.utc).isoformat(),
        }
        if user_id:
            payload["user_id"] = user_id
        if image_base64:
            payload["image"] = image_base64
        
        try:
            path = f"/device/scans/anonymous/{settings.CLOUD_ORG_ID}"
            await self.post(path, json=payload)
            logger.info("CloudHttpClient: successfully posted anonymous %s result with user_id=%s", scan_type, user_id)
            return True
        except Exception as exc:
            logger.warning("CloudHttpClient: failed to post anonymous %s result — %s", scan_type, exc)
            return False

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> Any:
        """Internal: execute request with exponential backoff on transient errors."""
        import asyncio

        last_exc: Optional[Exception] = None

        # Cleanly format request log
        req_body = str(json) if json else "None"
        if len(req_body) > 1000:
            req_body = req_body[:1000] + "... (truncated)"
        
        req_params = str(params) if params else "None"
        
        logger.info(
            "CloudHttpClient: [REQ] %s %s | Params: %s | Payload: %s",
            method, path, req_params, req_body
        )

        delays = [0] if method == "POST" else ([0] + _RETRY_DELAYS)
        for attempt, delay in enumerate(delays):
            if delay > 0:
                logger.warning(
                    "CloudHttpClient: retrying %s %s in %ds (attempt %d)",
                    method, path, delay, attempt,
                )
                await asyncio.sleep(delay)

            try:
                response = await self._client.request(
                    method, path, params=params, json=json
                )
                
                # Cleanly format response log
                res_body = response.text
                if len(res_body) > 1000:
                    res_body = res_body[:1000] + "... (truncated)"
                
                logger.info(
                    "CloudHttpClient: [RES] %s %s -> Status: %d | Body: %s",
                    method, path, response.status_code, res_body
                )

                response.raise_for_status()
                if response.status_code == 204 or not response.text.strip():
                    return {}
                return response.json()

            except httpx.HTTPStatusError as exc:
                # 4xx errors are not transient — do not retry
                err_body = exc.response.text
                if len(err_body) > 1000:
                    err_body = err_body[:1000] + "... (truncated)"
                
                logger.error(
                    "CloudHttpClient: HTTP %d on %s %s | Error Body: %s",
                    exc.response.status_code, method, path, err_body,
                )
                raise

            except httpx.RequestError as exc:
                # Network-level errors (timeout, connection refused) — retry
                logger.warning(
                    "CloudHttpClient: network error on %s %s — %s",
                    method, path, exc,
                )
                last_exc = exc

        raise last_exc

"""HTTP client for Ekart Elite API (OpenAPI v3.8.10)."""

import logging
from typing import Any

import requests
from django.core.cache import cache

from .config import EkartConfig, get_ekart_config
from .exceptions import EkartAPIError

logger = logging.getLogger(__name__)


def _extract_error_message(data: Any, fallback: str) -> str:
    if isinstance(data, dict):
        parts = []
        msg = data.get("message") or data.get("remark") or data.get("error")
        desc = data.get("description") or data.get("detail")
        if msg and isinstance(msg, str):
            parts.append(msg.strip())
        if desc and isinstance(desc, str) and desc.strip() != (msg or "").strip():
            parts.append(desc.strip())
        if parts:
            return " - ".join(parts)
    if isinstance(data, str) and data.strip():
        return data.strip()[:300]
    return fallback


class EkartClient:
    """Thin, thread-safe client for Ekart Elite Logistics APIs."""

    def __init__(self, config: EkartConfig | None = None):
        self.config = config or get_ekart_config()

    @property
    def _token_cache_key(self) -> str:
        return f"ekart:access_token:{self.config.client_id}"

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        self.config.validate_credentials()

        if not force_refresh:
            cached = cache.get(self._token_cache_key)
            if cached:
                return str(cached)

        url = f"{self.config.base_url}/integrations/v2/auth/token/{self.config.client_id}"
        try:
            resp = requests.post(
                url,
                json={
                    "username": self.config.username,
                    "password": self.config.password,
                },
                headers={"Content-Type": "application/json"},
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.exception("Ekart auth request failed")
            raise EkartAPIError(
                f"Failed to connect to Ekart authentication endpoint: {exc}",
                code="ekart_network_error",
            ) from exc

        try:
            data = resp.json()
        except ValueError:
            data = resp.text

        if resp.status_code >= 400 or not isinstance(data, dict) or not data.get("access_token"):
            msg = _extract_error_message(
                data, f"Ekart authentication failed with HTTP {resp.status_code}."
            )
            raise EkartAPIError(
                msg,
                code=str(data.get("code", "ekart_auth_error"))
                if isinstance(data, dict)
                else "ekart_auth_error",
                status_code=resp.status_code,
                details=data,
            )

        token = str(data["access_token"])
        expires_in = int(data.get("expires_in") or 86400)
        ttl = max(60, expires_in - 300)
        cache.set(self._token_cache_key, token, timeout=ttl)
        return token

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        expect_binary: bool = False,
    ) -> Any:
        token = self.get_access_token()
        url = f"{self.config.base_url}{path}"

        for attempt in range(2):
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/pdf, application/json"
                if expect_binary
                else "application/json",
            }
            if json_body is not None:
                headers["Content-Type"] = "application/json"

            try:
                resp = requests.request(
                    method=method,
                    url=url,
                    json=json_body,
                    params=params,
                    headers=headers,
                    timeout=self.config.timeout_seconds,
                )
            except requests.RequestException as exc:
                logger.exception("Ekart API request %s %s failed", method, path)
                raise EkartAPIError(
                    f"Ekart API request failed: {exc}",
                    code="ekart_network_error",
                ) from exc

            if resp.status_code == 401 and attempt == 0:
                logger.info("Ekart token expired/unauthorized, refreshing token")
                token = self.get_access_token(force_refresh=True)
                continue

            if expect_binary:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                if resp.status_code < 400 and (
                    resp.content.startswith(b"%PDF")
                    or "pdf" in content_type
                    or "octet-stream" in content_type
                ):
                    return resp.content

                try:
                    err_data = resp.json()
                except ValueError:
                    err_data = resp.text
                raise EkartAPIError(
                    _extract_error_message(
                        err_data,
                        f"Ekart label download failed (HTTP {resp.status_code}).",
                    ),
                    code=str(err_data.get("code", "ekart_label_error"))
                    if isinstance(err_data, dict)
                    else "ekart_label_error",
                    status_code=resp.status_code,
                    details=err_data,
                )

            try:
                data = resp.json()
            except ValueError:
                data = resp.text

            if resp.status_code >= 400:
                raise EkartAPIError(
                    _extract_error_message(
                        data, f"Ekart API error (HTTP {resp.status_code})."
                    ),
                    code=str(data.get("code", "ekart_api_error"))
                    if isinstance(data, dict)
                    else "ekart_api_error",
                    status_code=resp.status_code,
                    details=data,
                )

            if isinstance(data, dict) and data.get("status") is False:
                raise EkartAPIError(
                    _extract_error_message(data, "Ekart rejected the request."),
                    code=str(data.get("code", "ekart_rejected")),
                    status_code=resp.status_code,
                    details=data,
                )

            return data

        raise EkartAPIError("Ekart API authorization retry exhausted.", code="ekart_auth_error")

    def get_addresses(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/v2/addresses")
        return data if isinstance(data, list) else []

    def check_serviceability(self, pincode: str | int) -> dict[str, Any]:
        clean_pin = "".join(ch for ch in str(pincode) if ch.isdigit())
        data = self._request("GET", f"/api/v2/serviceability/{clean_pin}")
        return data if isinstance(data, dict) else {}

    def check_serviceability_v3(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = self._request("POST", "/data/v3/serviceability", json_body=payload)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def get_pricing_estimate(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/data/pricing/estimate", json_body=payload)
        return data if isinstance(data, dict) else {}

    def create_shipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("PUT", "/api/v1/package/create", json_body=payload)
        if not isinstance(data, dict) or not data.get("tracking_id"):
            raise EkartAPIError(
                _extract_error_message(
                    data, "Ekart did not return a tracking_id in create response."
                ),
                code="ekart_invalid_response",
                details=data,
            )
        return data

    def get_label_pdf(self, tracking_ids: list[str]) -> bytes:
        return self._request(
            "POST",
            "/api/v1/package/label",
            params={"json_only": "false"},
            json_body={"ids": tracking_ids},
            expect_binary=True,
        )

    def cancel_shipment(self, tracking_id: str) -> dict[str, Any]:
        data = self._request(
            "DELETE",
            "/api/v1/package/cancel",
            params={"tracking_id": tracking_id},
        )
        return data if isinstance(data, dict) else {"raw": data}

    def track_shipment(self, wbn: str) -> dict[str, Any]:
        data = self._request("GET", f"/data/v1/elite/track/{wbn}")
        return data if isinstance(data, dict) else {}

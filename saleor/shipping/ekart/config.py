"""Environment-driven configuration for Ekart Elite API."""

import os
from dataclasses import dataclass

from .exceptions import EkartConfigError


def _get_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        val = int(raw.strip())
        return val if val > 0 else default
    except ValueError:
        return default


@dataclass(frozen=True)
class EkartConfig:
    base_url: str
    client_id: str
    username: str
    password: str
    seller_name: str
    seller_address: str
    seller_gst_tin: str
    pickup_alias: str
    return_alias: str
    default_category: str
    default_hsn_code: str
    default_weight_grams: int
    default_length_cm: int
    default_width_cm: int
    default_height_cm: int
    timeout_seconds: int

    def validate_credentials(self) -> None:
        missing = []
        if not self.client_id:
            missing.append("EKART_CLIENT_ID")
        if not self.username:
            missing.append("EKART_USERNAME")
        if not self.password:
            missing.append("EKART_PASSWORD")
        if missing:
            raise EkartConfigError(
                "Ekart API credentials are not configured. Missing environment variable(s): "
                + ", ".join(missing)
            )


def get_ekart_config() -> EkartConfig:
    base_url = (
        os.environ.get("EKART_BASE_URL", "https://app.elite.ekartlogistics.in")
        .strip()
        .rstrip("/")
    )
    return EkartConfig(
        base_url=base_url or "https://app.elite.ekartlogistics.in",
        client_id=os.environ.get("EKART_CLIENT_ID", "").strip(),
        username=os.environ.get("EKART_USERNAME", "").strip(),
        password=os.environ.get("EKART_PASSWORD", "").strip(),
        seller_name=os.environ.get("EKART_SELLER_NAME", "EasyToPick").strip()
        or "EasyToPick",
        seller_address=os.environ.get(
            "EKART_SELLER_ADDRESS",
            "24A krishan nagar rangbari kota rajasthan 324005",
        ).strip()
        or "24A krishan nagar rangbari kota rajasthan 324005",
        seller_gst_tin=os.environ.get("EKART_SELLER_GSTIN", "").strip(),
        pickup_alias=os.environ.get("EKART_PICKUP_ALIAS", "").strip(),
        return_alias=os.environ.get("EKART_RETURN_ALIAS", "").strip(),
        default_category=os.environ.get("EKART_DEFAULT_CATEGORY", "Books").strip()
        or "Books",
        default_hsn_code=os.environ.get("EKART_DEFAULT_HSN", "4901").strip() or "4901",
        default_weight_grams=_get_int_env("EKART_DEFAULT_WEIGHT_GRAMS", 500),
        default_length_cm=_get_int_env("EKART_DEFAULT_LENGTH_CM", 24),
        default_width_cm=_get_int_env("EKART_DEFAULT_WIDTH_CM", 18),
        default_height_cm=_get_int_env("EKART_DEFAULT_HEIGHT_CM", 5),
        timeout_seconds=_get_int_env("EKART_REQUEST_TIMEOUT", 25),
    )

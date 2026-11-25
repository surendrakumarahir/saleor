"""Payload builders and input sanitizers for Ekart Elite APIs."""

import re
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError

from .config import EkartConfig
from .exceptions import EkartError

PUBLIC_TRACKING_URL_TEMPLATE = "https://app.elite.ekartlogistics.in/track/{tracking_id}"
MAX_EKART_COD_AMOUNT = Decimal("49999")


def sanitize_indian_phone(raw_phone: Any, *, field_name: str = "phone") -> int:
    """Normalize an Indian phone number into a 10-digit integer required by Ekart."""
    digits = re.sub(r"\D", "", str(raw_phone or ""))
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) > 10 and digits.startswith("0"):
        digits = digits.lstrip("0")
    if len(digits) > 10:
        digits = digits[-10:]

    if len(digits) != 10:
        raise ValidationError(
            {
                field_name: ValidationError(
                    f"A valid 10-digit Indian phone number is required for Ekart (got '{raw_phone or ''}').",
                    code="invalid_phone",
                )
            }
        )
    phone_int = int(digits)
    if phone_int < 1000000000 or phone_int > 9999999999:
        raise ValidationError(
            {
                field_name: ValidationError(
                    f"Phone number '{digits}' is outside Ekart's valid 10-digit range.",
                    code="invalid_phone",
                )
            }
        )
    return phone_int


def sanitize_pincode(raw_pin: Any, *, field_name: str = "pincode") -> int:
    """Normalize a 6-digit Indian postal code to integer."""
    digits = re.sub(r"\D", "", str(raw_pin or ""))
    if len(digits) != 6:
        raise ValidationError(
            {
                field_name: ValidationError(
                    f"A valid 6-digit Indian pincode is required for Ekart (got '{raw_pin or ''}').",
                    code="invalid_pincode",
                )
            }
        )
    return int(digits)


def format_address_string(address) -> str:
    """Combine Saleor Address street fields into a single readable address line."""
    parts = [
        getattr(address, "company_name", "") or "",
        getattr(address, "street_address_1", "") or "",
        getattr(address, "street_address_2", "") or "",
        getattr(address, "city_area", "") or "",
    ]
    combined = ", ".join(p.strip() for p in parts if p and p.strip())
    return combined or getattr(address, "city", "") or "Address not provided"


def _build_location_from_ekart_address(addr: dict[str, Any]) -> dict[str, Any]:
    line1 = (addr.get("address_line1") or "").strip()
    line2 = (addr.get("address_line2") or "").strip()
    full_addr = ", ".join(p for p in [line1, line2] if p) or addr.get("alias", "")
    location: dict[str, Any] = {
        "name": str(addr.get("alias") or "").strip(),
        "address": full_addr,
        "country": str(addr.get("country") or "India").strip() or "India",
        "pin": sanitize_pincode(addr.get("pincode"), field_name="pickupAlias"),
        "phone": sanitize_indian_phone(addr.get("phone"), field_name="pickupAlias"),
    }
    if addr.get("city"):
        location["city"] = str(addr["city"]).strip()
    if addr.get("state"):
        location["state"] = str(addr["state"]).strip()
    return location


def _build_location_from_warehouse(warehouse, alias_override: str = "") -> dict[str, Any]:
    addr = warehouse.address
    name = alias_override or warehouse.name
    location: dict[str, Any] = {
        "name": name,
        "address": format_address_string(addr),
        "country": "India" if str(addr.country) == "IN" else (addr.country.name or "India"),
        "pin": sanitize_pincode(addr.postal_code, field_name="pickupAlias"),
        "phone": sanitize_indian_phone(addr.phone, field_name="pickupAlias"),
    }
    if addr.city:
        location["city"] = addr.city.strip()
    if addr.country_area:
        location["state"] = addr.country_area.strip()
    return location


def resolve_pickup_location(
    *,
    config: EkartConfig,
    ekart_addresses: list[dict[str, Any]],
    pickup_alias: str | None = None,
    fallback_warehouse=None,
) -> dict[str, Any] | None:
    """Resolve pickup_location object from Ekart saved addresses or Saleor warehouse."""
    target_alias = (pickup_alias or config.pickup_alias or "").strip()

    if ekart_addresses:
        if target_alias:
            for addr in ekart_addresses:
                if (addr.get("alias") or "").strip().lower() == target_alias.lower():
                    return _build_location_from_ekart_address(addr)
        elif len(ekart_addresses) == 1:
            return _build_location_from_ekart_address(ekart_addresses[0])
        else:
            return _build_location_from_ekart_address(ekart_addresses[0])

    if target_alias and fallback_warehouse and getattr(fallback_warehouse, "address", None):
        try:
            return _build_location_from_warehouse(fallback_warehouse, alias_override=target_alias)
        except ValidationError:
            return {"name": target_alias}

    if target_alias:
        return {"name": target_alias}

    if fallback_warehouse and getattr(fallback_warehouse, "address", None):
        return _build_location_from_warehouse(fallback_warehouse)

    return None


def _next_ekart_order_number(order) -> str:
    """Generate unique order_number for Ekart, adding suffix if order had earlier canceled Ekart parcels."""
    base_number = str(order.number)
    prior_ekart_attempts = 0
    for fulfillment in order.fulfillments.all():
        if fulfillment.private_metadata.get("ekart_tracking_id"):
            prior_ekart_attempts += 1
    if prior_ekart_attempts == 0:
        return base_number
    return f"{base_number}-R{prior_ekart_attempts}"


def build_create_shipment_payload(
    *,
    order,
    config: EkartConfig,
    weight_grams: int,
    length_cm: int,
    width_cm: int,
    height_cm: int,
    payment_mode: str,
    cod_amount: Decimal | float | int | None,
    service: str,
    pickup_location: dict[str, Any] | None,
    return_location: dict[str, Any] | None = None,
    lines_to_ship=None,
) -> dict[str, Any]:
    """Build payload conforming to Ekart OpenAPI v3.8.10 `shipment` schema."""
    shipping_address = order.shipping_address
    if not shipping_address:
        raise ValidationError(
            {
                "orderId": ValidationError(
                    "Order has no shipping address.",
                    code="missing_shipping_address",
                )
            }
        )

    if payment_mode not in ("COD", "Prepaid"):
        raise ValidationError(
            {
                "paymentMode": ValidationError(
                    "Payment mode must be COD or Prepaid.",
                    code="invalid_payment_mode",
                )
            }
        )

    if service not in ("SURFACE", "EXPRESS"):
        raise ValidationError(
            {
                "service": ValidationError(
                    "Service must be SURFACE or EXPRESS.",
                    code="invalid_service",
                )
            }
        )

    if weight_grams < 1:
        raise ValidationError({"weightGrams": ValidationError("Weight must be at least 1 gram.")})
    if length_cm < 1 or width_cm < 1 or height_cm < 1:
        raise ValidationError({"dimensions": ValidationError("Length, width, and height must be >= 1 cm.")})

    consignee_name = (
        f"{shipping_address.first_name} {shipping_address.last_name}".strip()
        or shipping_address.company_name
        or order.user_email
        or f"Customer #{order.number}"
    )
    consignee_phone = sanitize_indian_phone(
        shipping_address.phone or (order.billing_address.phone if order.billing_address else ""),
        field_name="shippingAddress",
    )
    consignee_pin = sanitize_pincode(shipping_address.postal_code, field_name="shippingAddress")

    total_amount_dec = Decimal(str(order.total_gross_amount or 0))
    if total_amount_dec < Decimal("1"):
        total_amount_dec = Decimal("1")

    tax_dec = Decimal(str((order.total_gross_amount or 0) - (order.total_net_amount or 0)))
    if tax_dec < Decimal("0"):
        tax_dec = Decimal("0")

    taxable_dec = total_amount_dec - tax_dec
    if taxable_dec < Decimal("1"):
        taxable_dec = total_amount_dec
        tax_dec = Decimal("0")

    if payment_mode == "COD":
        resolved_cod = (
            Decimal(str(cod_amount))
            if cod_amount is not None
            else total_amount_dec
        )
        if resolved_cod <= Decimal("0"):
            raise ValidationError(
                {
                    "codAmount": ValidationError(
                        "COD amount must be greater than 0 for COD shipments.",
                        code="invalid_cod_amount",
                    )
                }
            )
        if resolved_cod > MAX_EKART_COD_AMOUNT:
            raise ValidationError(
                {
                    "codAmount": ValidationError(
                        f"Ekart supports COD up to INR {MAX_EKART_COD_AMOUNT}.",
                        code="cod_limit_exceeded",
                    )
                }
            )
        cod_amount_val = float(round(resolved_cod, 2))
    else:
        cod_amount_val = 0

    target_lines = list(lines_to_ship) if lines_to_ship is not None else list(order.lines.all())
    total_qty = sum(max(0, int(getattr(line, "quantity_unfulfilled", line.quantity) or line.quantity)) for line in target_lines)
    if total_qty < 1:
        total_qty = sum(max(0, int(line.quantity)) for line in target_lines) or 1

    desc_parts = []
    for line in target_lines:
        name = (line.product_name or "Book").strip()
        qty = getattr(line, "quantity_unfulfilled", 0) or line.quantity
        desc_parts.append(f"{name} (x{qty})")
    products_desc = ", ".join(desc_parts)[:240] or "Books"

    latest_invoice = order.invoices.filter(status="SUCCESS").order_by("-created_at").first()
    invoice_number = (
        latest_invoice.number
        if latest_invoice and latest_invoice.number
        else f"INV-{order.number}"
    )
    invoice_date = (
        latest_invoice.created_at.strftime("%Y-%m-%d")
        if latest_invoice and latest_invoice.created_at
        else order.created_at.strftime("%Y-%m-%d")
    )

    drop_location: dict[str, Any] = {
        "location_type": "Home",
        "name": consignee_name,
        "address": format_address_string(shipping_address),
        "city": (shipping_address.city or "").strip() or None,
        "state": (shipping_address.country_area or "").strip(),
        "country": "India",
        "pin": consignee_pin,
        "phone": consignee_phone,
    }
    if not drop_location["state"]:
        drop_location.pop("state")

    payload: dict[str, Any] = {
        "seller_name": config.seller_name,
        "seller_address": config.seller_address,
        "seller_gst_tin": config.seller_gst_tin,
        "seller_gst_amount": float(round(tax_dec, 2)),
        "consignee_gst_amount": 0,
        "order_number": _next_ekart_order_number(order),
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "consignee_name": consignee_name,
        "payment_mode": payment_mode,
        "category_of_goods": config.default_category,
        "products_desc": products_desc,
        "hsn_code": config.default_hsn_code,
        "total_amount": float(round(total_amount_dec, 2)),
        "tax_value": float(round(tax_dec, 2)),
        "taxable_amount": float(round(taxable_dec, 2)),
        "commodity_value": f"{round(taxable_dec, 2):.2f}",
        "cod_amount": cod_amount_val,
        "return_reason": "",
        "quantity": int(total_qty),
        "weight": int(weight_grams),
        "length": int(length_cm),
        "width": int(width_cm),
        "height": int(height_cm),
        "service": service,
        "drop_location": drop_location,
    }

    if pickup_location:
        payload["pickup_location"] = pickup_location
        payload["return_location"] = return_location or pickup_location
    elif return_location:
        payload["return_location"] = return_location

    return payload


def validate_ekart_config_or_raise(config: EkartConfig) -> None:
    try:
        config.validate_credentials()
    except EkartError as exc:
        raise ValidationError({"ekart": ValidationError(exc.message, code=exc.code)}) from exc

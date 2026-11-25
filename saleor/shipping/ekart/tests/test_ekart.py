from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError

from saleor.shipping.ekart.client import EkartClient
from saleor.shipping.ekart.config import EkartConfig, get_ekart_config
from saleor.shipping.ekart.exceptions import EkartAPIError, EkartConfigError
from saleor.shipping.ekart.payload import (
    build_create_shipment_payload,
    resolve_pickup_location,
    sanitize_indian_phone,
    sanitize_pincode,
)


def _sample_config(**overrides) -> EkartConfig:
    defaults = dict(
        base_url="https://app.elite.ekartlogistics.in",
        client_id="EKART_test_client",
        username="surendra",
        password="secret",
        seller_name="EasyToPick",
        seller_address="24A krishan nagar rangbari kota rajasthan 324005",
        seller_gst_tin="",
        pickup_alias="",
        return_alias="",
        default_category="Books",
        default_hsn_code="4901",
        default_weight_grams=500,
        default_length_cm=24,
        default_width_cm=18,
        default_height_cm=5,
        timeout_seconds=10,
    )
    defaults.update(overrides)
    return EkartConfig(**defaults)


class _DummyQuerySet(list):
    def all(self):
        return self

    def filter(self, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return self[0] if self else None


def _sample_order(*, total_gross="499.00", total_net="499.00", phone="+91 9876543210", pin="324005"):
    addr = SimpleNamespace(
        first_name="Aarav",
        last_name="Sharma",
        company_name="",
        street_address_1="12 MG Road",
        street_address_2="Near Central Park",
        city_area="",
        city="Kota",
        country_area="Rajasthan",
        postal_code=pin,
        phone=phone,
        country=SimpleNamespace(code="IN", name="India"),
    )
    line = SimpleNamespace(
        product_name="Atomic Habits",
        quantity=1,
        quantity_unfulfilled=1,
    )
    return SimpleNamespace(
        number=1042,
        user_email="aarav@example.com",
        created_at=datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc),
        shipping_address=addr,
        billing_address=addr,
        total_gross_amount=Decimal(total_gross),
        total_net_amount=Decimal(total_net),
        lines=_DummyQuerySet([line]),
        invoices=_DummyQuerySet([]),
        fulfillments=_DummyQuerySet([]),
    )


def test_sanitize_indian_phone_and_pincode():
    assert sanitize_indian_phone("+91 98765-43210") == 9876543210
    assert sanitize_indian_phone("09876543210") == 9876543210
    assert sanitize_pincode("324 005") == 324005

    with pytest.raises(ValidationError):
        sanitize_indian_phone("12345")

    with pytest.raises(ValidationError):
        sanitize_pincode("1234")


def test_build_payload_prepaid_and_cod():
    cfg = _sample_config()
    order = _sample_order()
    pickup = {"name": "Kota_WH", "address": cfg.seller_address, "country": "India", "pin": 324005, "phone": 9876543210}

    prepaid_payload = build_create_shipment_payload(
        order=order,
        config=cfg,
        weight_grams=450,
        length_cm=22,
        width_cm=16,
        height_cm=4,
        payment_mode="Prepaid",
        cod_amount=0,
        service="SURFACE",
        pickup_location=pickup,
    )
    assert prepaid_payload["seller_name"] == "EasyToPick"
    assert prepaid_payload["seller_address"] == "24A krishan nagar rangbari kota rajasthan 324005"
    assert prepaid_payload["seller_gst_tin"] == ""
    assert prepaid_payload["payment_mode"] == "Prepaid"
    assert prepaid_payload["cod_amount"] == 0
    assert prepaid_payload["weight"] == 450
    assert prepaid_payload["drop_location"]["pin"] == 324005
    assert prepaid_payload["drop_location"]["phone"] == 9876543210
    assert prepaid_payload["pickup_location"]["name"] == "Kota_WH"
    assert "consignee_alternate_phone" not in prepaid_payload

    cod_payload = build_create_shipment_payload(
        order=order,
        config=cfg,
        weight_grams=600,
        length_cm=24,
        width_cm=18,
        height_cm=5,
        payment_mode="COD",
        cod_amount=Decimal("499.00"),
        service="EXPRESS",
        pickup_location=pickup,
    )
    assert cod_payload["payment_mode"] == "COD"
    assert cod_payload["cod_amount"] == 499.0
    assert cod_payload["service"] == "EXPRESS"


def test_build_payload_cod_over_limit_fails():
    cfg = _sample_config()
    order = _sample_order(total_gross="55000.00", total_net="55000.00")
    with pytest.raises(ValidationError):
        build_create_shipment_payload(
            order=order,
            config=cfg,
            weight_grams=500,
            length_cm=24,
            width_cm=18,
            height_cm=5,
            payment_mode="COD",
            cod_amount=Decimal("55000.00"),
            service="SURFACE",
            pickup_location=None,
        )


def test_resolve_pickup_location_from_ekart_addresses():
    cfg = _sample_config(pickup_alias="Kota_Main")
    ekart_addrs = [
        {
            "alias": "Kota_Main",
            "phone": "9876543210",
            "address_line1": "24A Krishan Nagar",
            "address_line2": "Rangbari",
            "pincode": 324005,
            "city": "Kota",
            "state": "Rajasthan",
            "country": "India",
        }
    ]
    loc = resolve_pickup_location(config=cfg, ekart_addresses=ekart_addrs)
    assert loc is not None
    assert loc["name"] == "Kota_Main"
    assert loc["pin"] == 324005
    assert loc["phone"] == 9876543210


def test_config_defaults_and_validation(monkeypatch):
    monkeypatch.delenv("EKART_CLIENT_ID", raising=False)
    monkeypatch.delenv("EKART_USERNAME", raising=False)
    monkeypatch.delenv("EKART_PASSWORD", raising=False)
    cfg = get_ekart_config()
    assert cfg.seller_name == "EasyToPick"
    with pytest.raises(EkartConfigError):
        cfg.validate_credentials()


def test_client_caches_token_and_retries_on_401():
    cache.clear()
    cfg = _sample_config()
    client = EkartClient(cfg)

    auth_resp_1 = MagicMock(status_code=200)
    auth_resp_1.json.return_value = {"access_token": "tok_1", "expires_in": 3600, "token_type": "Bearer"}

    unauth_resp = MagicMock(status_code=401)
    unauth_resp.json.return_value = {"message": "Unauthorized"}

    auth_resp_2 = MagicMock(status_code=200)
    auth_resp_2.json.return_value = {"access_token": "tok_2", "expires_in": 3600, "token_type": "Bearer"}

    create_resp = MagicMock(status_code=200)
    create_resp.json.return_value = {
        "status": True,
        "remark": "Successfully created shipment",
        "tracking_id": "500999A3408005",
        "vendor": "EKART",
        "barcodes": {"wbn": "WBN1", "order": "1042"},
    }

    with (
        patch("saleor.shipping.ekart.client.requests.post", side_effect=[auth_resp_1, auth_resp_2]) as mock_post,
        patch("saleor.shipping.ekart.client.requests.request", side_effect=[unauth_resp, create_resp]) as mock_req,
    ):
        res = client.create_shipment({"order_number": "1042"})
        assert res["tracking_id"] == "500999A3408005"
        assert mock_post.call_count == 2
        assert mock_req.call_count == 2
        assert mock_req.call_args_list[1].kwargs["headers"]["Authorization"] == "Bearer tok_2"


def test_client_label_pdf_and_error():
    cache.clear()
    cfg = _sample_config()
    client = EkartClient(cfg)

    auth_resp = MagicMock(status_code=200)
    auth_resp.json.return_value = {"access_token": "tok_pdf", "expires_in": 3600}

    pdf_resp = MagicMock(status_code=200, content=b"%PDF-1.4 sample")
    pdf_resp.headers = {"Content-Type": "application/pdf"}

    err_resp = MagicMock(status_code=400, content=b'{"message":"Invalid WBN"}')
    err_resp.headers = {"Content-Type": "application/json"}
    err_resp.json.return_value = {"message": "Invalid WBN"}

    with (
        patch("saleor.shipping.ekart.client.requests.post", return_value=auth_resp),
        patch("saleor.shipping.ekart.client.requests.request", side_effect=[pdf_resp, err_resp]),
    ):
        pdf = client.get_label_pdf(["500999A3408005"])
        assert pdf.startswith(b"%PDF")

        with pytest.raises(EkartAPIError) as exc_info:
            client.get_label_pdf(["BAD"])
        assert "Invalid WBN" in exc_info.value.message


def test_graphql_schema_contains_ekart_queries_and_mutations():
    from saleor.graphql.api import schema
    from saleor.graphql.ekart.types import EkartDefaultsType

    query_fields = schema.get_query_type().fields
    mutation_fields = schema.get_mutation_type().fields

    for name in (
        "ekartDefaults",
        "ekartPickupAddresses",
        "ekartCheckServiceability",
        "ekartTracking",
    ):
        assert name in query_fields

    for name in (
        "ekartCreateShipment",
        "ekartDownloadLabel",
        "ekartCancelShipment",
    ):
        assert name in mutation_fields

    defaults = EkartDefaultsType.from_config()
    assert defaults.seller_name == "EasyToPick"
    assert defaults.default_weight_grams >= 1


def test_ekart_mutations_handle_validation_errors_cleanly():
    from saleor.graphql.ekart.schema import (
        EkartCancelShipment,
        EkartCreateShipment,
        EkartDownloadLabel,
    )

    err = ValidationError({"ekart": ValidationError("Test error message", code="ekart_api_error")})
    for mutation_cls in (EkartCreateShipment, EkartDownloadLabel, EkartCancelShipment):
        response = mutation_cls.handle_errors(err)
        assert len(response.errors) == 1
        assert response.errors[0].message == "Test error message"
        assert response.errors[0].code == "ekart_api_error"



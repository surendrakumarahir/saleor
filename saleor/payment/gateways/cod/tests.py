import copy
from decimal import Decimal

import pytest

from saleor.payment import TransactionKind
from saleor.payment.interface import PaymentData, PaymentLinesData

from .plugin import CODGatewayPlugin


@pytest.fixture(autouse=True)
def _cod_plugin_in_settings(settings):
    settings.PLUGINS = ["saleor.payment.gateways.cod.plugin.CODGatewayPlugin"]


@pytest.fixture
def cod_plugin():
    return CODGatewayPlugin(
        configuration=copy.deepcopy(CODGatewayPlugin.DEFAULT_CONFIGURATION),
        active=True,
    )


def _payment_data() -> PaymentData:
    def lines() -> PaymentLinesData:
        return PaymentLinesData(
            shipping_amount=Decimal("0"),
            voucher_amount=Decimal("0"),
            lines=[],
        )

    return PaymentData(
        gateway=CODGatewayPlugin.PLUGIN_ID,
        amount=Decimal("10.00"),
        currency="USD",
        billing=None,
        shipping=None,
        payment_id=1,
        graphql_payment_id="test-payment-id",
        order_id=None,
        customer_ip_address=None,
        customer_email="buyer@example.com",
        _resolve_lines_data=lines,
    )


def test_cod_authorize_returns_success(cod_plugin):
    response = cod_plugin.authorize_payment(_payment_data(), previous_value=None)
    assert response.is_success
    assert response.kind == TransactionKind.AUTH
    assert response.amount == Decimal("10.00")
    assert response.currency == "USD"
    assert response.error is None
    assert response.transaction_id.startswith("cod-")


def test_cod_capture_returns_success(cod_plugin):
    response = cod_plugin.capture_payment(_payment_data(), previous_value=None)
    assert response.is_success
    assert response.kind == TransactionKind.CAPTURE


def test_cod_process_payment_returns_authorization(cod_plugin):
    response = cod_plugin.process_payment(_payment_data(), previous_value=None)
    assert response.is_success
    assert response.kind == TransactionKind.AUTH
    assert response.transaction_id.startswith("cod-")


def test_cod_refund_returns_success(cod_plugin):
    response = cod_plugin.refund_payment(_payment_data(), previous_value=None)
    assert response.is_success
    assert response.kind == TransactionKind.REFUND

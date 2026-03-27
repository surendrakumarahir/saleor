"""Cash on Delivery (COD) payment gateway — offline authorization, no external API."""

from decimal import Decimal

from django.utils import timezone

from ... import TransactionKind
from ...interface import GatewayConfig, GatewayResponse, PaymentData

GATEWAY_NAME = "Cash on Delivery"


def _cod_transaction_id() -> str:
    """Build a unique offline transaction id for COD (timestamp-based)."""
    return f"cod-{int(timezone.now().timestamp())}"


def authorize(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Mark the payment as authorized locally; no funds are captured."""
    return GatewayResponse(
        is_success=True,
        action_required=False,
        kind=TransactionKind.AUTH,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=_cod_transaction_id(),
        error=None,
    )


def capture(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Record a successful capture for bookkeeping (cash collected at delivery)."""
    return GatewayResponse(
        is_success=True,
        action_required=False,
        kind=TransactionKind.CAPTURE,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token or _cod_transaction_id(),
        error=None,
    )


def void(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Void a pending COD authorization (e.g. order cancelled before delivery)."""
    return GatewayResponse(
        is_success=True,
        action_required=False,
        kind=TransactionKind.VOID,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token or _cod_transaction_id(),
        error=None,
    )


def refund(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Record a refund for returned goods or partial reimbursement."""
    return GatewayResponse(
        is_success=True,
        action_required=False,
        kind=TransactionKind.REFUND,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token or _cod_transaction_id(),
        error=None,
    )


def confirm(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Confirm a COD payment step when the workflow requires explicit confirmation."""
    return GatewayResponse(
        is_success=True,
        action_required=False,
        kind=TransactionKind.CONFIRM,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token or _cod_transaction_id(),
        error=None,
    )


def process_payment(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    """Process checkout payment as authorization only — same as authorize for COD."""
    return authorize(payment_information, config)

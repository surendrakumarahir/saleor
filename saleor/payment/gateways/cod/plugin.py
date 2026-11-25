"""Cash on Delivery payment plugin — registers COD as a native Saleor gateway."""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from saleor.payment.interface import GatewayConfig, PaymentGateway
from saleor.plugins.base_plugin import BasePlugin, ConfigurationTypeField

from . import (
    GATEWAY_NAME,
    authorize,
    capture,
    confirm,
    process_payment,
    refund,
    void,
)

if TYPE_CHECKING:
    from saleor.checkout.fetch import CheckoutInfo, CheckoutLineInfo
    from saleor.payment.interface import GatewayResponse, PaymentData


class CODGatewayPlugin(BasePlugin):
    """Offline Cash on Delivery gateway: authorizes locally without charging."""

    PLUGIN_ID = "mirumee.payments.cod"
    PLUGIN_NAME = "Cash on Delivery"
    PLUGIN_DESCRIPTION = (
        "Collect payment in cash when the order is delivered. "
        "Enable per channel in the dashboard or via pluginUpdate."
    )
    DEFAULT_ACTIVE = False
    CONFIGURATION_PER_CHANNEL = True

    DEFAULT_CONFIGURATION = [
        {"name": "supported_currencies", "value": ""},
        {"name": "minimum_order_amount", "value": "0"},
        {"name": "maximum_order_amount", "value": ""},
        {
            "name": "customer_message",
            "value": "Please keep exact cash ready at the time of delivery.",
        },
    ]

    CONFIG_STRUCTURE = {
        "supported_currencies": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Comma-separated ISO currency codes. Leave empty to allow all.",
            "label": "Supported currencies",
        },
        "minimum_order_amount": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Minimum checkout gross total for COD (same currency as checkout).",
            "label": "Minimum order amount",
        },
        "maximum_order_amount": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Maximum checkout gross total for COD; leave empty for no limit.",
            "label": "Maximum order amount",
        },
        "customer_message": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Message shown to the customer at checkout.",
            "label": "Customer message",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configuration = {item["name"]: item["value"] for item in self.configuration}
        self.config = GatewayConfig(
            gateway_name=GATEWAY_NAME,
            auto_capture=False,
            supported_currencies=configuration.get("supported_currencies") or "",
            connection_params={},
            store_customer=False,
        )
        self._minimum_order_amount = configuration.get("minimum_order_amount") or "0"
        self._maximum_order_amount = configuration.get("maximum_order_amount") or ""
        self._customer_message = configuration.get(
            "customer_message",
            "Please keep exact cash ready at the time of delivery.",
        )

    def _get_gateway_config(self) -> GatewayConfig:
        return self.config

    def _parse_config_decimal(self, raw: str | None, default: Decimal | None) -> Decimal | None:
        """Parse a decimal from plugin configuration; return default on empty or invalid."""
        if raw is None or not str(raw).strip():
            return default
        try:
            return Decimal(str(raw).strip())
        except InvalidOperation:
            return default

    def _is_order_amount_allowed(self, checkout_info: "CheckoutInfo") -> bool:
        """Return False if checkout gross total is outside configured min/max bounds."""
        checkout = checkout_info.checkout
        total = checkout.total
        if total is None:
            return True
        amount = total.gross.amount
        min_amt = self._parse_config_decimal(self._minimum_order_amount, Decimal("0"))
        if min_amt is not None and amount < min_amt:
            return False
        max_raw = self._maximum_order_amount
        if max_raw and str(max_raw).strip():
            max_amt = self._parse_config_decimal(max_raw, None)
            if max_amt is not None and amount > max_amt:
                return False
        return True

    def get_payment_gateways(
        self,
        currency: str | None,
        checkout_info: "CheckoutInfo | None",
        checkout_lines: list["CheckoutLineInfo"] | None,
        previous_value,
    ) -> list[PaymentGateway]:
        """Expose COD when active, currency matches, and order amount is within bounds."""
        if not self.active:
            return []
        supported = (self.config.supported_currencies or "").strip()
        if supported:
            allowed = {c.strip() for c in supported.split(",") if c.strip()}
            if currency and currency not in allowed:
                return []
        if checkout_info is not None and not self._is_order_amount_allowed(checkout_info):
            return []
        payment_config = (
            self.get_payment_config(previous_value)
            if hasattr(self, "get_payment_config")
            else []
        )
        if supported:
            currencies = [c.strip() for c in supported.split(",") if c.strip()]
        else:
            currencies = [currency] if currency else []
        return [
            PaymentGateway(
                id=self.PLUGIN_ID,
                name=self.PLUGIN_NAME,
                config=payment_config,
                currencies=currencies,
            )
        ]

    def token_is_required_as_payment_input(self, previous_value):
        if not self.active:
            return previous_value
        return False

    def authorize_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        if not self.active:
            return previous_value
        return authorize(payment_information, self._get_gateway_config())

    def capture_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        if not self.active:
            return previous_value
        return capture(payment_information, self._get_gateway_config())

    def void_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        if not self.active:
            return previous_value
        return void(payment_information, self._get_gateway_config())

    def refund_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        if not self.active:
            return previous_value
        return refund(payment_information, self._get_gateway_config())

    def confirm_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        if not self.active:
            return previous_value
        return confirm(payment_information, self._get_gateway_config())

    def process_payment(
        self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        if not self.active:
            return previous_value
        return process_payment(payment_information, self._get_gateway_config())

    def get_supported_currencies(self, previous_value):
        if not self.active:
            return previous_value
        raw = self.config.supported_currencies or ""
        if not raw.strip():
            return []
        return [c.strip() for c in raw.split(",") if c.strip()]

    def get_payment_config(self, previous_value):
        if not self.active:
            return previous_value
        return [
            {"field": "customer_message", "value": self._customer_message},
            {"field": "minimum_order_amount", "value": self._minimum_order_amount},
            {"field": "maximum_order_amount", "value": self._maximum_order_amount},
        ]

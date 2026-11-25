"""GraphQL types and enums for Ekart Logistics integration."""

import graphene

from ...shipping.ekart.config import get_ekart_config


class EkartPaymentModeEnum(graphene.Enum):
    COD = "COD"
    PREPAID = "Prepaid"


class EkartServiceTypeEnum(graphene.Enum):
    SURFACE = "SURFACE"
    EXPRESS = "EXPRESS"


class EkartMutationError(graphene.ObjectType):
    field = graphene.String(description="Name of the input field that caused the error.")
    message = graphene.String(required=True, description="Human-readable error message.")
    code = graphene.String(required=True, description="Machine-readable error code.")


class EkartAddressType(graphene.ObjectType):
    alias = graphene.String(required=True)
    phone = graphene.String(required=True)
    address_line1 = graphene.String(required=True)
    address_line2 = graphene.String()
    pincode = graphene.String(required=True)
    city = graphene.String()
    state = graphene.String()
    country = graphene.String()


class EkartServiceabilityType(graphene.ObjectType):
    status = graphene.Boolean(required=True)
    pincode = graphene.String(required=True)
    remark = graphene.String()
    cod = graphene.Boolean()
    max_cod_amount = graphene.Int()
    forward_pickup = graphene.Boolean()
    forward_drop = graphene.Boolean()
    reverse_pickup = graphene.Boolean()
    reverse_drop = graphene.Boolean()
    city = graphene.String()
    state = graphene.String()
    error = graphene.String()


class EkartDefaultsType(graphene.ObjectType):
    configured = graphene.Boolean(required=True)
    seller_name = graphene.String(required=True)
    seller_address = graphene.String(required=True)
    default_weight_grams = graphene.Int(required=True)
    default_length_cm = graphene.Int(required=True)
    default_width_cm = graphene.Int(required=True)
    default_height_cm = graphene.Int(required=True)
    pickup_alias = graphene.String()

    @staticmethod
    def from_config():
        cfg = get_ekart_config()
        return EkartDefaultsType(
            configured=bool(cfg.client_id and cfg.username and cfg.password),
            seller_name=cfg.seller_name,
            seller_address=cfg.seller_address,
            default_weight_grams=cfg.default_weight_grams,
            default_length_cm=cfg.default_length_cm,
            default_width_cm=cfg.default_width_cm,
            default_height_cm=cfg.default_height_cm,
            pickup_alias=cfg.pickup_alias or None,
        )


class EkartCreateShipmentInput(graphene.InputObjectType):
    weight_grams = graphene.Int(
        required=True, description="Total parcel weight in grams (minimum 1)."
    )
    length_cm = graphene.Int(
        required=True, description="Parcel length in centimeters (minimum 1)."
    )
    width_cm = graphene.Int(
        required=True, description="Parcel width in centimeters (minimum 1)."
    )
    height_cm = graphene.Int(
        required=True, description="Parcel height in centimeters (minimum 1)."
    )
    payment_mode = EkartPaymentModeEnum(
        required=True, description="Payment mode: COD or PREPAID."
    )
    cod_amount = graphene.Float(
        required=False,
        description="Amount to collect on delivery (required if paymentMode is COD).",
    )
    service = EkartServiceTypeEnum(
        default_value="SURFACE",
        description="Ekart service level: SURFACE or EXPRESS.",
    )
    pickup_alias = graphene.String(
        required=False,
        description="Optional Ekart registered pickup location alias.",
    )
    fulfillment_id = graphene.ID(
        required=False,
        description="Optional existing fulfillment ID to attach tracking number to.",
    )
    notify_customer = graphene.Boolean(
        default_value=True,
        description="If true, send Saleor fulfillment notification to customer.",
    )


class EkartLabelPayload(graphene.ObjectType):
    tracking_id = graphene.String(required=True)
    filename = graphene.String(required=True)
    pdf_base64 = graphene.String(required=True)


class EkartTrackingEventType(graphene.ObjectType):
    status = graphene.String()
    description = graphene.String()
    city = graphene.String()
    hub_name = graphene.String()
    event_date = graphene.String()


class EkartTrackingType(graphene.ObjectType):
    tracking_id = graphene.String(required=True)
    tracking_url = graphene.String(required=True)
    delivered = graphene.Boolean()
    status = graphene.String()
    expected_delivery_date = graphene.String()
    history = graphene.List(graphene.NonNull(EkartTrackingEventType), required=True)


class EkartRateQuoteType(graphene.ObjectType):
    service = graphene.String(required=True)
    available = graphene.Boolean(required=True)
    courier_group = graphene.String()
    tat_min = graphene.Int()
    tat_max = graphene.Int()
    forward_freight = graphene.String()
    fuel_surcharge = graphene.String()
    cod_charges = graphene.String()
    taxes = graphene.String()
    total_estimate = graphene.String()
    rto_estimate = graphene.String()
    zone = graphene.String()
    volumetric_weight_grams = graphene.Int()
    billing_weight_grams = graphene.Int()
    error = graphene.String()


class EkartRateEstimatePayload(graphene.ObjectType):
    pickup_pincode = graphene.String(required=True)
    drop_pincode = graphene.String(required=True)
    quotes = graphene.List(graphene.NonNull(EkartRateQuoteType), required=True)
    error = graphene.String()

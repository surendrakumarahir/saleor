"""GraphQL queries and mutations for Ekart Logistics shipment workflow."""

import base64
from collections import defaultdict
from decimal import Decimal
from typing import cast
from uuid import UUID

import graphene
from django.core.exceptions import ValidationError

from ...account.models import User
from ...core.tracing import traced_atomic_transaction
from ...order import FulfillmentStatus, OrderStatus, events as order_events
from ...order.actions import (
    OrderFulfillmentLineInfo,
    cancel_fulfillment as cancel_saleor_fulfillment,
    create_fulfillments,
    fulfillment_tracking_updated,
)
from ...order.notifications import send_fulfillment_update
from ...permission.enums import OrderPermissions
from ...shipping.ekart import EkartClient, EkartError, get_ekart_config
from ...shipping.ekart.payload import (
    PUBLIC_TRACKING_URL_TEMPLATE,
    build_create_shipment_payload,
    resolve_pickup_location,
    sanitize_pincode,
    validate_ekart_config_or_raise,
)
from ...warehouse.models import Stock, Warehouse
from ..app.dataloaders import get_app_promise
from ..core import ResolveInfo
from ..core.context import SyncWebhookControlContext
from ..core.doc_category import DOC_CATEGORY_ORDERS
from ..core.mutations import BaseMutation
from ..decorators import permission_required
from ..order.types import Fulfillment, Order
from ..plugins.dataloaders import get_plugin_manager_promise
from ..site.dataloaders import get_site_promise
from .types import (
    EkartAddressType,
    EkartCreateShipmentInput,
    EkartDefaultsType,
    EkartLabelPayload,
    EkartMutationError,
    EkartPaymentModeEnum,
    EkartRateEstimatePayload,
    EkartRateQuoteType,
    EkartServiceabilityType,
    EkartTrackingEventType,
    EkartTrackingType,
)


def _resolve_warehouse_for_order_line(order, order_line) -> Warehouse | None:
    allocation = (
        order_line.allocations.filter(quantity_allocated__gt=0)
        .select_related("stock__warehouse")
        .first()
    )
    if allocation and allocation.stock_id:
        return allocation.stock.warehouse

    if order_line.variant_id:
        stock = (
            Stock.objects.filter(
                product_variant_id=order_line.variant_id,
                warehouse__channels=order.channel_id,
            )
            .select_related("warehouse")
            .order_by("-quantity")
            .first()
        )
        if stock:
            return stock.warehouse

    warehouse = Warehouse.objects.for_channel(order.channel_id).first()
    if warehouse:
        return warehouse

    return Warehouse.objects.first()


def _save_ekart_metadata(
    fulfillment,
    *,
    tracking_id: str,
    response_data: dict,
    payload: dict,
    service: str,
    payment_mode: str,
    weight_grams: int,
    length_cm: int,
    width_cm: int,
    height_cm: int,
) -> None:
    barcodes = response_data.get("barcodes") or {}
    tracking_url = PUBLIC_TRACKING_URL_TEMPLATE.format(tracking_id=tracking_id)
    fulfillment.store_value_in_private_metadata(
        {
            "ekart_tracking_id": str(tracking_id),
            "ekart_vendor": str(response_data.get("vendor") or "EKART"),
            "ekart_wbn": str(barcodes.get("wbn") or tracking_id),
            "ekart_order_number": str(payload.get("order_number") or ""),
            "ekart_service": str(service),
            "ekart_payment_mode": str(payment_mode),
            "ekart_cod_amount": str(payload.get("cod_amount", 0)),
            "ekart_weight_grams": str(weight_grams),
            "ekart_dimensions_cm": f"{length_cm}x{width_cm}x{height_cm}",
            "ekart_tracking_url": tracking_url,
            "ekart_status": "CREATED",
        }
    )
    fulfillment.save(update_fields=["private_metadata"])


class EkartQueries(graphene.ObjectType):
    ekart_defaults = graphene.Field(
        EkartDefaultsType,
        description="Get Ekart configuration status and default parcel dimensions.",
    )
    ekart_pickup_addresses = graphene.List(
        graphene.NonNull(EkartAddressType),
        description="Fetch registered pickup/RTO addresses from Ekart Elite.",
    )
    ekart_check_serviceability = graphene.Field(
        EkartServiceabilityType,
        pincode=graphene.String(required=True),
        description="Check Ekart COD and Prepaid serviceability for an Indian pincode.",
    )
    ekart_tracking = graphene.Field(
        EkartTrackingType,
        tracking_id=graphene.String(required=True),
        description="Fetch live Ekart tracking details for a tracking ID / WBN.",
    )
    ekart_estimate_rates = graphene.Field(
        EkartRateEstimatePayload,
        order_id=graphene.ID(required=True),
        weight_grams=graphene.Int(required=True),
        length_cm=graphene.Int(required=True),
        width_cm=graphene.Int(required=True),
        height_cm=graphene.Int(required=True),
        payment_mode=EkartPaymentModeEnum(required=True),
        cod_amount=graphene.Float(required=False),
        pickup_alias=graphene.String(required=False),
        description="Estimate Ekart SURFACE & EXPRESS shipping charges before booking.",
    )

    @permission_required(OrderPermissions.MANAGE_ORDERS)
    def resolve_ekart_defaults(self, _info: ResolveInfo):
        return EkartDefaultsType.from_config()

    @permission_required(OrderPermissions.MANAGE_ORDERS)
    def resolve_ekart_pickup_addresses(self, _info: ResolveInfo):
        config = get_ekart_config()
        if not (config.client_id and config.username and config.password):
            return []
        try:
            addresses = EkartClient(config).get_addresses()
        except EkartError:
            return []
        result = []
        for addr in addresses:
            result.append(
                EkartAddressType(
                    alias=str(addr.get("alias") or ""),
                    phone=str(addr.get("phone") or ""),
                    address_line1=str(addr.get("address_line1") or ""),
                    address_line2=addr.get("address_line2") or None,
                    pincode=str(addr.get("pincode") or ""),
                    city=addr.get("city") or None,
                    state=addr.get("state") or None,
                    country=addr.get("country") or "India",
                )
            )
        return result

    @permission_required(OrderPermissions.MANAGE_ORDERS)
    def resolve_ekart_check_serviceability(self, _info: ResolveInfo, pincode: str):
        try:
            pin_int = sanitize_pincode(pincode)
        except ValidationError as exc:
            msg = exc.messages[0] if exc.messages else "Invalid pincode."
            return EkartServiceabilityType(
                status=False,
                pincode=str(pincode),
                remark=msg,
                error=msg,
            )

        config = get_ekart_config()
        if not (config.client_id and config.username and config.password):
            return EkartServiceabilityType(
                status=False,
                pincode=str(pin_int),
                remark="Ekart credentials not configured yet.",
                error="Ekart credentials not configured yet.",
            )

        try:
            data = EkartClient(config).check_serviceability(pin_int)
        except EkartError as exc:
            return EkartServiceabilityType(
                status=False,
                pincode=str(pin_int),
                remark=exc.message,
                error=exc.message,
            )

        details = data.get("details") or {}
        return EkartServiceabilityType(
            status=bool(data.get("status", False)),
            pincode=str(data.get("pincode") or pin_int),
            remark=data.get("remark"),
            cod=details.get("cod"),
            max_cod_amount=details.get("max_cod_amount"),
            forward_pickup=details.get("forward_pickup"),
            forward_drop=details.get("forward_drop"),
            reverse_pickup=details.get("reverse_pickup"),
            reverse_drop=details.get("reverse_drop"),
            city=details.get("city"),
            state=details.get("state"),
        )

    @permission_required(OrderPermissions.MANAGE_ORDERS)
    def resolve_ekart_tracking(self, _info: ResolveInfo, tracking_id: str):
        clean_id = (tracking_id or "").strip()
        tracking_url = PUBLIC_TRACKING_URL_TEMPLATE.format(tracking_id=clean_id)
        config = get_ekart_config()
        if not clean_id or not (config.client_id and config.username and config.password):
            return EkartTrackingType(
                tracking_id=clean_id,
                tracking_url=tracking_url,
                delivered=False,
                status=None,
                expected_delivery_date=None,
                history=[],
            )

        raw = EkartClient(config).track_shipment(clean_id)
        entry = raw.get(clean_id) or next(iter(raw.values()), {}) if isinstance(raw, dict) else {}
        if not isinstance(entry, dict):
            entry = {}

        history_list = entry.get("history") or []
        if not history_list and isinstance(entry.get("shipments"), list) and entry["shipments"]:
            first_ship = entry["shipments"][0]
            history_list = first_ship.get("history") or []
            delivered_val = str(first_ship.get("delivered", "")).lower() == "true"
            expected_date = first_ship.get("expected_delivery_date")
            current_status = entry.get("status")
        else:
            delivered_val = bool(entry.get("delivered", False))
            expected_date = entry.get("expected_delivery_date")
            current_status = (
                history_list[-1].get("status")
                if history_list and isinstance(history_list[-1], dict)
                else entry.get("status")
            )

        events = []
        for item in history_list:
            if isinstance(item, dict):
                events.append(
                    EkartTrackingEventType(
                        status=item.get("status"),
                        description=item.get("public_description") or item.get("description"),
                        city=item.get("city"),
                        hub_name=item.get("hub_name"),
                        event_date=item.get("event_date_iso8601") or item.get("event_date"),
                    )
                )

        return EkartTrackingType(
            tracking_id=clean_id,
            tracking_url=tracking_url,
            delivered=delivered_val,
            status=current_status,
            expected_delivery_date=expected_date,
            history=events,
        )

    @permission_required(OrderPermissions.MANAGE_ORDERS)
    def resolve_ekart_estimate_rates(
        self,
        info: ResolveInfo,
        order_id: str,
        weight_grams: int,
        length_cm: int,
        width_cm: int,
        height_cm: int,
        payment_mode: str,
        cod_amount: float | None = None,
        pickup_alias: str | None = None,
    ):
        from ...order.models import Order as OrderModel
        from ..core.utils import from_global_id_or_error

        _, order_pk = from_global_id_or_error(order_id, Order)
        order = OrderModel.objects.select_related("shipping_address", "channel").filter(pk=order_pk).first()
        if not order or not order.shipping_address:
            return EkartRateEstimatePayload(
                pickup_pincode="",
                drop_pincode="",
                quotes=[],
                error="Order or shipping address not found.",
            )

        try:
            drop_pin = str(sanitize_pincode(order.shipping_address.postal_code))
        except ValidationError as exc:
            msg = exc.messages[0] if exc.messages else "Invalid shipping pincode."
            return EkartRateEstimatePayload(
                pickup_pincode="",
                drop_pincode=str(order.shipping_address.postal_code or ""),
                quotes=[],
                error=msg,
            )

        config = get_ekart_config()
        if not (config.client_id and config.username and config.password):
            return EkartRateEstimatePayload(
                pickup_pincode="",
                drop_pincode=drop_pin,
                quotes=[],
                error="Ekart API credentials are not configured yet.",
            )

        client = EkartClient(config)
        try:
            ekart_addresses = client.get_addresses()
        except EkartError:
            ekart_addresses = []

        fallback_wh = Warehouse.objects.for_channel(order.channel_id).first() or Warehouse.objects.first()
        pickup_loc = resolve_pickup_location(
            config=config,
            ekart_addresses=ekart_addresses,
            pickup_alias=pickup_alias,
            fallback_warehouse=fallback_wh,
        )

        pickup_pin = ""
        if pickup_loc and pickup_loc.get("pin"):
            pickup_pin = str(pickup_loc["pin"])
        else:
            # Fallback to any 6-digit pincode in configured seller_address
            import re

            m = re.search(r"\b(\d{6})\b", config.seller_address or "")
            if m:
                pickup_pin = m.group(1)

        if not pickup_pin:
            return EkartRateEstimatePayload(
                pickup_pincode="",
                drop_pincode=drop_pin,
                quotes=[],
                error="Could not determine pickup warehouse pincode.",
            )

        payment_mode_str = str(getattr(payment_mode, "value", payment_mode))
        invoice_amt = max(1, round(float(order.total_gross_amount or 1), 2))
        resolved_cod = 0.0
        if payment_mode_str == "COD":
            resolved_cod = float(cod_amount if cod_amount is not None else invoice_amt)

        volumetric_grams = max(1, round((int(length_cm) * int(width_cm) * int(height_cm)) / 5.0))
        default_billing_grams = max(int(weight_grams), volumetric_grams)

        quotes: list[EkartRateQuoteType] = []
        for svc in ("SURFACE", "EXPRESS"):
            v3_payload = {
                "pickupPincode": pickup_pin,
                "dropPincode": drop_pin,
                "length": str(int(length_cm)),
                "width": str(int(width_cm)),
                "height": str(int(height_cm)),
                "weight": str(int(weight_grams)),
                "paymentType": payment_mode_str,
                "serviceType": svc,
                "codAmount": str(resolved_cod if payment_mode_str == "COD" else 0),
                "invoiceAmount": str(invoice_amt),
            }
            try:
                v3_results = client.check_serviceability_v3(v3_payload)
            except EkartError as exc:
                quotes.append(
                    EkartRateQuoteType(
                        service=svc,
                        available=False,
                        volumetric_weight_grams=volumetric_grams,
                        billing_weight_grams=default_billing_grams,
                        error=exc.message,
                    )
                )
                continue

            if not v3_results:
                quotes.append(
                    EkartRateQuoteType(
                        service=svc,
                        available=False,
                        volumetric_weight_grams=volumetric_grams,
                        billing_weight_grams=default_billing_grams,
                        error=f"No {svc} service returned for this route.",
                    )
                )
                continue

            # Optionally enrich with zone / billingWeight from /data/pricing/estimate
            zone = None
            vol_w = volumetric_grams
            bill_w = default_billing_grams
            try:
                est = client.get_pricing_estimate(
                    {
                        "billingClientType": "EXISTING_CLIENT",
                        "shippingDirection": "FORWARD",
                        "serviceType": svc,
                        "pickupPincode": int(pickup_pin),
                        "dropPincode": int(drop_pin),
                        "length": int(length_cm),
                        "width": int(width_cm),
                        "height": int(height_cm),
                        "weight": int(weight_grams),
                        "paymentMethod": payment_mode_str,
                        "paymentMode": payment_mode_str,
                        "codAmount": resolved_cod if payment_mode_str == "COD" else 0,
                        "invoiceAmount": invoice_amt,
                    }
                )
                if est.get("zone"):
                    zone = str(est["zone"])
                if est.get("volumetricWeight"):
                    vol_w = max(1, round(float(est["volumetricWeight"])))
                if est.get("billingWeight"):
                    bill_w = max(1, round(float(est["billingWeight"])))
            except (EkartError, ValueError, TypeError):
                pass

            first = v3_results[0]
            tat = first.get("tat") or {}
            fwd = first.get("forwardDeliveredCharges") or {}
            rto = first.get("rtoDeliveredCharges") or {}
            quotes.append(
                EkartRateQuoteType(
                    service=svc,
                    available=True,
                    courier_group=first.get("courierGroup"),
                    tat_min=tat.get("min"),
                    tat_max=tat.get("max"),
                    forward_freight=str(fwd.get("forwardFreight")) if fwd.get("forwardFreight") is not None else None,
                    fuel_surcharge=str(fwd.get("forwardFuelSurcharge")) if fwd.get("forwardFuelSurcharge") is not None else None,
                    cod_charges=str(fwd.get("codCharges")) if fwd.get("codCharges") is not None else None,
                    taxes=str(fwd.get("deliveredTotalTax")) if fwd.get("deliveredTotalTax") is not None else None,
                    total_estimate=str(fwd.get("totalForwardDeliveredEstimate")) if fwd.get("totalForwardDeliveredEstimate") is not None else None,
                    rto_estimate=str(rto.get("totalRTODeliveredEstimate")) if rto.get("totalRTODeliveredEstimate") is not None else None,
                    zone=zone,
                    volumetric_weight_grams=vol_w,
                    billing_weight_grams=bill_w,
                )
            )

        return EkartRateEstimatePayload(
            pickup_pincode=pickup_pin,
            drop_pincode=drop_pin,
            quotes=quotes,
        )


class EkartCreateShipment(BaseMutation):
    order = graphene.Field(Order, description="Updated Saleor order.")
    fulfillment = graphene.Field(
        Fulfillment, description="Created or updated fulfillment with Ekart AWB."
    )
    tracking_id = graphene.String(description="Ekart tracking ID (AWB).")
    tracking_url = graphene.String(description="Public Ekart tracking URL.")

    class Arguments:
        order_id = graphene.ID(required=True, description="ID of the Saleor order.")
        input = EkartCreateShipmentInput(required=True)

    class Meta:
        description = "Book a shipment parcel in Ekart Elite and fulfill the order in Saleor."
        doc_category = DOC_CATEGORY_ORDERS
        permissions = (OrderPermissions.MANAGE_ORDERS,)
        error_type_class = EkartMutationError

    @classmethod
    def perform_mutation(  # type: ignore[override]
        cls, _root, info: ResolveInfo, /, *, order_id: str, input: dict
    ):
        user = cast(User, info.context.user)
        order = cls.get_node_or_error(info, order_id, field="orderId", only_type=Order)
        cls.check_channel_permissions(info, [order.channel_id])

        if order.status in {OrderStatus.DRAFT, OrderStatus.UNCONFIRMED, OrderStatus.CANCELED, OrderStatus.EXPIRED}:
            raise ValidationError(
                {
                    "orderId": ValidationError(
                        f"Cannot create Ekart parcel for order with status {order.status}.",
                        code="invalid_order_status",
                    )
                }
            )

        config = get_ekart_config()
        validate_ekart_config_or_raise(config)

        weight_grams = int(input["weight_grams"])
        length_cm = int(input["length_cm"])
        width_cm = int(input["width_cm"])
        height_cm = int(input["height_cm"])
        payment_mode = str(input["payment_mode"])
        cod_amount = input.get("cod_amount")
        service = str(input.get("service") or "SURFACE")
        pickup_alias = input.get("pickup_alias")
        fulfillment_id = input.get("fulfillment_id")
        notify_customer = bool(input.get("notify_customer", True))

        target_fulfillment = None
        unfulfilled_lines = [line for line in order.lines.all() if line.quantity_unfulfilled > 0]

        if fulfillment_id:
            target_fulfillment = cls.get_node_or_error(
                info, fulfillment_id, field="fulfillmentId", only_type=Fulfillment
            )
            if target_fulfillment.order_id != order.pk:
                raise ValidationError(
                    {
                        "fulfillmentId": ValidationError(
                            "Fulfillment does not belong to this order.",
                            code="invalid_fulfillment",
                        )
                    }
                )
            if (
                target_fulfillment.tracking_number
                and target_fulfillment.private_metadata.get("ekart_status") != "CANCELLED"
            ):
                raise ValidationError(
                    {
                        "fulfillmentId": ValidationError(
                            f"Fulfillment already has tracking number {target_fulfillment.tracking_number}.",
                            code="shipment_already_exists",
                        )
                    }
                )
            lines_to_ship = [fl.order_line for fl in target_fulfillment.lines.select_related("order_line")]
        elif unfulfilled_lines:
            lines_to_ship = unfulfilled_lines
        else:
            existing_without_tracking = (
                order.fulfillments.filter(
                    status__in=[FulfillmentStatus.FULFILLED, FulfillmentStatus.WAITING_FOR_APPROVAL],
                    tracking_number="",
                )
                .order_by("-created_at")
                .first()
            )
            if existing_without_tracking:
                target_fulfillment = existing_without_tracking
                lines_to_ship = [
                    fl.order_line
                    for fl in target_fulfillment.lines.select_related("order_line")
                ]
            else:
                raise ValidationError(
                    {
                        "orderId": ValidationError(
                            "All order items are already fulfilled with tracking numbers.",
                            code="shipment_already_exists",
                        )
                    }
                )

        # Resolve warehouse before hitting Ekart so fulfillment creation won't fail afterward
        lines_for_warehouses: defaultdict[UUID, list[OrderFulfillmentLineInfo]] = defaultdict(list)
        primary_warehouse: Warehouse | None = None
        if target_fulfillment is None:
            for line in lines_to_ship:
                warehouse = _resolve_warehouse_for_order_line(order, line)
                if not warehouse:
                    raise ValidationError(
                        {
                            "orderId": ValidationError(
                                "No warehouse is configured for this order's channel.",
                                code="missing_warehouse",
                            )
                        }
                    )
                if primary_warehouse is None:
                    primary_warehouse = warehouse
                lines_for_warehouses[warehouse.pk].append(
                    {"order_line": line, "quantity": line.quantity_unfulfilled}
                )
        else:
            first_fl = target_fulfillment.lines.select_related("stock__warehouse").first()
            primary_warehouse = (
                first_fl.stock.warehouse
                if first_fl and first_fl.stock_id
                else Warehouse.objects.for_channel(order.channel_id).first() or Warehouse.objects.first()
            )

        client = EkartClient(config)
        try:
            ekart_addresses = client.get_addresses()
        except EkartError:
            ekart_addresses = []

        pickup_location = resolve_pickup_location(
            config=config,
            ekart_addresses=ekart_addresses,
            pickup_alias=pickup_alias,
            fallback_warehouse=primary_warehouse,
        )

        payload = build_create_shipment_payload(
            order=order,
            config=config,
            weight_grams=weight_grams,
            length_cm=length_cm,
            width_cm=width_cm,
            height_cm=height_cm,
            payment_mode=payment_mode,
            cod_amount=Decimal(str(cod_amount)) if cod_amount is not None else None,
            service=service,
            pickup_location=pickup_location,
            lines_to_ship=lines_to_ship,
        )

        try:
            ekart_response = client.create_shipment(payload)
        except EkartError as exc:
            raise ValidationError(
                {"ekart": ValidationError(exc.message, code=exc.code)}
            ) from exc

        tracking_id = str(ekart_response["tracking_id"])
        tracking_url = PUBLIC_TRACKING_URL_TEMPLATE.format(tracking_id=tracking_id)

        app = get_app_promise(info.context).get()
        manager = get_plugin_manager_promise(info.context).get()
        site = get_site_promise(info.context).get()

        with traced_atomic_transaction():
            if target_fulfillment is None:
                created = create_fulfillments(
                    user,
                    app,
                    order,
                    dict(lines_for_warehouses),
                    manager,
                    site.settings,
                    notify_customer=notify_customer,
                    allow_stock_to_be_exceeded=True,
                    auto_approved=True,
                    tracking_number=tracking_id,
                )
                result_fulfillment = created[0]
            else:
                target_fulfillment.tracking_number = tracking_id
                target_fulfillment.save(update_fields=["tracking_number"])
                fulfillment_tracking_updated(
                    target_fulfillment, user, app, tracking_id, manager
                )
                if notify_customer:
                    send_fulfillment_update(order, target_fulfillment, manager)
                result_fulfillment = target_fulfillment

            _save_ekart_metadata(
                result_fulfillment,
                tracking_id=tracking_id,
                response_data=ekart_response,
                payload=payload,
                service=service,
                payment_mode=payment_mode,
                weight_grams=weight_grams,
                length_cm=length_cm,
                width_cm=width_cm,
                height_cm=height_cm,
            )

            order_events.external_notification_event(
                order=order,
                user=user,
                app=app,
                message=(
                    f"Ekart parcel created (AWB: {tracking_id}, {payment_mode}, "
                    f"{weight_grams}g, {service})"
                ),
                parameters={
                    "tracking_id": tracking_id,
                    "payment_mode": payment_mode,
                    "service": service,
                    "weight_grams": weight_grams,
                },
            )

        order.refresh_from_db()
        return EkartCreateShipment(
            order=SyncWebhookControlContext(order),
            fulfillment=SyncWebhookControlContext(node=result_fulfillment),
            tracking_id=tracking_id,
            tracking_url=tracking_url,
        )


class EkartDownloadLabel(BaseMutation):
    label = graphene.Field(EkartLabelPayload, description="Ekart shipping label PDF in base64.")

    class Arguments:
        tracking_id = graphene.String(
            required=True, description="Ekart tracking ID / WBN."
        )

    class Meta:
        description = "Download an official Ekart shipping label PDF."
        doc_category = DOC_CATEGORY_ORDERS
        permissions = (OrderPermissions.MANAGE_ORDERS,)
        error_type_class = EkartMutationError

    @classmethod
    def perform_mutation(  # type: ignore[override]
        cls, _root, _info: ResolveInfo, /, *, tracking_id: str
    ):
        clean_id = (tracking_id or "").strip()
        if not clean_id:
            raise ValidationError(
                {"trackingId": ValidationError("Tracking ID is required.", code="required")}
            )

        config = get_ekart_config()
        validate_ekart_config_or_raise(config)

        try:
            pdf_bytes = EkartClient(config).get_label_pdf([clean_id])
        except EkartError as exc:
            raise ValidationError(
                {"ekart": ValidationError(exc.message, code=exc.code)}
            ) from exc

        encoded = base64.b64encode(pdf_bytes).decode("ascii")
        return EkartDownloadLabel(
            label=EkartLabelPayload(
                tracking_id=clean_id,
                filename=f"ekart-label-{clean_id}.pdf",
                pdf_base64=encoded,
            )
        )


class EkartCancelShipment(BaseMutation):
    order = graphene.Field(Order, description="Updated Saleor order.")
    fulfillment = graphene.Field(Fulfillment, description="Updated or canceled fulfillment.")
    tracking_id = graphene.String(description="Canceled Ekart tracking ID.")

    class Arguments:
        fulfillment_id = graphene.ID(
            required=True, description="ID of the Saleor fulfillment to cancel in Ekart."
        )
        cancel_fulfillment = graphene.Boolean(
            default_value=True,
            description="If true, also cancel the Saleor fulfillment and restock items.",
        )

    class Meta:
        description = "Cancel an Ekart shipment parcel and optionally cancel the Saleor fulfillment."
        doc_category = DOC_CATEGORY_ORDERS
        permissions = (OrderPermissions.MANAGE_ORDERS,)
        error_type_class = EkartMutationError

    @classmethod
    def perform_mutation(  # type: ignore[override]
        cls,
        _root,
        info: ResolveInfo,
        /,
        *,
        fulfillment_id: str,
        cancel_fulfillment: bool = True,
    ):
        cancel_in_saleor = bool(cancel_fulfillment)
        user = cast(User, info.context.user)
        fulfillment = cls.get_node_or_error(
            info, fulfillment_id, field="fulfillmentId", only_type=Fulfillment
        )
        order = fulfillment.order
        cls.check_channel_permissions(info, [order.channel_id])

        tracking_id = (
            fulfillment.private_metadata.get("ekart_tracking_id")
            or fulfillment.tracking_number
            or ""
        ).strip()
        if not tracking_id:
            raise ValidationError(
                {
                    "fulfillmentId": ValidationError(
                        "No Ekart tracking ID found on this fulfillment.",
                        code="missing_tracking_id",
                    )
                }
            )

        config = get_ekart_config()
        validate_ekart_config_or_raise(config)

        try:
            EkartClient(config).cancel_shipment(tracking_id)
        except EkartError as exc:
            raise ValidationError(
                {"ekart": ValidationError(exc.message, code=exc.code)}
            ) from exc

        app = get_app_promise(info.context).get()
        manager = get_plugin_manager_promise(info.context).get()

        with traced_atomic_transaction():
            fulfillment.store_value_in_private_metadata({"ekart_status": "CANCELLED"})
            fulfillment.save(update_fields=["private_metadata"])

            order_events.external_notification_event(
                order=order,
                user=user,
                app=app,
                message=f"Ekart parcel cancelled (AWB: {tracking_id})",
                parameters={"tracking_id": tracking_id},
            )

            if cancel_in_saleor and fulfillment.can_edit():
                first_fl = fulfillment.lines.select_related("stock__warehouse").first()
                warehouse = (
                    first_fl.stock.warehouse
                    if first_fl and first_fl.stock_id
                    else Warehouse.objects.for_channel(order.channel_id).first()
                )
                fulfillment = cancel_saleor_fulfillment(
                    fulfillment, user, app, warehouse, manager
                )

        order.refresh_from_db()
        return EkartCancelShipment(
            order=SyncWebhookControlContext(order),
            fulfillment=SyncWebhookControlContext(node=fulfillment),
            tracking_id=tracking_id,
        )


class EkartMutations(graphene.ObjectType):
    ekart_create_shipment = EkartCreateShipment.Field()
    ekart_download_label = EkartDownloadLabel.Field()
    ekart_cancel_shipment = EkartCancelShipment.Field()

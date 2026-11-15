from django.db.models import Avg, Count
from saleor.order.models import Order, OrderLine
from saleor.order import OrderStatus


def recalculate_product_rating(product):
    """Recalculate average rating and review count for a product."""
    from saleor.product.models import Product, ProductReview, ProductReviewStatus

    if not isinstance(product, Product):
        product = Product.objects.filter(pk=product).first()
        if not product:
            return

    stats = ProductReview.objects.filter(
        product=product,
        status=ProductReviewStatus.APPROVED,
    ).aggregate(
        avg_rating=Avg("rating"),
        total_count=Count("id"),
    )

    avg_val = stats["avg_rating"]
    total_count = stats["total_count"] or 0

    product.rating = round(avg_val, 2) if avg_val is not None else None

    if hasattr(product, "metadata"):
        if product.metadata is None:
            product.metadata = {}
        product.metadata["review_count"] = str(total_count)
        product.metadata["average_rating"] = f"{round(avg_val, 1):.1f}" if avg_val is not None else "0.0"
        product.save(update_fields=["rating", "metadata"])
    else:
        product.save(update_fields=["rating"])


def check_is_verified_buyer(product_id, user=None, email=None):
    """Check if the given user or email has ever purchased this product in a completed order."""
    if not product_id or (not user and not email):
        return False

    valid_statuses = [
        OrderStatus.FULFILLED,
        OrderStatus.PARTIALLY_FULFILLED,
        OrderStatus.UNFULFILLED,
    ]

    qs = OrderLine.objects.filter(
        variant__product_id=product_id,
        order__status__in=valid_statuses,
    )

    if user and getattr(user, "is_authenticated", False):
        if qs.filter(order__user_id=user.id).exists():
            return True

    if email:
        clean_email = email.strip().lower()
        if qs.filter(order__user_email__iexact=clean_email).exists():
            return True

    return False

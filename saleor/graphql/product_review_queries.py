"""GraphQL queries for Product Review Management."""

import graphene
from django.db.models import Q

from saleor.graphql.core.connection import (
    CountableConnection,
    create_connection_slice,
    filter_connection_queryset,
)
from saleor.graphql.core.fields import FilterConnectionField
from saleor.graphql.core.utils import from_global_id_or_error
from saleor.graphql.product_review_filters import ProductReviewFilterInput
from saleor.graphql.product_review_sorters import ProductReviewSortingInput
from saleor.graphql.product_review_types import (
    ProductReviewConnection,
    ProductReviewType,
)
from saleor.product.models import ProductReview, ProductReviewStatus


def _is_staff_user(info):
    context = getattr(info, "context", None)
    if not context:
        return False
    user = getattr(context, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_staff or user.has_perm("product.manage_products"))


class ProductReviewQueries(graphene.ObjectType):
    """Product Review queries exposed through GraphQL."""

    product_review = graphene.Field(
        ProductReviewType,
        id=graphene.ID(required=True, description="Product Review ID."),
        description="Retrieve a single product review.",
    )

    product_reviews = FilterConnectionField(
        ProductReviewConnection,
        filter=ProductReviewFilterInput(),
        sort_by=ProductReviewSortingInput(),
        product_slug=graphene.String(description="Filter by product slug."),
        product_id=graphene.ID(description="Filter by product ID."),
        client_token=graphene.String(description="Client token for guest identification."),
        user_id=graphene.ID(description="User ID for reviewer identification."),
        description="Retrieve a list of product reviews.",
    )

    def resolve_product_review(self, info, id):
        try:
            _, pk_int = from_global_id_or_error(id, "ProductReview", raise_error=False)
            lookup_id = pk_int if pk_int else id
            return ProductReview.objects.select_related("product", "user").prefetch_related("product__media").filter(pk=lookup_id).first()
        except Exception:
            return ProductReview.objects.select_related("product", "user").prefetch_related("product__media").filter(pk=id).first()

    def resolve_product_reviews(self, info, product_slug=None, product_id=None, client_token=None, user_id=None, **kwargs):
        qs = ProductReview.objects.select_related("product", "user").prefetch_related("product__media")
        is_staff = _is_staff_user(info)

        if product_slug:
            qs = qs.filter(product__slug=product_slug)

        if product_id:
            try:
                _, pk_int = from_global_id_or_error(product_id, "Product", raise_error=False)
                actual_id = int(pk_int) if pk_int else int(product_id)
                qs = qs.filter(product_id=actual_id)
            except Exception:
                qs = qs.filter(product_id=product_id)

        if not is_staff:
            user = getattr(getattr(info, "context", None), "user", None)
            auth_user_id = user.id if (user and getattr(user, "is_authenticated", False)) else user_id

            conditions = Q(status=ProductReviewStatus.APPROVED)
            if client_token:
                conditions |= Q(client_token=client_token)
            if auth_user_id:
                try:
                    _, auth_pk = from_global_id_or_error(str(auth_user_id), "User", raise_error=False)
                    actual_user_id = int(auth_pk) if auth_pk else int(auth_user_id)
                    conditions |= Q(user_id=actual_user_id)
                except Exception:
                    conditions |= Q(client_token=str(auth_user_id))
            qs = qs.filter(conditions)

        qs = filter_connection_queryset(qs, kwargs)

        sort_by = kwargs.get("sort_by")
        if sort_by:
            direction = "-" if sort_by.direction == "DESC" else ""
            field = sort_by.field
            if field == "created_at":
                qs = qs.order_by(f"{direction}created_at")
            elif field == "rating":
                qs = qs.order_by(f"{direction}rating", "-created_at")
            elif field == "status":
                qs = qs.order_by(f"{direction}status", "-created_at")
            elif field == "helpful_count":
                qs = qs.order_by(f"{direction}helpful_count", "-created_at")
        else:
            qs = qs.order_by("-created_at")

        return create_connection_slice(qs, info, kwargs, ProductReviewConnection)

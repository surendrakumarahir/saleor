"""GraphQL filter types for product review management."""

import django_filters
from django.db.models import Q

from saleor.graphql.core.doc_category import DOC_CATEGORY_PRODUCTS
from saleor.graphql.core.filters import FilterInputObjectType
from saleor.graphql.core.utils import from_global_id_or_error
from saleor.product.models import ProductReview


class ProductReviewFilter(django_filters.FilterSet):
    """Filters for ProductReview."""

    search = django_filters.CharFilter(method="filter_search")
    status = django_filters.CharFilter(field_name="status")
    rating = django_filters.NumberFilter(field_name="rating")
    is_verified_buyer = django_filters.BooleanFilter(field_name="is_verified_buyer")
    product_slug = django_filters.CharFilter(field_name="product__slug")
    product_id = django_filters.CharFilter(method="filter_product_id")

    class Meta:
        model = ProductReview
        fields = ("search", "status", "rating", "is_verified_buyer", "product_slug", "product_id")

    def filter_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(user_name__icontains=value)
            | Q(user_email__icontains=value)
            | Q(title__icontains=value)
            | Q(content__icontains=value)
            | Q(product__name__icontains=value)
            | Q(product__slug__icontains=value)
        )

    def filter_product_id(self, queryset, _name, value):
        if not value:
            return queryset
        try:
            _, pk = from_global_id_or_error(value, "Product", raise_error=False)
            actual_id = int(pk) if pk else int(value)
            return queryset.filter(product_id=actual_id)
        except Exception:
            return queryset.filter(product_id=value)


class ProductReviewFilterInput(FilterInputObjectType):
    """Filter input for product reviews."""

    class Meta:
        doc_category = DOC_CATEGORY_PRODUCTS
        filterset_class = ProductReviewFilter

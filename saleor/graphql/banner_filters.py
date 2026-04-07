"""GraphQL filters for banner management."""

import django_filters

from saleor.banner.models import Banner, ImageCollection
from saleor.graphql.core.doc_category import DOC_CATEGORY_PRODUCTS
from saleor.graphql.core.filters import FilterInputObjectType


class ImageCollectionFilter(django_filters.FilterSet):
    """Filters for ImageCollection."""

    channel_id = django_filters.CharFilter(field_name="channel__id")
    is_active = django_filters.BooleanFilter(field_name="is_active")
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = ImageCollection
        fields = ("channel_id", "is_active", "name")


class ImageCollectionFilterInput(FilterInputObjectType):
    """Filter input type for image collections."""

    class Meta:
        doc_category = DOC_CATEGORY_PRODUCTS
        filterset_class = ImageCollectionFilter


class BannerFilter(django_filters.FilterSet):
    """Filters for Banner."""

    collection_id = django_filters.CharFilter(
        field_name="image_collection__id"
    )
    channel_id = django_filters.CharFilter(
        field_name="image_collection__channel__id"
    )
    is_active = django_filters.BooleanFilter(field_name="is_active")
    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = Banner
        fields = ("collection_id", "channel_id", "is_active", "title")


class BannerFilterInput(FilterInputObjectType):
    """Filter input type for banners."""

    class Meta:
        doc_category = DOC_CATEGORY_PRODUCTS
        filterset_class = BannerFilter

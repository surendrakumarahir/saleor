"""GraphQL queries and resolvers for banner management."""

import graphene
from django.utils import timezone

from saleor.banner.models import Banner, ImageCollection
from saleor.graphql.banner_filters import (
    BannerFilterInput,
    ImageCollectionFilterInput,
)
from saleor.graphql.banner_types import (
    BannerConnection,
    BannerType,
    ImageCollectionConnection,
    ImageCollectionType,
)
from saleor.graphql.core.connection import (
    create_connection_slice,
    filter_connection_queryset,
)
from saleor.graphql.core.fields import FilterConnectionField, PermissionsField
from saleor.permission.enums import BannerPermissions


class BannerQueries(graphene.ObjectType):
    """Banner management queries."""

    banner = PermissionsField(
        BannerType,
        id=graphene.ID(required=True),
        description="Get a single banner by ID.",
        permissions=[
            BannerPermissions.MANAGE_BANNERS,
        ],
    )

    banners = FilterConnectionField(
        BannerConnection,
        filter=BannerFilterInput(),
        description="Get list of banners.",
    )

    image_collection = PermissionsField(
        ImageCollectionType,
        id=graphene.ID(required=True),
        description="Get a single image collection by ID.",
        permissions=[
            BannerPermissions.MANAGE_BANNERS,
        ],
    )

    image_collections = FilterConnectionField(
        ImageCollectionConnection,
        filter=ImageCollectionFilterInput(),
        description="Get list of image collections.",
    )

    active_banners_by_collection = graphene.List(
        BannerType,
        collection_id=graphene.ID(required=True),
        at_time=graphene.String(),
        description="Get active banners for a collection, respecting scheduling.",
    )

    def resolve_banner(self, info, id):
        """Resolve single banner."""
        try:
            return Banner.objects.get(pk=id)
        except Banner.DoesNotExist:
            return None

    def resolve_banners(self, info, **kwargs):
        """Resolve banners list with filtering."""
        qs = Banner.objects.select_related("image_collection")
        qs = filter_connection_queryset(
            qs, kwargs, allow_replica=info.context.allow_replica
        )
        return create_connection_slice(qs, info, kwargs, BannerConnection)

    def resolve_image_collection(self, info, id):
        """Resolve single image collection."""
        try:
            return ImageCollection.objects.get(pk=id)
        except ImageCollection.DoesNotExist:
            return None

    def resolve_image_collections(self, info, **kwargs):
        """Resolve image collections list with filtering."""
        qs = ImageCollection.objects.all()
        qs = filter_connection_queryset(
            qs, kwargs, allow_replica=info.context.allow_replica
        )
        return create_connection_slice(qs, info, kwargs, ImageCollectionConnection)

    def resolve_active_banners_by_collection(self, info, collection_id, at_time=None):
        """Resolve active banners for a collection at a specific time."""
        if at_time is None:
            at_time = timezone.now()

        try:
            collection = ImageCollection.objects.get(pk=collection_id)
        except ImageCollection.DoesNotExist:
            return []

        banners = collection.banners.filter(is_active=True).order_by("position")
        active_banners = [b for b in banners if b.is_scheduled_active(at_time)]
        return active_banners

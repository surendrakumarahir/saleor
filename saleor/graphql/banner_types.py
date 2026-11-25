"""GraphQL types for banner management."""

import graphene
from django.core.files.storage import default_storage

from saleor.banner.models import Banner, ImageCollection
from saleor.core.utils import build_absolute_uri
from saleor.graphql.core.connection import CountableConnection, create_connection_slice
from saleor.graphql.core.fields import ConnectionField
from saleor.graphql.core.descriptions import ADDED_IN_319


class ImageCollectionType(graphene.ObjectType):
    """GraphQL type for ImageCollection."""

    id = graphene.ID(required=True, description="Image collection ID.")
    name = graphene.String(required=True, description="Collection name.")
    description = graphene.String(description="Collection description.")
    channel_id = graphene.String(required=True, description="Channel ID associated with this collection.")
    is_active = graphene.Boolean(required=True, description="Whether the collection is active.")
    banners = ConnectionField(
        lambda: BannerConnection,
        description="List of banners in this collection.",
    )
    created_at = graphene.String(description="Collection creation timestamp.")
    updated_at = graphene.String(description="Collection last update timestamp.")

    class Meta:
        description = f"Image collection for banners. {ADDED_IN_319}"

    @staticmethod
    def resolve_banners(root: ImageCollection, info, **kwargs):
        qs = root.banners.all().order_by("position", "-created_at")
        return create_connection_slice(qs, info, kwargs, BannerConnection)


class BannerType(graphene.ObjectType):
    """GraphQL type for Banner."""

    id = graphene.ID(required=True, description="Banner ID.")
    title = graphene.String(required=True, description="Banner title.")
    description = graphene.String(description="Banner description.")
    image = graphene.String(description="Banner image URL.")
    alt_text = graphene.String(description="Alternative text for the banner image.")
    link_url = graphene.String(description="URL the banner links to.")
    link_text = graphene.String(description="Text displayed for the banner link.")
    custom_field_1 = graphene.String(description="Custom field 1 for additional data.")
    custom_field_2 = graphene.String(description="Custom field 2 for additional data.")
    custom_field_3 = graphene.String(description="Custom field 3 for additional data.")
    position = graphene.Int(required=True, description="Banner position in collection.")
    is_active = graphene.Boolean(required=True, description="Whether the banner is active.")
    start_date = graphene.String(description="Banner display start date.")
    end_date = graphene.String(description="Banner display end date.")
    created_at = graphene.String(description="Banner creation timestamp.")
    updated_at = graphene.String(description="Banner last update timestamp.")

    class Meta:
        description = f"Banner type. {ADDED_IN_319}"

    @staticmethod
    def resolve_image(root: Banner, _info):
        if not root.image:
            return None

        image_name = str(root.image)
        if image_name.startswith(("http://", "https://", "/media/")):
            return image_name

        return build_absolute_uri(default_storage.url(image_name))


class ImageCollectionConnection(CountableConnection):
    """Connection type for image collections."""

    class Meta:
        node = ImageCollectionType


class BannerConnection(CountableConnection):
    """Connection type for banners."""

    class Meta:
        node = BannerType

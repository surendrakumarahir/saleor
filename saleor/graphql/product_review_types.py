"""GraphQL types for Product Review Management."""

import graphene

from saleor.core.utils import build_absolute_uri
from saleor.graphql.core.connection import CountableConnection
from saleor.product.models import ProductReview, ProductReviewStatus


class ProductReviewStatusEnum(graphene.Enum):
    """Enum representing moderation status of a product review."""

    PENDING = ProductReviewStatus.PENDING
    APPROVED = ProductReviewStatus.APPROVED
    REJECTED = ProductReviewStatus.REJECTED


class ProductReviewType(graphene.ObjectType):
    """GraphQL type for ProductReview."""

    id = graphene.ID(required=True)
    product_id = graphene.ID(required=True)
    product_name = graphene.String(required=True)
    product_slug = graphene.String(required=True)
    product_thumbnail = graphene.String()
    user_name = graphene.String(required=True)
    user_email = graphene.String()
    rating = graphene.Int(required=True)
    title = graphene.String()
    content = graphene.String(required=True)
    status = ProductReviewStatusEnum(required=True)
    is_verified_buyer = graphene.Boolean(required=True)
    images = graphene.List(graphene.String)
    helpful_count = graphene.Int(required=True)
    admin_reply = graphene.String()
    admin_replied_at = graphene.String()
    client_token = graphene.String()
    user_id = graphene.ID()
    created_at = graphene.String(required=True)
    updated_at = graphene.String()

    @staticmethod
    def resolve_id(root: ProductReview, _info):
        return graphene.Node.to_global_id("ProductReview", root.id)

    @staticmethod
    def resolve_product_id(root: ProductReview, _info):
        return graphene.Node.to_global_id("Product", root.product_id) if root.product_id else ""

    @staticmethod
    def resolve_product_name(root: ProductReview, _info):
        return root.product.name if root.product else ""

    @staticmethod
    def resolve_product_slug(root: ProductReview, _info):
        return root.product.slug if root.product else ""

    @staticmethod
    def resolve_product_thumbnail(root: ProductReview, _info):
        if not root.product:
            return None
        media = root.product.media.first()
        if media and media.image:
            return build_absolute_uri(media.image.url)
        return None

    @staticmethod
    def resolve_images(root: ProductReview, _info):
        if isinstance(root.images, list):
            return root.images
        return []

    @staticmethod
    def resolve_user_id(root: ProductReview, _info):
        return graphene.Node.to_global_id("User", root.user_id) if root.user_id else None

    @staticmethod
    def resolve_admin_replied_at(root: ProductReview, _info):
        return root.admin_replied_at.isoformat() if root.admin_replied_at else None

    @staticmethod
    def resolve_created_at(root: ProductReview, _info):
        return root.created_at.isoformat() if root.created_at else None

    @staticmethod
    def resolve_updated_at(root: ProductReview, _info):
        return root.updated_at.isoformat() if root.updated_at else None


class ProductReviewConnection(CountableConnection):
    class Meta:
        node = ProductReviewType

"""GraphQL types for Blog Management."""

import json
import graphene
from django.core.files.storage import default_storage

from saleor.blog.models import (
    BlogAuditLog,
    BlogAuthor,
    BlogCategory,
    BlogPost,
    BlogPostFAQ,
    BlogPostRevision,
    BlogPostStatus,
    BlogRedirect,
    BlogTag,
)
from saleor.core.utils import build_absolute_uri
from saleor.graphql.core.connection import CountableConnection, create_connection_slice
from saleor.graphql.core.descriptions import ADDED_IN_319
from saleor.graphql.core.scalars import JSON


def _resolve_image_url(image_field):
    if not image_field:
        return None
    image_name = str(image_field)
    if image_name.startswith(("http://", "https://", "/media/")):
        return image_name
    return build_absolute_uri(default_storage.url(image_name))


class BlogPostStatusEnum(graphene.Enum):
    """Enum representing publication status of a blog post."""

    DRAFT = BlogPostStatus.DRAFT
    IN_REVIEW = BlogPostStatus.IN_REVIEW
    SCHEDULED = BlogPostStatus.SCHEDULED
    PUBLISHED = BlogPostStatus.PUBLISHED
    ARCHIVED = BlogPostStatus.ARCHIVED


class BlogAuthorType(graphene.ObjectType):
    """GraphQL type for BlogAuthor."""

    id = graphene.ID(required=True)
    display_name = graphene.String(required=True)
    slug = graphene.String(required=True)
    bio = graphene.String()
    avatar = graphene.String()
    designation = graphene.String()
    social_links = JSON()
    created_at = graphene.String()
    updated_at = graphene.String()

    @staticmethod
    def resolve_avatar(root: BlogAuthor, _info):
        return _resolve_image_url(root.avatar)

    @staticmethod
    def resolve_created_at(root: BlogAuthor, _info):
        return root.created_at.isoformat() if root.created_at else None

    @staticmethod
    def resolve_updated_at(root: BlogAuthor, _info):
        return root.updated_at.isoformat() if root.updated_at else None


class BlogCategoryType(graphene.ObjectType):
    """GraphQL type for BlogCategory with hierarchical nesting."""

    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    slug = graphene.String(required=True)
    description = graphene.String()
    parent_id = graphene.ID()
    parent = graphene.Field(lambda: BlogCategoryType)
    children = graphene.List(lambda: BlogCategoryType)
    seo_title = graphene.String()
    seo_description = graphene.String()
    badge_color = graphene.String()
    is_active = graphene.Boolean(required=True)
    post_count = graphene.Int()
    created_at = graphene.String()
    updated_at = graphene.String()

    @staticmethod
    def resolve_parent_id(root: BlogCategory, _info):
        return str(root.parent_id) if root.parent_id else None

    @staticmethod
    def resolve_parent(root: BlogCategory, _info):
        return root.parent

    @staticmethod
    def resolve_children(root: BlogCategory, _info):
        return root.children.filter(is_active=True).order_by("name")

    @staticmethod
    def resolve_post_count(root: BlogCategory, _info):
        return root.posts.filter(status=BlogPostStatus.PUBLISHED).count()

    @staticmethod
    def resolve_created_at(root: BlogCategory, _info):
        return root.created_at.isoformat() if root.created_at else None

    @staticmethod
    def resolve_updated_at(root: BlogCategory, _info):
        return root.updated_at.isoformat() if root.updated_at else None


class BlogTagType(graphene.ObjectType):
    """GraphQL type for BlogTag."""

    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    slug = graphene.String(required=True)
    description = graphene.String()
    post_count = graphene.Int()
    created_at = graphene.String()
    updated_at = graphene.String()

    @staticmethod
    def resolve_post_count(root: BlogTag, _info):
        return root.posts.filter(status=BlogPostStatus.PUBLISHED).count()

    @staticmethod
    def resolve_created_at(root: BlogTag, _info):
        return root.created_at.isoformat() if root.created_at else None

    @staticmethod
    def resolve_updated_at(root: BlogTag, _info):
        return root.updated_at.isoformat() if root.updated_at else None


class BlogPostRevisionType(graphene.ObjectType):
    """Snapshot revision of a blog post."""

    id = graphene.ID(required=True)
    revision_number = graphene.Int(required=True)
    title = graphene.String(required=True)
    slug = graphene.String(required=True)
    excerpt = graphene.String()
    content = graphene.String()
    content_html = graphene.String()
    created_by_name = graphene.String()
    created_at = graphene.String()

    @staticmethod
    def resolve_created_by_name(root: BlogPostRevision, _info):
        if root.created_by:
            return root.created_by.get_full_name() or root.created_by.email
        return None

    @staticmethod
    def resolve_created_at(root: BlogPostRevision, _info):
        return root.created_at.isoformat() if root.created_at else None


class BlogPostFAQType(graphene.ObjectType):
    """GraphQL type for BlogPostFAQ."""

    id = graphene.ID(required=True)
    question = graphene.String(required=True)
    answer = graphene.String(required=True)
    sort_order = graphene.Int()
    created_at = graphene.String()
    updated_at = graphene.String()

    @staticmethod
    def resolve_created_at(root: BlogPostFAQ, _info):
        return root.created_at.isoformat() if root.created_at else None

    @staticmethod
    def resolve_updated_at(root: BlogPostFAQ, _info):
        return root.updated_at.isoformat() if root.updated_at else None


class BlogPostType(graphene.ObjectType):
    """Comprehensive GraphQL type for BlogPost."""

    id = graphene.ID(required=True)
    title = graphene.String(required=True)
    slug = graphene.String(required=True)
    excerpt = graphene.String()
    content = graphene.String()
    content_html = graphene.String()
    status = BlogPostStatusEnum(required=True)
    author = graphene.Field(BlogAuthorType)
    primary_category = graphene.Field(BlogCategoryType)
    categories = graphene.List(BlogCategoryType)
    tags = graphene.List(BlogTagType)
    featured_image = graphene.String()
    featured_image_alt = graphene.String()
    featured_image_caption = graphene.String()
    seo_title = graphene.String()
    seo_description = graphene.String()
    canonical_url = graphene.String()
    robots_index = graphene.Boolean()
    robots_follow = graphene.Boolean()
    og_title = graphene.String()
    og_description = graphene.String()
    og_image = graphene.String()
    is_featured = graphene.Boolean()
    reading_time_minutes = graphene.Int()
    allow_comments = graphene.Boolean()
    published_at = graphene.String()
    scheduled_at = graphene.String()
    created_at = graphene.String()
    updated_at = graphene.String()
    created_by_id = graphene.ID()
    created_by_name = graphene.String()
    updated_by_id = graphene.ID()
    updated_by_name = graphene.String()
    revision_number = graphene.Int()
    recommended_books = JSON()
    table_of_contents = JSON()
    product_collections = JSON()
    faqs = graphene.List(BlogPostFAQType)

    @staticmethod
    def resolve_faqs(root: BlogPost, _info):
        return root.faqs.all().order_by("sort_order", "id")

    @staticmethod
    def resolve_featured_image(root: BlogPost, _info):
        return _resolve_image_url(root.featured_image)

    @staticmethod
    def resolve_og_image(root: BlogPost, _info):
        return _resolve_image_url(root.og_image)

    @staticmethod
    def resolve_categories(root: BlogPost, _info):
        return root.categories.all()

    @staticmethod
    def resolve_tags(root: BlogPost, _info):
        return root.tags.all()

    @staticmethod
    def resolve_published_at(root: BlogPost, _info):
        return root.published_at.isoformat() if root.published_at else None

    @staticmethod
    def resolve_scheduled_at(root: BlogPost, _info):
        return root.scheduled_at.isoformat() if root.scheduled_at else None

    @staticmethod
    def resolve_created_at(root: BlogPost, _info):
        return root.created_at.isoformat() if root.created_at else None

    @staticmethod
    def resolve_updated_at(root: BlogPost, _info):
        return root.updated_at.isoformat() if root.updated_at else None

    @staticmethod
    def resolve_created_by_name(root: BlogPost, _info):
        if root.created_by:
            return root.created_by.get_full_name() or root.created_by.email
        return None

    @staticmethod
    def resolve_updated_by_name(root: BlogPost, _info):
        if root.updated_by:
            return root.updated_by.get_full_name() or root.updated_by.email
        return None


class BlogRedirectType(graphene.ObjectType):
    """GraphQL type for BlogRedirect."""

    id = graphene.ID(required=True)
    old_slug = graphene.String(required=True)
    destination_slug = graphene.String(required=True)
    is_permanent = graphene.Boolean(required=True)
    created_at = graphene.String()

    @staticmethod
    def resolve_created_at(root: BlogRedirect, _info):
        return root.created_at.isoformat() if root.created_at else None


class BlogPostConnection(CountableConnection):
    class Meta:
        node = BlogPostType


class BlogCategoryConnection(CountableConnection):
    class Meta:
        node = BlogCategoryType


class BlogTagConnection(CountableConnection):
    class Meta:
        node = BlogTagType


class BlogAuthorConnection(CountableConnection):
    class Meta:
        node = BlogAuthorType

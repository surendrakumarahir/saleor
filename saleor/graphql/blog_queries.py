"""GraphQL queries and resolvers for blog management."""

import graphene
from django.utils import timezone
from django.db.models import Q

from saleor.blog.models import (
    BlogAuthor,
    BlogCategory,
    BlogPost,
    BlogPostRevision,
    BlogPostStatus,
    BlogRedirect,
    BlogTag,
)
from saleor.graphql.blog_filters import (
    BlogCategoryFilterInput,
    BlogPostFilterInput,
)
from saleor.graphql.blog_sorters import BlogPostSortingInput
from saleor.graphql.blog_types import (
    BlogAuthorConnection,
    BlogAuthorType,
    BlogCategoryConnection,
    BlogCategoryType,
    BlogPostConnection,
    BlogPostRevisionType,
    BlogPostType,
    BlogTagConnection,
    BlogTagType,
)
from saleor.graphql.core.connection import (
    create_connection_slice,
    filter_connection_queryset,
)
from saleor.graphql.core.fields import FilterConnectionField
from saleor.graphql.core.utils import from_global_id_or_error


def _is_staff_user(info):
    context = getattr(info, "context", None)
    if not context:
        return False
    user = getattr(context, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    is_staff = getattr(user, "is_staff", False)
    has_perm = user.has_perm("blog.manage_blog") if hasattr(user, "has_perm") else False
    return bool(is_staff or has_perm)


class BlogQueries(graphene.ObjectType):
    """Blog queries for storefront and admin dashboard."""

    blog_post = graphene.Field(
        BlogPostType,
        id=graphene.ID(description="Blog post ID."),
        slug=graphene.String(description="Blog post slug."),
        description="Retrieve a single blog post by ID or slug.",
    )

    blog_posts = FilterConnectionField(
        BlogPostConnection,
        filter=BlogPostFilterInput(),
        sort_by=BlogPostSortingInput(),
        description="Retrieve a list of blog posts.",
    )

    blog_category = graphene.Field(
        BlogCategoryType,
        id=graphene.ID(description="Category ID."),
        slug=graphene.String(description="Category slug."),
        description="Retrieve a single category by ID or slug.",
    )

    blog_categories = FilterConnectionField(
        BlogCategoryConnection,
        filter=BlogCategoryFilterInput(),
        description="Retrieve a list of blog categories.",
    )

    blog_tag = graphene.Field(
        BlogTagType,
        id=graphene.ID(description="Tag ID."),
        slug=graphene.String(description="Tag slug."),
        description="Retrieve a single tag by ID or slug.",
    )

    blog_tags = FilterConnectionField(
        BlogTagConnection,
        description="Retrieve a list of blog tags.",
    )

    blog_author = graphene.Field(
        BlogAuthorType,
        id=graphene.ID(description="Author ID."),
        slug=graphene.String(description="Author slug."),
        description="Retrieve a single author by ID or slug.",
    )

    blog_authors = FilterConnectionField(
        BlogAuthorConnection,
        description="Retrieve a list of blog authors.",
    )

    blog_post_revisions = graphene.List(
        BlogPostRevisionType,
        post_id=graphene.ID(description="Post ID."),
        post_slug=graphene.String(description="Post slug."),
        description="Retrieve revisions for a blog post (staff only).",
    )

    blog_related_posts = graphene.List(
        BlogPostType,
        slug=graphene.String(required=True, description="Current post slug to exclude."),
        category_slug=graphene.String(description="Category slug to filter by."),
        limit=graphene.Int(default_value=3, description="Maximum number of posts to return."),
        description="Retrieve related published posts.",
    )

    def resolve_blog_post(self, info, id=None, slug=None):
        qs = BlogPost.objects.select_related("author", "primary_category").prefetch_related("categories", "tags")
        is_staff = _is_staff_user(info)

        if not is_staff:
            now = timezone.now()
            qs = qs.filter(
                Q(status=BlogPostStatus.PUBLISHED, published_at__lte=now)
                | Q(status=BlogPostStatus.PUBLISHED, published_at__isnull=True)
            )

        post = None
        if id:
            try:
                _, pk_int = from_global_id_or_error(id, "BlogPost", raise_error=False)
                lookup_id = pk_int if pk_int else id
                post = qs.filter(pk=lookup_id).first()
            except Exception:
                post = qs.filter(pk=id).first()
        elif slug:
            post = qs.filter(slug=slug).first()
            if not post:
                # Check redirect mapping
                redirect = BlogRedirect.objects.filter(old_slug=slug).first()
                if redirect:
                    post = qs.filter(slug=redirect.destination_slug).first()

        return post

    def resolve_blog_posts(self, info, **kwargs):
        qs = BlogPost.objects.select_related("author", "primary_category").prefetch_related("categories", "tags")
        is_staff = _is_staff_user(info)

        if not is_staff:
            now = timezone.now()
            qs = qs.filter(
                Q(status=BlogPostStatus.PUBLISHED, published_at__lte=now)
                | Q(status=BlogPostStatus.PUBLISHED, published_at__isnull=True)
            )

        qs = filter_connection_queryset(qs, kwargs)

        sort_by = kwargs.get("sort_by")
        if sort_by:
            direction = "-" if sort_by.direction == "DESC" else ""
            field = sort_by.field
            if field == "published_at":
                qs = qs.order_by(f"{direction}published_at", f"{direction}created_at")
            elif field == "created_at":
                qs = qs.order_by(f"{direction}created_at")
            elif field == "updated_at":
                qs = qs.order_by(f"{direction}updated_at")
            elif field == "title":
                qs = qs.order_by(f"{direction}title")
            elif field == "reading_time":
                qs = qs.order_by(f"{direction}reading_time_minutes")
        else:
            qs = qs.order_by("-is_featured", "-published_at", "-created_at")

        return create_connection_slice(qs, info, kwargs, BlogPostConnection)

    def resolve_blog_category(self, info, id=None, slug=None):
        if id:
            try:
                _, pk_int = from_global_id_or_error(id, "BlogCategory", raise_error=False)
                lookup_id = pk_int if pk_int else id
                return BlogCategory.objects.filter(pk=lookup_id).first()
            except Exception:
                return BlogCategory.objects.filter(pk=id).first()
        if slug:
            return BlogCategory.objects.filter(slug=slug).first()
        return None

    def resolve_blog_categories(self, info, **kwargs):
        qs = BlogCategory.objects.all().order_by("name")
        qs = filter_connection_queryset(qs, kwargs)
        return create_connection_slice(qs, info, kwargs, BlogCategoryConnection)

    def resolve_blog_tag(self, info, id=None, slug=None):
        if id:
            try:
                _, pk_int = from_global_id_or_error(id, "BlogTag", raise_error=False)
                lookup_id = pk_int if pk_int else id
                return BlogTag.objects.filter(pk=lookup_id).first()
            except Exception:
                return BlogTag.objects.filter(pk=id).first()
        if slug:
            return BlogTag.objects.filter(slug=slug).first()
        return None

    def resolve_blog_tags(self, info, **kwargs):
        qs = BlogTag.objects.all().order_by("name")
        return create_connection_slice(qs, info, kwargs, BlogTagConnection)

    def resolve_blog_author(self, info, id=None, slug=None):
        if id:
            try:
                _, pk_int = from_global_id_or_error(id, "BlogAuthor", raise_error=False)
                lookup_id = pk_int if pk_int else id
                return BlogAuthor.objects.filter(pk=lookup_id).first()
            except Exception:
                return BlogAuthor.objects.filter(pk=id).first()
        if slug:
            return BlogAuthor.objects.filter(slug=slug).first()
        return None

    def resolve_blog_authors(self, info, **kwargs):
        qs = BlogAuthor.objects.all().order_by("display_name")
        return create_connection_slice(qs, info, kwargs, BlogAuthorConnection)

    def resolve_blog_post_revisions(self, info, post_id=None, post_slug=None):
        if not _is_staff_user(info):
            return []

        qs = BlogPostRevision.objects.select_related("created_by")
        if post_id:
            try:
                _, pk_int = from_global_id_or_error(post_id, "BlogPost", raise_error=False)
                lookup_id = pk_int if pk_int else post_id
                qs = qs.filter(post_id=lookup_id)
            except Exception:
                qs = qs.filter(post_id=post_id)
        elif post_slug:
            qs = qs.filter(post__slug=post_slug)
        else:
            return []

        return qs.order_by("-revision_number")

    def resolve_blog_related_posts(self, info, slug, category_slug=None, limit=3):
        now = timezone.now()
        qs = BlogPost.objects.filter(
            Q(status=BlogPostStatus.PUBLISHED, published_at__lte=now)
            | Q(status=BlogPostStatus.PUBLISHED, published_at__isnull=True)
        ).exclude(slug=slug).select_related("author", "primary_category")

        if category_slug and category_slug != "all":
            category_qs = qs.filter(
                Q(primary_category__slug=category_slug) | Q(categories__slug=category_slug)
            ).distinct()
            if category_qs.exists():
                return list(category_qs.order_by("-published_at")[:limit])

        return list(qs.order_by("-is_featured", "-published_at")[:limit])

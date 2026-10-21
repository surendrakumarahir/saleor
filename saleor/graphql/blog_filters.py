"""GraphQL filter types for blog management."""

import django_filters
from django.db.models import Q

from saleor.blog.models import BlogCategory, BlogPost
from saleor.graphql.core.doc_category import DOC_CATEGORY_PAGES
from saleor.graphql.core.filters import FilterInputObjectType


class BlogPostFilter(django_filters.FilterSet):
    """Filters for BlogPost."""

    search = django_filters.CharFilter(method="filter_search")
    status = django_filters.CharFilter(field_name="status")
    category_slug = django_filters.CharFilter(method="filter_category")
    tag_slug = django_filters.CharFilter(field_name="tags__slug")
    author_slug = django_filters.CharFilter(field_name="author__slug")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = BlogPost
        fields = ("search", "status", "category_slug", "tag_slug", "author_slug", "is_featured")

    def filter_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) | Q(excerpt__icontains=value) | Q(slug__icontains=value)
        )

    def filter_category(self, queryset, _name, value):
        if not value or value == "all":
            return queryset
        return queryset.filter(
            Q(primary_category__slug=value) | Q(categories__slug=value)
        ).distinct()


class BlogPostFilterInput(FilterInputObjectType):
    """Filter input for blog posts."""

    class Meta:
        doc_category = DOC_CATEGORY_PAGES
        filterset_class = BlogPostFilter


class BlogCategoryFilter(django_filters.FilterSet):
    """Filters for BlogCategory."""

    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = BlogCategory
        fields = ("search", "is_active")


class BlogCategoryFilterInput(FilterInputObjectType):
    """Filter input for blog categories."""

    class Meta:
        doc_category = DOC_CATEGORY_PAGES
        filterset_class = BlogCategoryFilter

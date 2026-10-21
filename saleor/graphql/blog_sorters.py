"""GraphQL sorter types for blog management."""

from saleor.graphql.core.doc_category import DOC_CATEGORY_PAGES
from saleor.graphql.core.types import BaseEnum, SortInputObjectType


class BlogPostSortField(BaseEnum):
    TITLE = ["title", "slug"]
    PUBLISHED_AT = ["published_at", "title"]
    CREATED_AT = ["created_at", "title"]
    UPDATED_AT = ["updated_at", "title"]
    READING_TIME = ["reading_time_minutes", "title"]

    class Meta:
        doc_category = DOC_CATEGORY_PAGES

    @property
    def description(self):
        return f"Sort blog posts by {self.name.lower().replace('_', ' ')}."


class BlogPostSortingInput(SortInputObjectType):
    class Meta:
        doc_category = DOC_CATEGORY_PAGES
        sort_enum = BlogPostSortField
        type_name = "blog posts"

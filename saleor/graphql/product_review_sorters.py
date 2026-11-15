"""GraphQL sorting types for product review management."""

from saleor.graphql.core.doc_category import DOC_CATEGORY_PRODUCTS
from saleor.graphql.core.types import BaseEnum, SortInputObjectType


class ProductReviewSortField(BaseEnum):
    CREATED_AT = ["created_at"]
    RATING = ["rating", "created_at"]
    STATUS = ["status", "created_at"]
    HELPFUL_COUNT = ["helpful_count", "created_at"]

    class Meta:
        doc_category = DOC_CATEGORY_PRODUCTS

    @property
    def description(self):
        return f"Sort product reviews by {self.name.lower().replace('_', ' ')}."


class ProductReviewSortingInput(SortInputObjectType):
    class Meta:
        doc_category = DOC_CATEGORY_PRODUCTS
        sort_enum = ProductReviewSortField
        type_name = "product reviews"

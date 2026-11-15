"""GraphQL error types for Product Review management."""

import graphene


class ProductReviewErrorCode(graphene.Enum):
    """Possible errors in product review operations."""

    NOT_FOUND = "not_found"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_RATING = "invalid_rating"
    INVALID_STATUS = "invalid_status"
    PERMISSION_DENIED = "permission_denied"
    ALREADY_REVIEWED = "already_reviewed"
    GRAPHQL_ERROR = "graphql_error"


class ProductReviewError(graphene.ObjectType):
    """Represents an error in product review operations."""

    code = ProductReviewErrorCode(required=True, description="Error code.")
    message = graphene.String(description="Error message.")
    field = graphene.String(description="Name of the field where error occurred.")

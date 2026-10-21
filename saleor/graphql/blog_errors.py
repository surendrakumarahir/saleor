"""GraphQL error types for blog management."""

import graphene


class BlogErrorCode(graphene.Enum):
    """Possible errors in blog operations."""

    NOT_FOUND = "not_found"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_SLUG = "invalid_slug"
    SLUG_ALREADY_EXISTS = "slug_already_exists"
    INVALID_STATUS = "invalid_status"
    INVALID_PARENT = "invalid_parent"
    CIRCULAR_CATEGORY_PARENT = "circular_category_parent"
    PERMISSION_DENIED = "permission_denied"
    INVALID_DATE = "invalid_date"
    REVISION_NOT_FOUND = "revision_not_found"
    MEDIA_UPLOAD_ERROR = "media_upload_error"
    GRAPHQL_ERROR = "graphql_error"


class BlogError(graphene.ObjectType):
    """Represents an error in blog operations."""

    code = BlogErrorCode(required=True, description="Error code.")
    message = graphene.String(description="Error message.")
    field = graphene.String(description="Name of the field where error occurred.")

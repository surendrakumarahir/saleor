"""Error codes for blog management."""

from enum import Enum


class BlogErrorCode(Enum):
    """Error codes for blog GraphQL operations."""

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
    GRAPHQL_ERROR = "graphql_error"

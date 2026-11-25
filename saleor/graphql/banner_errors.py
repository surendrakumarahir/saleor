"""GraphQL error types for banner management."""

import graphene


class BannerErrorCode(graphene.Enum):
    """Possible errors in banner management."""

    INVALID_BANNER_DATA = "invalid_banner_data"
    INVALID_COLLECTION_DATA = "invalid_collection_data"
    COLLECTION_NOT_FOUND = "collection_not_found"
    BANNER_NOT_FOUND = "banner_not_found"
    INVALID_DATE_RANGE = "invalid_date_range"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    IMAGE_UPLOAD_ERROR = "image_upload_error"
    IMAGE_NOT_FOUND = "image_not_found"
    IMAGE_IN_USE = "image_in_use"


class BannerError(graphene.ObjectType):
    """Represents an error in banner operations."""

    code = BannerErrorCode(required=True, description="Error code.")
    message = graphene.String(description="Error message.")
    field = graphene.String(description="Name of the field where error occurred.")

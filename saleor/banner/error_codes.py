"""Error codes for banner management."""

from enum import Enum


class BannerErrorCode(str, Enum):
    """Enumeration of banner error codes."""

    INVALID_BANNER_DATA = "invalid_banner_data"
    INVALID_COLLECTION_DATA = "invalid_collection_data"
    COLLECTION_NOT_FOUND = "collection_not_found"
    BANNER_NOT_FOUND = "banner_not_found"
    INVALID_DATE_RANGE = "invalid_date_range"
    REQUIRED_FIELD_MISSING = "required_field_missing"

"""Permission enums for banner management."""

from enum import Enum


class BannerPermissions(Enum):
    """Banner management permissions."""

    MANAGE_BANNERS = "banner.manage_banners"

    @property
    def codename(self):
        return self.value.split(".")[1]

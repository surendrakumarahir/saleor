"""Permission enums for blog management."""

from enum import Enum


class BlogPermissions(Enum):
    """Blog management permissions."""

    MANAGE_BLOG = "blog.manage_blog"
    PUBLISH_BLOG = "blog.publish_blog"

    @property
    def codename(self):
        return self.value.split(".")[1]

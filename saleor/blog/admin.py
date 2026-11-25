"""Django admin registration for blog management."""

from django.contrib import admin
from .models import (
    BlogAuthor,
    BlogCategory,
    BlogComment,
    BlogPost,
    BlogPostFAQ,
    BlogTag,
)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author_name",
        "author_email",
        "post",
        "status",
        "is_pinned",
        "created_at",
    )
    list_filter = ("status", "is_pinned", "created_at", "post")
    search_fields = ("author_name", "author_email", "content", "post__title")
    list_editable = ("status", "is_pinned")
    actions = ["approve_comments", "reject_comments"]

    @admin.action(description="Mark selected comments as Approved")
    def approve_comments(self, request, queryset):
        queryset.update(status="APPROVED")

    @admin.action(description="Mark selected comments as Rejected")
    def reject_comments(self, request, queryset):
        queryset.update(status="REJECTED")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "author", "primary_category", "published_at")
    list_filter = ("status", "primary_category", "published_at")
    search_fields = ("title", "slug", "content")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(BlogAuthor)
class BlogAuthorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "slug", "designation")
    search_fields = ("display_name", "slug")


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(BlogTag)
class BlogTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")

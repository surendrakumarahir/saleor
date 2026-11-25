"""Django admin configuration for banner management."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Banner, ImageCollection


class BannerInline(admin.TabularInline):
    """Inline admin for banners within image collection."""

    model = Banner
    extra = 1
    fields = (
        "title",
        "position",
        "is_active",
        "start_date",
        "end_date",
        "image_preview",
    )
    readonly_fields = ("image_preview", "created_at", "updated_at")

    def image_preview(self, obj):
        """Display image preview in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" />',
                obj.image.url,
            )
        return "No image"

    image_preview.short_description = "Image Preview"


@admin.register(ImageCollection)
class ImageCollectionAdmin(admin.ModelAdmin):
    """Admin configuration for ImageCollection model."""

    list_display = (
        "name",
        "channel",
        "is_active",
        "banner_count",
        "created_at",
    )
    list_filter = ("is_active", "channel", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [BannerInline]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "description", "channel", "is_active")
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def banner_count(self, obj):
        """Display count of banners in collection."""
        return obj.banners.count()

    banner_count.short_description = "Number of Banners"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """Admin configuration for Banner model."""

    list_display = (
        "title",
        "image_collection",
        "position",
        "is_active",
        "is_scheduled",
        "image_preview",
        "created_at",
    )
    list_filter = (
        "is_active",
        "image_collection__channel",
        "image_collection",
        "created_at",
    )
    search_fields = ("title", "description", "alt_text")
    readonly_fields = (
        "image_preview",
        "created_at",
        "updated_at",
    )
    ordering = ("position",)

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "title",
                    "description",
                    "image_collection",
                    "position",
                )
            },
        ),
        (
            "Image",
            {
                "fields": ("image", "image_preview", "alt_text"),
            },
        ),
        (
            "Links",
            {
                "fields": ("link_url", "link_text"),
                "classes": ("collapse",),
            },
        ),
        (
            "Custom Fields",
            {
                "fields": (
                    "custom_field_1",
                    "custom_field_2",
                    "custom_field_3",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Key-Value Storage",
            {
                "fields": ("key_values",),
                "classes": ("collapse",),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active",),
            },
        ),
        (
            "Scheduling",
            {
                "fields": ("start_date", "end_date"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def image_preview(self, obj):
        """Display image preview in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="150" />',
                obj.image.url,
            )
        return "No image"

    image_preview.short_description = "Image Preview"

    def is_scheduled(self, obj):
        """Check if banner is scheduled."""
        from django.utils import timezone

        if obj.start_date or obj.end_date:
            now = timezone.now()
            is_active = obj.is_scheduled_active(now)
            status = "✓ Active" if is_active else "✗ Inactive"
            return format_html(
                '<span style="color: {};">{}</span>',
                "green" if is_active else "red",
                status,
            )
        return format_html('<span style="color: blue;">No Schedule</span>')

    is_scheduled.short_description = "Schedule Status"

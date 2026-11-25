"""Models for banner management system."""

from django.db import models
from django.utils import timezone

from ..channel.models import Channel


class ImageCollection(models.Model):
    """Collection of banners grouped by channel."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="banner_collections"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Image Collection"
        verbose_name_plural = "Image Collections"
        unique_together = ("name", "channel")

    def __str__(self):
        return f"{self.name} ({self.channel.slug})"


class Banner(models.Model):
    """Banner model for managing promotional banners across channels."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="banners/")
    alt_text = models.CharField(max_length=255, blank=True)
    link_url = models.URLField(blank=True, null=True)
    link_text = models.CharField(max_length=100, blank=True)
    custom_field_1 = models.CharField(max_length=255, blank=True)
    custom_field_2 = models.CharField(max_length=255, blank=True)
    custom_field_3 = models.CharField(max_length=255, blank=True)
    key_values = models.JSONField(default=dict, blank=True)
    image_collection = models.ForeignKey(
        ImageCollection, on_delete=models.CASCADE, related_name="banners"
    )
    position = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "-created_at")
        verbose_name = "Banner"
        verbose_name_plural = "Banners"
        indexes = [
            models.Index(fields=("image_collection", "position")),
            models.Index(fields=("is_active", "start_date", "end_date")),
        ]

    def __str__(self):
        return self.title

    def is_scheduled_active(self, at_time=None):
        """Check if banner is active based on scheduling.

        Args:
            at_time: datetime to check against. If None, uses current time.

        Returns:
            bool: True if banner is active and within scheduled time range.
        """
        if not self.is_active:
            return False

        if at_time is None:
            at_time = timezone.now()

        if self.start_date and at_time < self.start_date:
            return False

        if self.end_date and at_time > self.end_date:
            return False

        return True

"""Utility functions for banner management."""

from django.utils import timezone
from typing import List, Optional
from datetime import datetime

from .models import Banner, ImageCollection


def get_active_banners_for_collection(
    collection_id: int, at_time: Optional[datetime] = None
) -> List[Banner]:
    """
    Get all active banners for a collection at a specific time.

    Args:
        collection_id: ID of the ImageCollection
        at_time: DateTime to check against. Defaults to now.

    Returns:
        List of Banner objects that are currently active
    """
    if at_time is None:
        at_time = timezone.now()

    try:
        collection = ImageCollection.objects.get(pk=collection_id)
    except ImageCollection.DoesNotExist:
        return []

    banners = collection.banners.filter(is_active=True).order_by("position")
    active_banners = [b for b in banners if b.is_scheduled_active(at_time)]
    return active_banners


def get_banners_by_channel(channel_id: int) -> List[Banner]:
    """
    Get all active banners for a specific channel.

    Args:
        channel_id: ID of the Channel

    Returns:
        List of Banner objects for the channel
    """
    return Banner.objects.filter(
        image_collection__channel_id=channel_id,
        is_active=True,
    ).select_related("image_collection")


def reorder_banners(collection_id: int, banner_order: List[int]) -> None:
    """
    Reorder banners in a collection.

    Args:
        collection_id: ID of the ImageCollection
        banner_order: List of banner IDs in desired order
    """
    for position, banner_id in enumerate(banner_order):
        Banner.objects.filter(
            pk=banner_id,
            image_collection_id=collection_id,
        ).update(position=position)


def get_expired_banners() -> List[Banner]:
    """Get all banners that have expired."""
    now = timezone.now()
    return Banner.objects.filter(
        end_date__lt=now,
        is_active=True,
    )


def get_upcoming_banners() -> List[Banner]:
    """Get all banners that haven't started yet."""
    now = timezone.now()
    return Banner.objects.filter(
        start_date__gt=now,
        is_active=True,
    )


def deactivate_expired_banners() -> int:
    """
    Deactivate all expired banners.

    Returns:
        Number of banners deactivated
    """
    expired = get_expired_banners()
    count = expired.update(is_active=False)
    return count


def get_collection_banners_with_stats(collection_id: int) -> dict:
    """
    Get statistics about a collection's banners.

    Returns:
        Dictionary with banner statistics
    """
    try:
        collection = ImageCollection.objects.get(pk=collection_id)
    except ImageCollection.DoesNotExist:
        return {}

    banners = collection.banners.all()
    now = timezone.now()

    return {
        "collection": collection,
        "total": banners.count(),
        "active": banners.filter(is_active=True).count(),
        "inactive": banners.filter(is_active=False).count(),
        "scheduled": banners.filter(start_date__isnull=False).count(),
        "currently_showing": len(get_active_banners_for_collection(collection_id, now)),
        "expired": banners.filter(end_date__lt=now, is_active=True).count(),
        "upcoming": banners.filter(start_date__gt=now, is_active=True).count(),
    }

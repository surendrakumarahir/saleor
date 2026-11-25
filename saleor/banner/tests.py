"""Tests for banner models and utilities."""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase

from saleor.banner.models import Banner, ImageCollection
from saleor.banner.utils import (
    get_active_banners_for_collection,
    get_expired_banners,
    get_upcoming_banners,
    reorder_banners,
)


@pytest.mark.django_db
class TestBannerModel(TestCase):
    """Test cases for Banner model."""

    def setUp(self):
        """Set up test fixtures."""
        from saleor.channel.models import Channel

        self.channel = Channel.objects.create(
            name="Test Channel",
            slug="test-channel",
            is_active=True,
        )
        self.collection = ImageCollection.objects.create(
            name="Test Collection",
            channel=self.channel,
            is_active=True,
        )

    def test_banner_creation(self):
        """Test basic banner creation."""
        banner = Banner.objects.create(
            title="Test Banner",
            description="Test Description",
            image="test.jpg",
            alt_text="Test Alt",
            image_collection=self.collection,
            position=0,
        )

        assert banner.title == "Test Banner"
        assert banner.is_active is True
        assert banner.is_scheduled_active() is True

    def test_banner_is_scheduled_active_future_start(self):
        """Test banner is inactive when start date is in future."""
        future_date = timezone.now() + timedelta(days=1)
        banner = Banner.objects.create(
            title="Test Banner",
            image="test.jpg",
            image_collection=self.collection,
            start_date=future_date,
            position=0,
        )

        assert banner.is_scheduled_active() is False

    def test_banner_is_scheduled_active_past_end(self):
        """Test banner is inactive when end date is in past."""
        past_date = timezone.now() - timedelta(days=1)
        banner = Banner.objects.create(
            title="Test Banner",
            image="test.jpg",
            image_collection=self.collection,
            end_date=past_date,
            position=0,
        )

        assert banner.is_scheduled_active() is False

    def test_banner_is_scheduled_active_within_range(self):
        """Test banner is active within scheduled range."""
        now = timezone.now()
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)

        banner = Banner.objects.create(
            title="Test Banner",
            image="test.jpg",
            image_collection=self.collection,
            start_date=start,
            end_date=end,
            position=0,
        )

        assert banner.is_scheduled_active() is True

    def test_banner_key_values_storage(self):
        """Test key-value storage in banner."""
        banner = Banner.objects.create(
            title="Test Banner",
            image="test.jpg",
            image_collection=self.collection,
            key_values={
                "discount_percent": "50",
                "campaign_id": "summer_2024",
                "tags": ["sale", "featured"],
            },
            position=0,
        )

        assert banner.key_values["discount_percent"] == "50"
        assert "summer_2024" in banner.key_values.values()

    def test_banner_custom_fields(self):
        """Test custom fields storage."""
        banner = Banner.objects.create(
            title="Test Banner",
            image="test.jpg",
            image_collection=self.collection,
            custom_field_1="Custom Value 1",
            custom_field_2="Custom Value 2",
            custom_field_3="Custom Value 3",
            position=0,
        )

        assert banner.custom_field_1 == "Custom Value 1"
        assert banner.custom_field_2 == "Custom Value 2"
        assert banner.custom_field_3 == "Custom Value 3"

    def test_banner_link_data(self):
        """Test link URL and text."""
        banner = Banner.objects.create(
            title="Test Banner",
            image="test.jpg",
            image_collection=self.collection,
            link_url="https://example.com/sale",
            link_text="Shop Now",
            position=0,
        )

        assert banner.link_url == "https://example.com/sale"
        assert banner.link_text == "Shop Now"


@pytest.mark.django_db
class TestBannerUtilities(TestCase):
    """Test utility functions for banner management."""

    def setUp(self):
        """Set up test fixtures."""
        from saleor.channel.models import Channel

        self.channel = Channel.objects.create(
            name="Test Channel",
            slug="test-channel",
            is_active=True,
        )
        self.collection = ImageCollection.objects.create(
            name="Test Collection",
            channel=self.channel,
        )

    def test_get_active_banners_for_collection(self):
        """Test getting active banners for a collection."""
        # Create active banner
        Banner.objects.create(
            title="Active Banner",
            image="active.jpg",
            image_collection=self.collection,
            is_active=True,
            position=0,
        )

        # Create inactive banner
        Banner.objects.create(
            title="Inactive Banner",
            image="inactive.jpg",
            image_collection=self.collection,
            is_active=False,
            position=1,
        )

        active = get_active_banners_for_collection(self.collection.id)
        assert len(active) == 1
        assert active[0].title == "Active Banner"

    def test_get_expired_banners(self):
        """Test getting expired banners."""
        past_date = timezone.now() - timedelta(days=1)
        Banner.objects.create(
            title="Expired Banner",
            image="expired.jpg",
            image_collection=self.collection,
            end_date=past_date,
            is_active=True,
            position=0,
        )

        expired = get_expired_banners()
        assert expired.count() >= 1

    def test_get_upcoming_banners(self):
        """Test getting upcoming banners."""
        future_date = timezone.now() + timedelta(days=1)
        Banner.objects.create(
            title="Upcoming Banner",
            image="upcoming.jpg",
            image_collection=self.collection,
            start_date=future_date,
            is_active=True,
            position=0,
        )

        upcoming = get_upcoming_banners()
        assert upcoming.count() >= 1

    def test_reorder_banners(self):
        """Test reordering banners."""
        banner1 = Banner.objects.create(
            title="Banner 1",
            image="1.jpg",
            image_collection=self.collection,
            position=0,
        )
        banner2 = Banner.objects.create(
            title="Banner 2",
            image="2.jpg",
            image_collection=self.collection,
            position=1,
        )
        banner3 = Banner.objects.create(
            title="Banner 3",
            image="3.jpg",
            image_collection=self.collection,
            position=2,
        )

        # Reorder to [3, 1, 2]
        reorder_banners(
            self.collection.id, [banner3.id, banner1.id, banner2.id]
        )

        banner1.refresh_from_db()
        banner2.refresh_from_db()
        banner3.refresh_from_db()

        assert banner3.position == 0
        assert banner1.position == 1
        assert banner2.position == 2


@pytest.mark.django_db
class TestImageCollectionModel(TestCase):
    """Test ImageCollection model."""

    def setUp(self):
        """Set up test fixtures."""
        from saleor.channel.models import Channel

        self.channel = Channel.objects.create(
            name="Test Channel",
            slug="test-channel",
            is_active=True,
        )

    def test_collection_creation(self):
        """Test collection creation."""
        collection = ImageCollection.objects.create(
            name="Test Collection",
            description="Test Description",
            channel=self.channel,
        )

        assert collection.name == "Test Collection"
        assert collection.channel == self.channel

    def test_collection_unique_constraint(self):
        """Test that name must be unique per channel."""
        ImageCollection.objects.create(
            name="Unique Name",
            channel=self.channel,
        )

        with pytest.raises(Exception):
            ImageCollection.objects.create(
                name="Unique Name",
                channel=self.channel,
            )

    def test_collection_banners_relationship(self):
        """Test banners relationship."""
        collection = ImageCollection.objects.create(
            name="Test Collection",
            channel=self.channel,
        )

        Banner.objects.create(
            title="Banner 1",
            image="1.jpg",
            image_collection=collection,
            position=0,
        )
        Banner.objects.create(
            title="Banner 2",
            image="2.jpg",
            image_collection=collection,
            position=1,
        )

        assert collection.banners.count() == 2

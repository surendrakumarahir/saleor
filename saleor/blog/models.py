"""Data models for Blog Management System."""

import math
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class BlogPostStatus:
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

    CHOICES = [
        (DRAFT, "Draft"),
        (IN_REVIEW, "In Review"),
        (SCHEDULED, "Scheduled"),
        (PUBLISHED, "Published"),
        (ARCHIVED, "Archived"),
    ]


class BlogAuthor(models.Model):
    """Author profile for blog articles."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_author_profile",
    )
    display_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="blog/authors/", blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_name",)
        verbose_name = "Blog Author"
        verbose_name_plural = "Blog Authors"
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.display_name


class BlogCategory(models.Model):
    """Categorization for blog posts with hierarchical support."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    badge_color = models.CharField(
        max_length=100, default="bg-emerald-50 text-emerald-700"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Blog Category"
        verbose_name_plural = "Blog Categories"
        indexes = [
            models.Index(fields=["slug", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.parent:
            if self.parent_id == self.id:
                raise ValidationError("A category cannot be its own parent.")
            current = self.parent
            visited = {self.id}
            while current:
                if current.id in visited:
                    raise ValidationError("Circular parent category relationship detected.")
                visited.add(current.id)
                current = current.parent

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class BlogTag(models.Model):
    """Tag for blog posts."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Blog Tag"
        verbose_name_plural = "Blog Tags"
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    """Main Blog Post model."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField(blank=True)
    content_html = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=BlogPostStatus.CHOICES,
        default=BlogPostStatus.DRAFT,
        db_index=True,
    )
    author = models.ForeignKey(
        BlogAuthor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    primary_category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_posts",
    )
    categories = models.ManyToManyField(
        BlogCategory,
        related_name="posts",
        blank=True,
    )
    tags = models.ManyToManyField(
        BlogTag,
        related_name="posts",
        blank=True,
    )
    featured_image = models.ImageField(upload_to="blog/posts/", blank=True, null=True)
    featured_image_alt = models.CharField(max_length=255, blank=True)
    featured_image_caption = models.CharField(max_length=255, blank=True)

    # SEO fields
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    canonical_url = models.URLField(blank=True, null=True)
    robots_index = models.BooleanField(default=True)
    robots_follow = models.BooleanField(default=True)

    # Social fields
    og_title = models.CharField(max_length=255, blank=True)
    og_description = models.TextField(blank=True)
    og_image = models.ImageField(upload_to="blog/posts/og/", blank=True, null=True)

    # Engagement & Features
    is_featured = models.BooleanField(default=False, db_index=True)
    reading_time_minutes = models.PositiveIntegerField(default=5)
    allow_comments = models.BooleanField(default=False)

    # Publishing dates
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)

    # Tracking & Auditing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_blog_posts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_blog_posts",
    )
    revision_number = models.PositiveIntegerField(default=1)

    # Storefront features
    recommended_books = models.JSONField(default=list, blank=True)
    table_of_contents = models.JSONField(default=list, blank=True)
    product_collections = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["is_featured", "-published_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_publicly_published(self):
        """Check if post is published and visible on storefront."""
        now = timezone.now()
        if self.status == BlogPostStatus.PUBLISHED:
            return self.published_at is None or self.published_at <= now
        if self.status == BlogPostStatus.SCHEDULED and self.scheduled_at:
            return self.scheduled_at <= now
        return False

    def calculate_reading_time(self):
        """Estimate reading time from content or content_html."""
        raw_text = self.content_html or self.content or ""
        clean_text = re.sub(r"<[^>]+>", " ", raw_text)
        words = len(clean_text.split())
        self.reading_time_minutes = max(1, math.ceil(words / 200)) if words else 3
        return self.reading_time_minutes

    def create_revision(self, user=None):
        """Snapshot current state to BlogPostRevision."""
        return BlogPostRevision.objects.create(
            post=self,
            revision_number=self.revision_number,
            title=self.title,
            slug=self.slug,
            excerpt=self.excerpt,
            content=self.content,
            content_html=self.content_html,
            created_by=user,
        )


class BlogPostRevision(models.Model):
    """Historical snapshot of a blog post."""

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    excerpt = models.TextField(blank=True)
    content = models.TextField(blank=True)
    content_html = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-revision_number",)
        verbose_name = "Blog Post Revision"
        verbose_name_plural = "Blog Post Revisions"
        indexes = [
            models.Index(fields=["post", "revision_number"]),
        ]

    def __str__(self):
        return f"{self.post.title} (Rev {self.revision_number})"


class BlogRedirect(models.Model):
    """URL redirect mappings when an article's slug changes."""

    old_slug = models.CharField(max_length=255, unique=True, db_index=True)
    destination_slug = models.CharField(max_length=255)
    is_permanent = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Blog Redirect"
        verbose_name_plural = "Blog Redirects"

    def __str__(self):
        return f"Redirect: {self.old_slug} -> {self.destination_slug}"


class BlogAuditLog(models.Model):
    """Audit log for editorial tracking."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp",)
        verbose_name = "Blog Audit Log"
        verbose_name_plural = "Blog Audit Logs"

    def __str__(self):
        return f"{self.action} on {self.target_type}:{self.target_id} by {self.actor}"


class BlogPostFAQ(models.Model):
    """FAQ item associated with a blog post."""

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="faqs",
    )
    question = models.CharField(max_length=500)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Blog Post FAQ"
        verbose_name_plural = "Blog Post FAQs"
        indexes = [
            models.Index(fields=["post", "sort_order"]),
        ]

    def __str__(self):
        return f"FAQ: {self.question[:50]} ({self.post.title})"


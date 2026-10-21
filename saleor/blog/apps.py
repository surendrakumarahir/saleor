"""Django app configuration for blog management."""

from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = "saleor.blog"
    label = "blog"
    verbose_name = "Blog Management"

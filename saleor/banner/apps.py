"""Django app configuration for banner management."""

from django.apps import AppConfig


class BannerConfig(AppConfig):
    name = "saleor.banner"
    label = "banner"
    verbose_name = "Banner Management"

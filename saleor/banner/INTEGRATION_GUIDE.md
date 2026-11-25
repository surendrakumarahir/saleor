"""Banner Management System - Integration Guide

# Installation Instructions

## 1. Copy the Banner App

Copy the entire `saleor/banner/` directory to your Saleor installation at:
```
saleor/banner/
```

## 2. Update Django Settings

Add 'banner' app to INSTALLED_APPS in `saleor/settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'saleor.banner',
    # ... rest of apps
]
```

## 3. Add GraphQL Mutations and Queries

Edit `saleor/graphql/api.py` and add the following:

```python
from saleor.graphql.banner_queries import BannerQueries
from saleor.graphql.banner_mutations import BannerMutations

class Query(BannerQueries, ...other queries...):
    pass

class Mutation(BannerMutations, ...other mutations...):
    pass
```

## 4. Run Migrations

```bash
python manage.py migrate banner
```

## 5. Create Banner Permission in Database

After migrations, create the MANAGE_BANNERS permission:

```python
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from saleor.banner.models import ImageCollection

content_type = ContentType.objects.get_for_model(ImageCollection)
permission, created = Permission.objects.get_or_create(
    codename='manage_banners',
    name='Can manage banners',
    content_type=content_type,
)
```

Or use Django admin to add the permission to staff users.

## 6. Update AGENTS.md (Optional)

Add to your AGENTS.md file:

### Banner Management System

- Models: `saleor.banner.models`
- Permissions: `saleor.banner.permissions`
- Admin: `saleor.banner.admin`
- GraphQL Types: `saleor.graphql.banner_types`
- GraphQL Queries: `saleor.graphql.banner_queries`
- GraphQL Mutations: `saleor.graphql.banner_mutations`


## API Usage Examples

### Create Image Collection

```graphql
mutation {
  createImageCollection(
    input: {
      name: "Homepage Banners"
      description: "Main banners for homepage"
      channelId: "Q2hhbm5lbDox"
      isActive: true
    }
  ) {
    imageCollection {
      id
      name
      channel {
        slug
      }
    }
    errors {
      code
      message
    }
  }
}
```

### Create Banner

```graphql
mutation {
  createBanner(
    input: {
      title: "Summer Sale"
      description: "50% off all items"
      image: "https://example.com/banner.jpg"
      altText: "Summer Sale Banner"
      linkUrl: "https://example.com/sale"
      linkText: "Shop Now"
      collectionId: "QmFubmVyQ29sbGVjdGlvbjox"
      position: 0
      isActive: true
      startDate: "2024-06-01T00:00:00Z"
      endDate: "2024-08-31T23:59:59Z"
      keyValues: {
        "discount_percent": "50"
        "campaign_id": "summer_2024"
      }
    }
  ) {
    banner {
      id
      title
      position
      isActive
    }
    errors {
      code
      message
    }
  }
}
```

### Get Active Banners for Collection

```graphql
query {
  activeBannersByCollection(
    collectionId: "QmFubmVyQ29sbGVjdGlvbjox"
  ) {
    id
    title
    image
    altText
    linkUrl
    linkText
    keyValues
    isActive
  }
}
```

### List All Banners with Filters

```graphql
query {
  banners(
    first: 10
    filter: {
      channelId: "Q2hhbm5lbDox"
      isActive: true
    }
  ) {
    edges {
      node {
        id
        title
        position
        image
        keyValues
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### Update Banner

```graphql
mutation {
  updateBanner(
    input: {
      id: "QmFubmVyOjE="
      title: "New Title"
      position: 1
      isActive: true
    }
  ) {
    banner {
      id
      title
      position
    }
    errors {
      code
      message
    }
  }
}
```

### Delete Banner

```graphql
mutation {
  deleteBanner(id: "QmFubmVyOjE=") {
    success
    errors {
      code
      message
    }
  }
}
```


## Models Overview

### ImageCollection

- **name**: CharField - Unique collection name
- **description**: TextField - Optional description
- **channel**: ForeignKey - Channel this collection belongs to
- **is_active**: BooleanField - Enable/disable collection
- **created_at**: DateTimeField - Auto timestamp
- **updated_at**: DateTimeField - Auto timestamp

### Banner

- **title**: CharField - Banner title
- **description**: TextField - Detailed description
- **image**: ImageField - Banner image (uploads to 'banners/')
- **alt_text**: CharField - Image alt text for accessibility
- **link_url**: URLField - Optional link destination
- **link_text**: CharField - Optional link label
- **custom_field_1-3**: CharField - Extensible custom fields
- **key_values**: JSONField - Unlimited key-value pairs
- **image_collection**: ForeignKey - Parent collection
- **position**: IntegerField - Display order
- **is_active**: BooleanField - Enable/disable banner
- **start_date**: DateTimeField - Schedule start (null = immediate)
- **end_date**: DateTimeField - Schedule end (null = no expiry)
- **created_at**: DateTimeField - Auto timestamp
- **updated_at**: DateTimeField - Auto timestamp

### Methods

**Banner.is_scheduled_active(at_time=None)**

Check if a banner is currently active based on scheduling.

```python
from saleor.banner.models import Banner
from django.utils import timezone

banner = Banner.objects.first()
is_active = banner.is_scheduled_active()  # Current time
is_active = banner.is_scheduled_active(timezone.now())  # Explicit time
```


## Django Admin

Access banner management at:
- `/admin/banner/imagecollection/` - Manage collections
- `/admin/banner/banner/` - Manage banners

Features:
- Inline banner editing within collections
- Image preview in admin
- Schedule status indicator
- Filter by channel, collection, status, creation date
- Search by title, description, alt text
- Sortable by position
- Bulk actions support


## Permissions

### MANAGE_BANNERS

Required for all banner operations:
- Creating collections and banners
- Updating collections and banners
- Deleting collections and banners
- Viewing protected queries

Assign to staff users via Django admin or:

```python
from django.contrib.auth.models import Group, Permission

manage_banners_perm = Permission.objects.get(codename='manage_banners')
staff_group = Group.objects.get(name='Staff')
staff_group.permissions.add(manage_banners_perm)
```


## File Structure

```
saleor/banner/
├── __init__.py
├── apps.py
├── models.py
├── admin.py
├── permissions.py
├── error_codes.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py

saleor/graphql/
├── banner_types.py        # GraphQL types
├── banner_filters.py      # Filter classes
├── banner_queries.py      # Query resolvers
├── banner_mutations.py    # Mutation resolvers
├── banner_errors.py       # Error definitions
```


## Thread Safety & Concurrency

The banner app follows Saleor's concurrency patterns:

- Position updates are atomic using Django ORM
- Schedule queries are read-only
- Multi-instance deployments supported
- No race conditions in basic operations


## Performance Considerations

### Indexes

- `(image_collection, position)` - For ordering queries
- `(is_active, start_date, end_date)` - For scheduling queries

### Query Optimization

Get active banners efficiently:

```python
from django.utils import timezone
from saleor.banner.models import Banner

banners = Banner.objects.filter(
    image_collection_id=collection_id,
    is_active=True,
).select_related('image_collection')

now = timezone.now()
active = [b for b in banners if b.is_scheduled_active(now)]
```

Or use database filtering for scheduled banners:

```python
from django.db.models import Q
from django.utils import timezone

now = timezone.now()
banners = Banner.objects.filter(
    image_collection_id=collection_id,
    is_active=True,
).filter(
    Q(start_date__isnull=True) | Q(start_date__lte=now),
    Q(end_date__isnull=True) | Q(end_date__gte=now),
)
```


## Troubleshooting

### Banners not appearing in GraphQL

1. Check that app is in INSTALLED_APPS
2. Verify migrations were run: `python manage.py migrate banner`
3. Check BannerQueries and BannerMutations are added to api.py
4. Verify user has MANAGE_BANNERS permission

### Image upload issues

1. Check MEDIA_ROOT and MEDIA_URL are configured
2. Ensure 'banners/' directory is writable
3. Verify Pillow is installed for image processing

### Permission denied errors

1. Create MANAGE_BANNERS permission after migrations
2. Assign permission to staff group or individual users
3. User must be staff=True for admin access


## Extending the System

### Adding custom fields to Banner

Edit [models.py](models.py):

```python
class Banner(models.Model):
    # ... existing fields ...
    custom_metadata = models.JSONField(default=dict)
```

Then create a migration:

```bash
python manage.py makemigrations banner
python manage.py migrate banner
```

### Custom banner types

Extend Banner model:

```python
class VideoPopupBanner(Banner):
    video_url = models.URLField()
    autoplay = models.BooleanField(default=False)

    class Meta:
        proxy = True
```

### Events/Signals

Add banner event tracking:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Banner

@receiver(post_save, sender=Banner)
def banner_created(sender, instance, created, **kwargs):
    if created:
        print(f"Banner created: {instance.title}")
```
"""

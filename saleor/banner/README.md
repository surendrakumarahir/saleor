"""
# Banner Management System for Saleor

A comprehensive, production-ready banner management plugin for Saleor e-commerce platform.

## Overview

This banner management system provides complete banner lifecycle management with support for:

- **Multiple Collections**: Organize banners by channel-specific collections
- **Advanced Scheduling**: Time-based banner activation with start/end dates
- **Rich Metadata**: Custom fields and unlimited key-value storage
- **GraphQL API**: Full CRUD operations via GraphQL
- **Django Admin**: Professional admin interface with image previews
- **Permission System**: Role-based access control via Saleor permissions
- **Performance**: Optimized queries with proper database indexes

## Features

### ✨ Core Features

- 📦 **ImageCollection Model**: Group banners by channel
- 🖼️ **Banner Model**: Flexible banner storage with:
  - Image uploads with alt text
  - Scheduling (start/end dates)
  - Click tracking via link_url and link_text
  - 3 custom text fields for extensibility
  - Unlimited key-value pairs via JSONField
  - Position-based ordering
- 🔐 **Permission System**: MANAGE_BANNERS permission
- 📊 **Admin Interface**: Inline editing, image preview, schedule status
- 🚀 **GraphQL API**: Complete schema with queries and mutations
- 🧪 **Unit Tests**: Comprehensive test coverage

### 🎯 GraphQL Operations

**Queries:**
- `banner(id)` - Get single banner
- `banners(first, filter)` - List banners with filtering
- `imageCollection(id)` - Get single collection
- `imageCollections(first, filter)` - List collections
- `activeBannersByCollection(collectionId, atTime)` - Get scheduled banners

**Mutations:**
- `createImageCollection` - Create collection
- `updateImageCollection` - Update collection
- `deleteImageCollection` - Delete collection
- `createBanner` - Create banner
- `updateBanner` - Update banner
- `deleteBanner` - Delete banner

### 🔧 Admin Features

- Inline banner creation within collections
- Image preview (100x100 for inline, 150x150 for detail)
- Schedule status indicator (✓ Active, ✗ Inactive, No Schedule)
- Filtering by channel, collection, active status
- Search by title, description, alt text
- Reorderable positions
- Bulk actions support

## File Structure

```
saleor/banner/
├── __init__.py                      # Package init
├── apps.py                          # Django app config
├── models.py                        # ImageCollection and Banner models
├── admin.py                         # Django admin configuration
├── permissions.py                  # Permission enums
├── error_codes.py                  # Error code definitions
├── utils.py                         # Utility functions
├── tests.py                         # Unit tests
├── SETUP.md                         # Installation guide
├── INTEGRATION_GUIDE.md             # API usage guide
├── README.md                        # This file
└── migrations/
    ├── __init__.py
    └── 0001_initial.py

saleor/graphql/
├── banner_types.py                 # GraphQL object types
├── banner_filters.py               # Filter classes
├── banner_queries.py               # Query resolvers
├── banner_mutations.py             # Mutation resolvers
└── banner_errors.py                # Error types
```

## Quick Start

### Installation

1. Copy `saleor/banner/` directory to your Saleor installation
2. Copy GraphQL files to `saleor/graphql/`:
   - banner_types.py
   - banner_filters.py
   - banner_queries.py
   - banner_mutations.py
   - banner_errors.py

### Configuration

1. Add to `saleor/settings.py`:
   ```python
   INSTALLED_APPS = [
       # ... other apps ...
       'saleor.banner',
   ]
   ```

2. Update `saleor/graphql/api.py`:
   ```python
   from saleor.graphql.banner_queries import BannerQueries
   from saleor.graphql.banner_mutations import BannerMutations

   class Query(BannerQueries, ...):
       pass

   class Mutation(BannerMutations, ...):
       pass
   ```

3. Run migrations:
   ```bash
   python manage.py migrate banner
   ```

4. Create permission:
   ```python
   from django.contrib.auth.models import Permission
   from django.contrib.contenttypes.models import ContentType
   from saleor.banner.models import ImageCollection

   ct = ContentType.objects.get_for_model(ImageCollection)
   Permission.objects.get_or_create(
       codename='manage_banners',
       name='Can manage banners',
       content_type=ct,
   )
   ```

See [SETUP.md](SETUP.md) for detailed installation instructions.

## Models

### ImageCollection

```python
class ImageCollection(models.Model):
    name: CharField              # Collection name (unique per channel)
    description: TextField       # Optional description
    channel: ForeignKey          # Channel this collection belongs to
    is_active: BooleanField      # Enable/disable collection
    created_at: DateTimeField    # Auto timestamp
    updated_at: DateTimeField    # Auto timestamp
```

### Banner

```python
class Banner(models.Model):
    title: CharField             # Banner title (required)
    description: TextField       # Optional description
    image: ImageField            # Banner image (uploads to 'banners/')
    alt_text: CharField          # Image alt text for accessibility
    link_url: URLField           # Optional link destination
    link_text: CharField         # Optional link label
    custom_field_1: CharField    # Extensible custom field
    custom_field_2: CharField    # Extensible custom field
    custom_field_3: CharField    # Extensible custom field
    key_values: JSONField        # Unlimited key-value pairs
    image_collection: ForeignKey # Parent collection
    position: IntegerField       # Display order (default: 0)
    is_active: BooleanField      # Enable/disable banner
    start_date: DateTimeField    # Schedule start (null = immediate)
    end_date: DateTimeField      # Schedule end (null = no expiry)
    created_at: DateTimeField    # Auto timestamp
    updated_at: DateTimeField    # Auto timestamp

    def is_scheduled_active(at_time=None) -> bool:
        """Check if banner is active at given time."""
```

## GraphQL Examples

### Create Banner with Scheduling

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
      collectionId: "..."
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
    banner { id title }
    errors { code message }
  }
}
```

### Get Active Banners for Collection

```graphql
{
  activeBannersByCollection(
    collectionId: "..."
    atTime: "2024-07-15T12:00:00Z"
  ) {
    id
    title
    image
    linkUrl
    keyValues
  }
}
```

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for more examples.

## Admin Interface

Access at `/admin/banner/`:

- **Image Collections**: Create, edit, delete collections with inline banner management
- **Banners**: Create, edit, delete, reorder banners with image preview

Features:
- Inline banner editing within collection detail
- Image preview (100x100 in inline, 150x150 in detail)
- Schedule status indicator
- Filter by channel, collection, active status
- Search by title, description, alt text
- Sortable by position
- Bulk delete action

## Permissions

### MANAGE_BANNERS

Required permission for:
- Creating, reading, updating, deleting collections
- Creating, reading, updating, deleting banners
- All GraphQL mutations (reads are public)

Assign to staff users via Django admin or programmatically:

```python
from django.contrib.auth.models import Permission, Group

perm = Permission.objects.get(codename='manage_banners')
staff_group = Group.objects.get(name='Staff')
staff_group.permissions.add(perm)
```

## Utility Functions

Located in `saleor/banner/utils.py`:

```python
# Get active banners for a collection
get_active_banners_for_collection(collection_id, at_time=None)

# Get banners by channel
get_banners_by_channel(channel_id)

# Reorder banners
reorder_banners(collection_id, banner_order)

# Get expired banners
get_expired_banners()

# Get upcoming banners
get_upcoming_banners()

# Deactivate expired banners
deactivate_expired_banners()

# Get collection statistics
get_collection_banners_with_stats(collection_id)
```

## Testing

Run tests:

```bash
# With pytest
pytest saleor/banner/tests.py -v

# With Django test runner
python manage.py test saleor.banner

# Specific test
pytest saleor/banner/tests.py::TestBannerModel::test_banner_creation -v
```

Test coverage includes:
- Model creation and validation
- Scheduling logic
- Key-value storage
- Custom fields
- Relationship constraints
- Utility functions
- Banner ordering

## Performance

### Database Indexes

```python
# Indexed for ordering queries
Index(fields=('image_collection', 'position'))

# Indexed for scheduling queries
Index(fields=('is_active', 'start_date', 'end_date'))

# Unique constraint
UniqueConstraint(fields=('name', 'channel'))
```

### Query Optimization

Get active banners efficiently:

```python
# With Python filtering
banners = Banner.objects.filter(
    image_collection_id=collection_id,
    is_active=True,
).select_related('image_collection')
active = [b for b in banners if b.is_scheduled_active()]

# Or with database filtering
banners = Banner.objects.filter(
    image_collection_id=collection_id,
    is_active=True,
).filter(
    Q(start_date__isnull=True) | Q(start_date__lte=now),
    Q(end_date__isnull=True) | Q(end_date__gte=now),
)
```

### Recommendations

- Cache `activeBannersByCollection` results with TTL
- Use select_related/prefetch_related in batch operations
- Implement pagination for banner lists
- Consider CDN for banner image delivery

## Extending the System

### Add New Custom Field

1. Edit `models.py`:
   ```python
   class Banner(models.Model):
       custom_metadata = models.JSONField(default=dict)
   ```

2. Create migration:
   ```bash
   python manage.py makemigrations banner
   python manage.py migrate banner
   ```

3. Update GraphQL types in `banner_types.py`

### Add Banner Events

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Banner)
def banner_created(sender, instance, created, **kwargs):
    if created:
        # Handle banner creation event
        pass
```

## Troubleshooting

See [SETUP.md](SETUP.md) for detailed troubleshooting guide.

Common issues:
- App not in INSTALLED_APPS → Add to settings.py
- Migration errors → Delete __pycache__, re-run migrations
- Permission denied → Create MANAGE_BANNERS permission
- Image upload fails → Check MEDIA_ROOT, install Pillow

## Production Checklist

- [ ] All migrations applied successfully
- [ ] MANAGE_BANNERS permission created and assigned
- [ ] Image storage configured (S3, local, etc.)
- [ ] Unit tests passing locally and in CI/CD
- [ ] GraphQL queries tested with authentication
- [ ] Admin interface accessible to staff
- [ ] Database backups configured
- [ ] Logging/monitoring set up for banner operations
- [ ] Rate limiting considered for GraphQL mutations

## Support & Documentation

- **Installation**: See [SETUP.md](SETUP.md)
- **API Usage**: See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
- **Models**: See [models.py](models.py)
- **Admin**: See [admin.py](admin.py)
- **Tests**: See [tests.py](tests.py)
- **Utilities**: See [utils.py](utils.py)

## License

This banner management system follows the same license as Saleor.

## Contributing

When extending the banner system:

1. Follow Saleor's code style and patterns
2. Write tests for new features
3. Update documentation
4. Use type hints
5. Follow Django best practices
6. Ensure thread safety for concurrent access

## Version Information

- Saleor: 3.x+ (tested on 3.22+)
- Django: 3.2+
- Python: 3.9+
- Graphene: 2.x+

## Support

For issues or questions:
1. Check [SETUP.md](SETUP.md) troubleshooting section
2. Review [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
3. Check existing tests for usage examples
4. Review Saleor documentation at https://docs.saleor.io

---

**Happy banner management! 🎉**
"""

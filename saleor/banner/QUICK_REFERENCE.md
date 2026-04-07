"""
# Banner Management System - Quick Reference

## 📦 What You've Received

Complete banner management plugin for Saleor with 2500+ lines of production-ready code:

- **App**: saleor/banner/ (10 files)
- **GraphQL**: 5 files in saleor/graphql/
- **Documentation**: 4 comprehensive guides
- **Tests**: 15+ test cases
- **Admin**: Django admin interface


## ⚡ Quick Installation

### 1. Add to settings.py
```python
INSTALLED_APPS = [
    'saleor.banner',  # Add this
]
```

### 2. Update saleor/graphql/api.py
```python
from saleor.graphql.banner_queries import BannerQueries
from saleor.graphql.banner_mutations import BannerMutations

class Query(BannerQueries, ...): pass
class Mutation(BannerMutations, ...): pass
```

### 3. Run migrations
```bash
python manage.py migrate banner
```

### 4. Create permission
```bash
python manage.py shell
>>> from django.contrib.auth.models import Permission
>>> from django.contrib.contenttypes.models import ContentType
>>> from saleor.banner.models import ImageCollection
>>> ct = ContentType.objects.get_for_model(ImageCollection)
>>> Permission.objects.get_or_create(
...     codename='manage_banners',
...     name='Can manage banners',
...     content_type=ct
... )
```

**That's it!** See SETUP.md for detailed instructions.


## 📁 File Structure

```
saleor/banner/                    ← All banner code
├── models.py                     ← Database models
├── admin.py                      ← Admin interface
├── permissions.py               ← Permission enum
├── utils.py                     ← Helper functions
├── tests.py                     ← Unit tests
├── migrations/0001_initial.py   ← Database schema
└── README/SETUP/INTEGRATION_GUIDE.md

saleor/graphql/
├── banner_types.py              ← GraphQL types
├── banner_queries.py            ← GraphQL queries
├── banner_mutations.py          ← GraphQL mutations
├── banner_filters.py            ← Filters
└── banner_errors.py             ← Error types
```


## 🎯 Core Features

### Models
- **ImageCollection**: Channel-scoped banner groups
- **Banner**: Individual banners with scheduling, metadata, images

### Admin
- `/admin/banner/imagecollection/` - Manage collections
- `/admin/banner/banner/` - Manage banners
- Image preview, inline editing, schedule indicators

### GraphQL Queries
- `banner(id)` - Get banner
- `banners(filter, first)` - List banners
- `imageCollection(id)` - Get collection
- `imageCollections(filter, first)` - List collections
- `activeBannersByCollection(collectionId, atTime)` - Scheduled banners

### GraphQL Mutations
- Create/Update/Delete ImageCollection
- Create/Update/Delete Banner
- Full validation and error handling

### Utilities
- get_active_banners_for_collection()
- get_banners_by_channel()
- reorder_banners()
- get_expired_banners()
- get_upcoming_banners()
- deactivate_expired_banners()
- get_collection_banners_with_stats()


## 📊 Database Models

### ImageCollection
```
- name: CharField
- description: TextField (optional)
- channel: ForeignKey to Channel
- is_active: BooleanField
- created_at, updated_at: DateTimeField
```

### Banner
```
- title: CharField
- description: TextField
- image: ImageField
- alt_text, link_url, link_text: CharField/URLField
- custom_field_1, custom_field_2, custom_field_3: CharField
- key_values: JSONField (unlimited key-value pairs)
- image_collection: ForeignKey
- position: IntegerField (for ordering)
- is_active: BooleanField
- start_date, end_date: DateTimeField (scheduling)
- created_at, updated_at: DateTimeField
```


## 🚀 GraphQL Examples

### Create Collection
```graphql
mutation {
  createImageCollection(input: {
    name: "Homepage"
    channelId: "Q2hhbm5lbDox"
  }) {
    imageCollection { id name }
    errors { code message }
  }
}
```

### Create Banner
```graphql
mutation {
  createBanner(input: {
    title: "Summer Sale"
    image: "https://example.com/banner.jpg"
    collectionId: "..."
    linkUrl: "https://example.com/sale"
    linkText: "Shop Now"
    startDate: "2024-06-01T00:00:00Z"
    endDate: "2024-08-31T23:59:59Z"
  }) {
    banner { id title }
    errors { code message }
  }
}
```

### Get Active Banners
```graphql
query {
  activeBannersByCollection(collectionId: "...") {
    id title image linkUrl
  }
}
```

### List Banners
```graphql
query {
  banners(first: 20, filter: { isActive: true }) {
    edges { node { id title position } }
  }
}
```


## 🔐 Permissions

### MANAGE_BANNERS
- Required for all mutations
- Required for protected queries
- Assign to staff users

### Setup
```python
from django.contrib.auth.models import Permission, Group
perm = Permission.objects.get(codename='manage_banners')
staff_group = Group.objects.get(name='Staff')
staff_group.permissions.add(perm)
```


## 🧪 Testing

```bash
# Run all tests
pytest saleor/banner/tests.py -v

# Run specific test
pytest saleor/banner/tests.py::TestBannerModel -v
```

Test coverage: 15+ test cases
- Model creation and validation
- Scheduling logic
- Relationships
- Utilities


## 📚 Documentation Files

1. **README.md** - Feature overview, examples, troubleshooting
2. **SETUP.md** - Step-by-step installation, production checklist
3. **INTEGRATION_GUIDE.md** - Detailed API usage, performance tips
4. **IMPLEMENTATION_SUMMARY.md** - What's included, feature list


## ⚙️ Utility Functions

### Get Active Banners
```python
from saleor.banner.utils import get_active_banners_for_collection
from django.utils import timezone

banners = get_active_banners_for_collection(collection_id)
# Returns banners active NOW

banners = get_active_banners_for_collection(
    collection_id,
    at_time=specific_datetime
)
# Returns banners active at specific time
```

### Reorder Banners
```python
from saleor.banner.utils import reorder_banners

banner_ids = [3, 1, 2]  # New order
reorder_banners(collection_id, banner_ids)
```

### Get Stats
```python
from saleor.banner.utils import get_collection_banners_with_stats

stats = get_collection_banners_with_stats(collection_id)
# Returns: {
#   'collection': ...,
#   'total': 10,
#   'active': 8,
#   'inactive': 2,
#   'scheduled': 5,
#   'currently_showing': 3,
#   'expired': 1,
#   'upcoming': 2
# }
```


## 🎯 Common Tasks

### Create First Banner Collection
```python
from saleor.banner.models import ImageCollection
from saleor.channel.models import Channel

channel = Channel.objects.first()
collection = ImageCollection.objects.create(
    name="Homepage Banners",
    description="Main page promotions",
    channel=channel,
    is_active=True
)
```

### Create Banner with Scheduling
```python
from saleor.banner.models import Banner
from django.utils import timezone
from datetime import timedelta

now = timezone.now()
collection = ImageCollection.objects.first()

banner = Banner.objects.create(
    title="Limited Time Offer",
    image="offer.jpg",
    image_collection=collection,
    link_url="https://example.com/offer",
    link_text="Learn More",
    position=0,
    is_active=True,
    start_date=now,
    end_date=now + timedelta(days=7),
    key_values={
        "discount_percent": "30",
        "campaign_id": "limited_offer"
    }
)
```

### Check if Banner is Currently Active
```python
banner = Banner.objects.first()
if banner.is_scheduled_active():
    print("Banner is currently showing!")
```

### Get All Expired Banners
```python
from saleor.banner.utils import get_expired_banners

expired = get_expired_banners()
for banner in expired:
    banner.is_active = False
    banner.save()
```


## 🔍 Access Points

### Admin Interface
- Collections: `/admin/banner/imagecollection/`
- Banners: `/admin/banner/banner/`

### GraphQL
- Endpoint: `/graphql/`
- Queries: banner, banners, imageCollection, imageCollections, activeBannersByCollection
- Mutations: create/update/delete for both models

### Management Commands
```bash
python manage.py migrate banner
python manage.py test saleor.banner
python manage.py shell
```


## 🛠️ Troubleshooting Quick Fixes

| Issue | Fix |
|-------|-----|
| App not found | Add 'saleor.banner' to INSTALLED_APPS |
| Permission denied | Create MANAGE_BANNERS permission |
| Migration errors | Delete __pycache__, re-run migrate |
| Image upload fails | Install Pillow, check MEDIA_ROOT |
| No admin access | User needs is_staff=True + permission |
| GraphQL returns no data | Check permission assignment |

**Full troubleshooting: See SETUP.md**


## 📞 Support Resources

- **Installation Issues** → SETUP.md
- **API Usage** → INTEGRATION_GUIDE.md
- **Feature Overview** → README.md
- **What's Included** → IMPLEMENTATION_SUMMARY.md
- **Inline Documentation** → Code docstrings
- **Tests** → tests.py for usage examples

---

## ✅ Next Steps

1. **Read SETUP.md** for installation
2. **Run migrations** (`python manage.py migrate banner`)
3. **Create permission** (see SETUP.md step 5)
4. **Test in admin** (`/admin/banner/`)
5. **Test GraphQL** (`/graphql/`)
6. **Read INTEGRATION_GUIDE.md** for advanced usage

**Everything is ready to go! 🚀**
"""

"""
Banner Management System for Saleor - Complete Setup Guide

================================================================================
                            INSTALLATION STEPS
================================================================================

## STEP 1: Verify Files in Place

All banner app files should be at:
    /saleor/banner/
        ├── __init__.py
        ├── apps.py
        ├── models.py
        ├── admin.py
        ├── permissions.py
        ├── error_codes.py
        ├── utils.py
        ├── tests.py
        ├── INTEGRATION_GUIDE.md
        └── migrations/
            ├── __init__.py
            └── 0001_initial.py

And GraphQL files at:
    /saleor/graphql/
        ├── banner_types.py
        ├── banner_filters.py
        ├── banner_queries.py
        ├── banner_mutations.py
        └── banner_errors.py


## STEP 2: Add to Django Settings

Edit: saleor/settings.py

Find INSTALLED_APPS and add 'saleor.banner':

    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        
        # ... other Saleor apps ...
        'saleor.channel',
        'saleor.banner',  # ← ADD THIS LINE
        
        # ... rest of apps ...
    ]


## STEP 3: Update GraphQL API

Edit: saleor/graphql/api.py

Add imports at the top:
    from saleor.graphql.banner_queries import BannerQueries
    from saleor.graphql.banner_mutations import BannerMutations

Update Query class to inherit from BannerQueries:
    class Query(
        # ... existing query parents ...
        BannerQueries,
        # ... rest of parents ...
    ):
        pass

Update Mutation class to inherit from BannerMutations:
    class Mutation(
        # ... existing mutation parents ...
        BannerMutations,
        # ... rest of parents ...
    ):
        pass

Example:
    class Query(
        BannerQueries,
        AccountQueries,
        AppQueries,
        # ... other queries
    ):
        pass

    class Mutation(
        BannerMutations,
        AccountMutations,
        AppMutations,
        # ... other mutations
    ):
        pass


## STEP 4: Run Migrations

In terminal:
    python manage.py migrate banner

Expected output:
    Operations to perform:
      Apply all migrations: banner
    Running migrations:
      Applying banner.0001_initial... OK


## STEP 5: Create Permission

In Django shell:
    python manage.py shell

    >>> from django.contrib.auth.models import Permission, Group
    >>> from django.contrib.contenttypes.models import ContentType
    >>> from saleor.banner.models import ImageCollection
    >>> 
    >>> ct = ContentType.objects.get_for_model(ImageCollection)
    >>> perm, created = Permission.objects.get_or_create(
    ...     codename='manage_banners',
    ...     name='Can manage banners',
    ...     content_type=ct,
    ... )
    >>> print(f"Permission created: {created}")
    >>> exit()

Or in Django Admin:
    1. Go to /admin/auth/permission/
    2. Create new permission:
       - Content type: Image Collection
       - Codename: manage_banners
       - Name: Can manage banners


## STEP 6: Assign Permission to Staff Group (Optional)

In Django shell:
    python manage.py shell

    >>> from django.contrib.auth.models import Permission, Group
    >>> 
    >>> # Get or create staff group
    >>> staff_group, created = Group.objects.get_or_create(name='Staff')
    >>> 
    >>> # Get permission
    >>> perm = Permission.objects.get(codename='manage_banners')
    >>> 
    >>> # Add permission to group
    >>> staff_group.permissions.add(perm)
    >>> 
    >>> print(f"Permission added to Staff group")
    >>> exit()


## STEP 7: Verify Installation

Test the installation:
    python manage.py shell

    >>> from saleor.banner.models import ImageCollection, Banner
    >>> from saleor.channel.models import Channel
    >>>
    >>> # Get a channel
    >>> channel = Channel.objects.first()
    >>> 
    >>> # Create a collection
    >>> collection = ImageCollection.objects.create(
    ...     name="Test Collection",
    ...     channel=channel,
    ...     is_active=True
    ... )
    >>> print(f"Created collection: {collection}")
    >>>
    >>> # Create a banner
    >>> banner = Banner.objects.create(
    ...     title="Test Banner",
    ...     image="test.jpg",
    ...     image_collection=collection,
    ...     position=0,
    ...     is_active=True
    ... )
    >>> print(f"Created banner: {banner}")
    >>> 
    >>> # Verify
    >>> print(f"Total collections: {ImageCollection.objects.count()}")
    >>> print(f"Total banners: {Banner.objects.count()}")
    >>> exit()

Expected output:
    Created collection: Test Collection (...)
    Created banner: Test Banner
    Total collections: 1
    Total banners: 1


## STEP 8: Test GraphQL API

Use GraphQL playground at: http://localhost:8000/graphql/

Query to list collections:
    {
      imageCollections(first: 10) {
        edges {
          node {
            id
            name
            channel {
              slug
            }
          }
        }
      }
    }

Query to list banners:
    {
      banners(first: 10) {
        edges {
          node {
            id
            title
            position
            isActive
          }
        }
      }
    }


## STEP 9: Access Django Admin

Visit: http://localhost:8000/admin/

You should see:
    - Banner Management > Image Collections
    - Banner Management > Banners

Click "Image Collections" and create a new collection to test the admin interface.


================================================================================
                           QUICK TROUBLESHOOTING
================================================================================

### Issue: "App 'banner' doesn't have a 'models' module"
**Solution:** Ensure saleor/banner/__init__.py exists and has content

### Issue: Migration errors
**Solution:** 
    - Delete saleor/banner/migrations/__pycache__
    - Run: python manage.py migrate banner --fake-initial
    - Then: python manage.py migrate

### Issue: Permission denied in GraphQL
**Solution:**
    - Create MANAGE_BANNERS permission (Step 5)
    - Assign permission to user's group (Step 6)
    - User must have is_staff=True

### Issue: Image upload fails
**Solution:**
    - Check MEDIA_ROOT in settings.py is writable
    - Ensure MEDIA_URL is configured
    - Install Pillow: pip install Pillow

### Issue: "Content type matching query does not exist"
**Solution:**
    - Run migrations again: python manage.py migrate
    - Rebuild migration: python manage.py makemigrations --empty banner --name add_permissions

### Issue: GraphQL mutations return no errors but no data
**Solution:**
    - Check user has MANAGE_BANNERS permission
    - Verify query syntax matches schema
    - Check Django logs for detailed errors

### Issue: Admin doesn't show banners
**Solution:**
    - Check INSTALLED_APPS has 'saleor.banner'
    - Restart Django development server
    - Clear browser cache


================================================================================
                           TESTING THE SYSTEM
================================================================================

### Running Unit Tests

    python manage.py test saleor.banner

### Running with pytest

    pytest saleor/banner/tests.py -v

### Running specific test

    pytest saleor/banner/tests.py::TestBannerModel::test_banner_creation -v

### Testing GraphQL mutations with curl

    curl -X POST http://localhost:8000/graphql/ \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -d '{
        "query": "mutation { createImageCollection(input: {name: \"Test\", channelId: \"Q2hhbm5lbDox\", isActive: true}) { imageCollection { id name } errors { code message } } }"
      }'


================================================================================
                        PRODUCTION DEPLOYMENT
================================================================================

### Before Going Live

1. ✓ Run all tests: pytest saleor/banner/tests.py
2. ✓ Check migrations: python manage.py migrate --plan
3. ✓ Verify permissions: python manage.py shell
   >>> from django.contrib.auth.models import Permission
   >>> Permission.objects.get(codename='manage_banners')
4. ✓ Test GraphQL queries with authentication
5. ✓ Configure image storage (S3, CDN, etc.)
6. ✓ Set up proper media handling

### Deployment Checklist

- [ ] App added to INSTALLED_APPS in settings.py
- [ ] GraphQL types, queries, mutations added to api.py
- [ ] Migrations run on production database
- [ ] MANAGE_BANNERS permission created
- [ ] Permission assigned to staff groups
- [ ] Image storage configured (MEDIA_ROOT, MEDIA_URL)
- [ ] Tests pass locally and in CI/CD
- [ ] Monitoring/logging configured for banner operations
- [ ] Backup database before deployment

### Scaling Considerations

- Banners are read-heavy, write-light → good for caching
- Add cache layer for active_banners_by_collection query:
    from django.core.cache import cache
    cache_key = f"active_banners_{collection_id}"
    banners = cache.get(cache_key)

- Use select_for_update() if implementing bulk operations

- Consider denormalizing channels on Banner for faster queries


================================================================================
                          NEXT STEPS
================================================================================

1. Read INTEGRATION_GUIDE.md for API usage examples
2. Read models.py for field documentation
3. Explore banner_queries.py for available GraphQL queries
4. Explore banner_mutations.py for available GraphQL mutations
5. Check utils.py for utility functions
6. Review admin.py for admin customization options

For detailed information, see:
- INTEGRATION_GUIDE.md - API usage and examples
- models.py - Field definitions and model methods
- admin.py - Django admin customization


================================================================================
"""

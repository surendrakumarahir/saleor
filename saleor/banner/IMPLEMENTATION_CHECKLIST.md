"""
# Banner Management System - Implementation Checklist

Use this checklist to track your implementation progress.

## 📋 Pre-Implementation

- [ ] All banner app files copied to saleor/banner/
  - [ ] __init__.py
  - [ ] apps.py
  - [ ] models.py
  - [ ] admin.py
  - [ ] permissions.py
  - [ ] error_codes.py
  - [ ] utils.py
  - [ ] tests.py
  - [ ] migrations/__init__.py
  - [ ] migrations/0001_initial.py

- [ ] All GraphQL files copied to saleor/graphql/
  - [ ] banner_types.py
  - [ ] banner_filters.py
  - [ ] banner_queries.py
  - [ ] banner_mutations.py
  - [ ] banner_errors.py

- [ ] Documentation files reviewed
  - [ ] README.md
  - [ ] SETUP.md
  - [ ] INTEGRATION_GUIDE.md
  - [ ] IMPLEMENTATION_SUMMARY.md
  - [ ] QUICK_REFERENCE.md


## 🔧 Installation Steps

### Step 1: Django Settings
- [ ] Opened saleor/settings.py
- [ ] Found INSTALLED_APPS list
- [ ] Added 'saleor.banner' to INSTALLED_APPS
- [ ] Saved settings.py

### Step 2: GraphQL API
- [ ] Opened saleor/graphql/api.py
- [ ] Added import: `from saleor.graphql.banner_queries import BannerQueries`
- [ ] Added import: `from saleor.graphql.banner_mutations import BannerMutations`
- [ ] Updated Query class to inherit from BannerQueries
- [ ] Updated Mutation class to inherit from BannerMutations
- [ ] Verified class definitions look correct
- [ ] Saved api.py

### Step 3: Database Migrations
- [ ] Opened terminal
- [ ] Ran: `python manage.py migrate banner`
- [ ] Confirmed: "Applying banner.0001_initial... OK"
- [ ] Verified no errors in output

### Step 4: Create Permission
- [ ] Opened Django shell: `python manage.py shell`
- [ ] Executed permission creation code (see SETUP.md Step 5)
- [ ] Confirmed permission was created
- [ ] Exited shell: `exit()`

### Step 5: Assign Permission to Staff Group (Optional)
- [ ] Decided if assigning to group or per-user
- [ ] If group: opened Django shell and ran group assignment (SETUP.md Step 6)
- [ ] If per-user: will assign via admin interface
- [ ] Saved and verified


## ✅ Verification Steps

### Admin Interface
- [ ] Opened Django development server: `python manage.py runserver`
- [ ] Opened browser: http://localhost:8000/admin/
- [ ] Logged in with admin account
- [ ] Navigated to "Banner Management" section
- [ ] Confirmed "Image Collections" appears
- [ ] Confirmed "Banners" appears
- [ ] No error messages

### Create Test Data
- [ ] Clicked "Image Collections" → Add
- [ ] Filled in:
  - [ ] Name: "Test Collection"
  - [ ] Channel: (selected from dropdown)
  - [ ] Is Active: (checked)
- [ ] Clicked "Save"
- [ ] Confirmed collection created successfully
- [ ] Returned to collection detail
- [ ] Added inline banner:
  - [ ] Title: "Test Banner"
  - [ ] Image: (uploaded image file)
  - [ ] Position: 0
  - [ ] Is Active: (checked)
- [ ] Clicked "Save"
- [ ] Confirmed banner created successfully

### GraphQL Endpoint
- [ ] Opened http://localhost:8000/graphql/
- [ ] Confirmed GraphQL playground loaded
- [ ] Executed test query (see next section)
- [ ] Verified results returned

#### Test GraphQL Query
```graphql
{
  imageCollections(first: 10) {
    edges {
      node {
        id
        name
      }
    }
  }
}
```
- [ ] Query executed successfully
- [ ] Results showed test collection
- [ ] No error messages

#### Test GraphQL List Banners
```graphql
{
  banners(first: 10) {
    edges {
      node {
        id
        title
        isActive
      }
    }
  }
}
```
- [ ] Query executed successfully
- [ ] Results showed test banner
- [ ] No error messages


## 🧪 Testing

### Run Unit Tests
- [ ] Opened terminal
- [ ] Ran: `pytest saleor/banner/tests.py -v`
- [ ] Confirmed all tests passed
- [ ] No errors or failures

### Run Django Tests (Alternative)
- [ ] Ran: `python manage.py test saleor.banner`
- [ ] Confirmed all tests passed
- [ ] No errors or failures

### Run Specific Test Class
- [ ] Ran: `pytest saleor/banner/tests.py::TestBannerModel -v`
- [ ] Confirmed all model tests passed


## 🔒 Permission Testing

### Assign Permission to Test User
- [ ] Logged into admin
- [ ] Went to Users section
- [ ] Opened test staff user
- [ ] Added MANAGE_BANNERS permission
- [ ] Saved user

### Test Permission Enforcement
- [ ] Logged out and logged in as test staff user
- [ ] Navigated to /admin/banner/
- [ ] Confirmed banners accessible (has permission)
- [ ] Tried to create banner
- [ ] Confirmed mutation allowed
- [ ] Logged out

### Test Permission Denied
- [ ] Created test user WITHOUT permission
- [ ] Logged in as that user
- [ ] Tried to access /admin/banner/
- [ ] Confirmed access denied
- [ ] Tried GraphQL mutation for banner
- [ ] Confirmed permission error returned


## 📊 Advanced Testing

### Scheduling Test
- [ ] Created banner with future start_date
- [ ] Checked: `activeBannersByCollection()` doesn't include it
- [ ] Waited (or used time travel in tests)
- [ ] Checked: banner now appears in active list
- [ ] Created banner with past end_date
- [ ] Checked: banner not in active list

### Key-Value Storage Test
- [ ] Created banner with key_values:
  ```graphql
  keyValues: {
    "campaign": "summer_2024"
    "discount": "50"
    "tags": ["hot", "new"]
  }
  ```
- [ ] Retrieved banner via GraphQL
- [ ] Confirmed key_values intact in response

### Custom Fields Test
- [ ] Created banner with custom fields filled
- [ ] Retrieved via GraphQL
- [ ] Confirmed all custom fields preserved

### Filtering Test
- [ ] Created multiple banners across channels
- [ ] Tested filter by channel_id
- [ ] Tested filter by is_active
- [ ] Tested filter by collection_id
- [ ] Confirmed filters working correctly


## 📖 Documentation Review

- [ ] Read QUICK_REFERENCE.md for overview
- [ ] Read SETUP.md for installation details
- [ ] Read INTEGRATION_GUIDE.md for API usage
- [ ] Bookmarked README.md for feature reference
- [ ] Found all code examples useful and clear


## 🚀 Production Preparation

### Database Backup
- [ ] Created database backup before migration
- [ ] Verified backup file exists
- [ ] Tested backup restore (optional)

### Settings Verification
- [ ] Confirmed MEDIA_ROOT configured
- [ ] Confirmed MEDIA_URL configured
- [ ] Confirmed INSTALLED_APPS correct
- [ ] Confirmed no duplicate app entries

### Security Checklist
- [ ] MANAGE_BANNERS permission created
- [ ] Permission assigned to appropriate staff groups
- [ ] Tested permission enforcement
- [ ] No hardcoded credentials in code
- [ ] No sensitive data in migrations

### Performance Checklist
- [ ] Verified database indexes created
- [ ] Tested queries with large datasets (optional)
- [ ] Confirmed select_related used appropriately
- [ ] No N+1 query problems

### Documentation Checklist
- [ ] All documentation files present
- [ ] README.md reviewed
- [ ] SETUP.md followed exactly
- [ ] Team has access to documentation
- [ ] Support contacts identified


## 📝 Deployment Notes

### Pre-Deployment
- [ ] All tests passing locally
- [ ] Code reviewed
- [ ] Permission setup verified
- [ ] Database backup created
- [ ] Rollback plan documented

### Deployment
- [ ] Deployed code to staging
- [ ] Ran migrations on staging
- [ ] Created permission on staging
- [ ] Tested in staging environment
- [ ] Verified GraphQL queries work
- [ ] Verified admin interface works
- [ ] Obtained deployment approval

### Post-Deployment
- [ ] Verified app in production
- [ ] Tested GraphQL endpoint
- [ ] Tested admin interface
- [ ] Monitored for errors
- [ ] Confirmed no performance issues
- [ ] Updated team of successful deployment


## 🎯 First Production Banners

- [ ] Created first image collection in production
- [ ] Created first banner in production
- [ ] Tested scheduling if using dates
- [ ] Verified banners appear in GraphQL queries
- [ ] Tested banner links
- [ ] Confirmed images display correctly
- [ ] Monitored performance


## 📊 Maintenance & Monitoring

- [ ] Set up logs for banner operations
- [ ] Set up alerts for failures
- [ ] Monitored database size growth
- [ ] Created backup routine for banner data
- [ ] Documented any customizations made
- [ ] Scheduled performance reviews


## ✨ Optional Enhancements (Post-Launch)

- [ ] Added custom banner types (video, popup, etc.)
- [ ] Implemented banner analytics tracking
- [ ] Added A/B testing capability
- [ ] Integrated with email campaigns
- [ ] Created banner preview functionality
- [ ] Added banner performance dashboard
- [ ] Implemented banner versioning/history
- [ ] Added bulk banner operations
- [ ] Created banner templates
- [ ] Added banner scheduling via Celery tasks


## 🎉 Sign-Off

- [ ] All checklist items completed
- [ ] System tested and verified
- [ ] Documentation reviewed
- [ ] Team trained on system
- [ ] Monitoring set up
- [ ] Ready for production use

**Date Completed:** _______________

**Completed By:** _______________

**Notes & Issues Encountered:**
```
[Space for notes about any issues or customizations made]
```


## 📞 Support Contacts

**For Documentation Questions:**
- Refer to QUICK_REFERENCE.md

**For Installation Issues:**
- See SETUP.md troubleshooting section

**For API Usage Questions:**
- See INTEGRATION_GUIDE.md

**For Code Issues:**
- Check tests.py for usage examples
- Review inline code comments
- Consult Django documentation

---

**Congratulations on implementing Banner Management System! 🎉**

For ongoing support, maintain this checklist and update as you make changes.
"""

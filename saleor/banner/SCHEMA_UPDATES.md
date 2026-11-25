# Schema Updates Summary

## Changes Made

### 1. Channel Global ID handling in `createImageCollection`

**File:** `saleor/graphql/banner_mutations.py`

**What changed:**
- `channelId` now validates as GraphQL `Channel` global ID using:
  - `from_global_id_or_error(channel_id, "Channel", raise_error=True)`
- Handles both invalid ID format/type and missing channel record.

**Why:**
- Input is GraphQL global ID (`Q2hhbm5lbDox`) while DB lookup needs decoded PK.

---

### 2. Connection-safe list resolvers for banners and image collections

**File:** `saleor/graphql/banner_queries.py`

**What changed:**
- `resolve_banners` and `resolve_image_collections` now follow Saleor connection pattern:
  - `filter_connection_queryset(...)`
  - `create_connection_slice(...)`

**Why:**
- Prevents `null` connection edge errors and ensures Relay pagination behavior is consistent.

---

### 3. Added `banners` connection on `ImageCollectionType`

**File:** `saleor/graphql/banner_types.py`

**What changed:**
- Added nested `banners` connection field.
- Added resolver using `create_connection_slice(...)`.

**Why:**
- Enables queries like:
  - `imageCollections { edges { node { banners(first: 10) { ... } } } }`

---

### 4. Banner image upload-first APIs

**File:** `saleor/graphql/banner_mutations.py`

**New mutations:**
- `uploadBannerImage(file: Upload!, folder: String)`
  - Uploads to media storage under `banners/` (or a subfolder).
  - Returns `fileKey` + `uploadedFile { url, contentType }`.
- `deleteBannerImage(fileKey: String!, force: Boolean = false)`
  - Deletes file from storage.
  - Blocks deletion when file is in use unless `force: true`.

**Additional mutation updates:**
- `createBanner` accepts `imageKey` (preferred) and keeps deprecated `image` support.
- `updateBanner` accepts `imageKey` (preferred) and keeps deprecated `image` support.

**New banner error codes:**
- `IMAGE_UPLOAD_ERROR`
- `IMAGE_NOT_FOUND`
- `IMAGE_IN_USE`

---

### 5. Banner image URL normalization

**File:** `saleor/graphql/banner_types.py`

**What changed:**
- Added `BannerType.resolve_image` to return usable media URL when value is a storage key.

---

### 6. Practical docs updated

**File:** `saleor/banner/PRACTICAL_EXAMPLES.md`

**What changed:**
- Added upload-first flow:
  1. `uploadBannerImage`
  2. `createBanner(imageKey: ...)`
  3. optional `deleteBannerImage`
- Updated list/query examples and common errors.

---

## Migration Status

**✅ NO MIGRATION REQUIRED**

Reason: Changes are in GraphQL schema/resolvers/mutations and docs only.

---

## Testing Checklist

- [ ] Restart API server after schema changes
- [ ] `createImageCollection` with global `channelId`
- [ ] `imageCollections(first: 10)` returns non-null edges
- [ ] Nested `banners(first: 10)` works under `imageCollections`
- [ ] `uploadBannerImage` multipart upload succeeds
- [ ] `createBanner` with `imageKey` succeeds
- [ ] `updateBanner` with `imageKey` succeeds
- [ ] `deleteBannerImage` blocks when in use (`IMAGE_IN_USE`)
- [ ] `deleteBannerImage(force: true)` deletes file

---

## File Locations

- Backend mutations: `/saleor/graphql/banner_mutations.py`
- Backend queries: `/saleor/graphql/banner_queries.py`
- GraphQL types: `/saleor/graphql/banner_types.py`
- GraphQL errors: `/saleor/graphql/banner_errors.py`
- Practical examples: `/saleor/banner/PRACTICAL_EXAMPLES.md`
- This file: `/saleor/banner/SCHEMA_UPDATES.md`

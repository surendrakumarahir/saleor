# Practical Examples: Banner Management GraphQL API

Complete working examples for creating collections, banners, and managing them.

ID behavior in this custom schema is mixed:
- `createImageCollection.channelId` input expects a GraphQL global Channel ID (e.g. `Q2hhbm5lbDox`)
- Returned `imageCollection.id` and `imageCollection.channelId` are plain DB IDs as strings (e.g. `"3"`, `"1"`)
- Banner and collection `id` arguments in update/delete mutations are also plain DB IDs as strings

---

## 1. Create Image Collection

### Mutation
```graphql
mutation CreateImageCollection(
  $channelId: ID!
  $name: String!
  $description: String
  $isActive: Boolean
) {
  createImageCollection(
    channelId: $channelId
    name: $name
    description: $description
    isActive: $isActive
  ) {
    imageCollection {
      id
      name
      channelId
      isActive
    }
    errors { field message code }
  }
}
```

### Variables (with base64-encoded Channel ID)
```json
{
  "channelId": "Q2hhbm5lbDox",
  "name": "Flash Sale - June 15",
  "description": "One-day mega sale",
  "isActive": true
}
```

### Expected Response
```json
{
  "data": {
    "createImageCollection": {
      "imageCollection": {
        "id": "3",
        "name": "Flash Sale - June 15",
        "channelId": "1",
        "isActive": true
      },
      "errors": []
    }
  }
}
```

### What to do next
1. Save `imageCollection.id` from the response (example: `"3"`).
2. Upload image with `uploadBannerImage` and save returned `fileKey`.
3. Use `collectionId` + `imageKey` in `createBanner`.
4. Query `imageCollection(id: "3")` or `imageCollections(...)` to verify it.

---

## 2. Update Image Collection

### Mutation
```graphql
mutation UpdateImageCollection(
  $id: ID!
  $name: String
  $description: String
  $isActive: Boolean
) {
  updateImageCollection(
    id: $id
    name: $name
    description: $description
    isActive: $isActive
  ) {
    imageCollection {
      id
      name
      description
      isActive
    }
    errors { field message code }
  }
}
```

### Variables
```json
{
  "id": "3",
  "name": "Summer Flash Sale - Updated",
  "description": "Updated description for the sale",
  "isActive": true
}
```

---

## 3. Upload Banner Image (First Step)

`uploadBannerImage` uses multipart GraphQL upload and stores the file in media storage
under `banners/` by default.

### Mutation
```graphql
mutation UploadBannerImage($file: Upload!, $folder: String) {
  uploadBannerImage(file: $file, folder: $folder) {
    fileKey
    uploadedFile {
      url
      contentType
    }
    errors {
      field
      message
      code
    }
  }
}
```

### Variables
`$file` must be sent via GraphQL multipart request spec. Example variables:
```json
{
  "file": null,
  "folder": "banners/summer-2026"
}
```

### Expected Response
```json
{
  "data": {
    "uploadBannerImage": {
      "fileKey": "banners/summer-2026/sale_banner_a1b2c3d4.jpg",
      "uploadedFile": {
        "url": "https://your-domain/media/banners/summer-2026/sale_banner_a1b2c3d4.jpg",
        "contentType": "image/jpeg"
      },
      "errors": []
    }
  }
}
```

Save `fileKey` from this response and use it as `imageKey` in banner create/update.

---

## 4. Create Banner in Collection

### Mutation
```graphql
mutation CreateBanner(
  $collectionId: ID!
  $title: String!
  $imageKey: String!
  $description: String
  $altText: String
  $linkUrl: String
  $linkText: String
  $customField1: String
  $customField2: String
  $customField3: String
  $isActive: Boolean
  $startDate: DateTime
  $endDate: DateTime
) {
  createBanner(
    collectionId: $collectionId
    title: $title
    imageKey: $imageKey
    description: $description
    altText: $altText
    linkUrl: $linkUrl
    linkText: $linkText
    customField1: $customField1
    customField2: $customField2
    customField3: $customField3
    isActive: $isActive
    startDate: $startDate
    endDate: $endDate
  ) {
    banner {
      id
      title
      image
      isActive
      position
    }
    errors { field message code }
  }
}
```

### Variables
```json
{
  "collectionId": "3",
  "title": "50% Off All Items",
  "imageKey": "banners/summer-2026/sale_banner_a1b2c3d4.jpg",
  "description": "Limited time offer - 50% off everything",
  "altText": "Summer sale banner 50% off",
  "linkUrl": "https://example.com/sale",
  "linkText": "Shop Now",
  "customField1": "summer_2024",
  "customField2": "featured",
  "customField3": "tier_1",
  "isActive": true,
  "startDate": "2024-06-15T00:00:00Z",
  "endDate": "2024-06-16T23:59:59Z"
}
```

### Expected Response
```json
{
  "data": {
    "createBanner": {
      "banner": {
        "id": "1",
        "title": "50% Off All Items",
        "image": "https://your-domain/media/banners/summer-2026/sale_banner_a1b2c3d4.jpg",
        "isActive": true,
        "position": 1
      },
      "errors": []
    }
  }
}
```

---

## 5. Update Banner

### Mutation
```graphql
mutation UpdateBanner(
  $id: ID!
  $title: String
  $imageKey: String
  $description: String
  $linkUrl: String
  $linkText: String
  $isActive: Boolean
) {
  updateBanner(
    id: $id
    title: $title
    imageKey: $imageKey
    description: $description
    linkUrl: $linkUrl
    linkText: $linkText
    isActive: $isActive
  ) {
    banner {
      id
      title
      description
      isActive
    }
    errors { field message code }
  }
}
```

### Variables
```json
{
  "id": "1",
  "title": "60% Off - Extended!",
  "imageKey": "banners/summer-2026/sale_banner_v2_e5f6a7b8.jpg",
  "description": "Sale extended! Now 60% off all items",
  "linkUrl": "https://example.com/mega-sale",
  "linkText": "Shop Extended Sale",
  "isActive": true
}
```

---

## 6. Delete Banner

### Mutation
```graphql
mutation DeleteBanner($id: ID!) {
  deleteBanner(id: $id) {
    errors { field message code }
  }
}
```

### Variables
```json
{
  "id": "1"
}
```

---

## 7. Delete Uploaded Banner Image

Delete the physical file from storage. By default this mutation blocks deletion
if the image is still referenced by banners.

### Mutation
```graphql
mutation DeleteBannerImage($fileKey: String!, $force: Boolean) {
  deleteBannerImage(fileKey: $fileKey, force: $force) {
    success
    errors {
      field
      message
      code
    }
  }
}
```

### Variables
```json
{
  "fileKey": "banners/summer-2026/sale_banner_a1b2c3d4.jpg",
  "force": false
}
```

---

## 8. Delete Image Collection

### Mutation
```graphql
mutation DeleteImageCollection($id: ID!) {
  deleteImageCollection(id: $id) {
    errors { field message code }
  }
}
```

### Variables
```json
{
  "id": "3"
}
```

---

## 9. Get ImageCollection Listing

Use `imageCollections` with the `filter` argument.

### Query (all collections)
```graphql
query GetImageCollections {
  imageCollections(first: 10) {
    edges {
      node {
        id
        name
        description
        channelId
        isActive
      }
    }
  }
}
```

### Query (filtered listing)
```graphql
query GetImageCollections($filter: ImageCollectionFilterInput) {
  imageCollections(filter: $filter, first: 10) {
    edges {
      node {
        id
        name
        description
        channelId
        isActive
      }
    }
  }
}
```

### Variables (filtered)
```json
{
  "filter": {
    "channelId": "1",
    "isActive": true,
    "name": "Flash"
  }
}
```

### Example Response
```json
{
  "data": {
    "imageCollections": {
      "edges": [
        {
          "node": {
            "id": "3",
            "name": "Flash Sale - June 15",
            "description": "One-day mega sale",
            "channelId": "1",
            "isActive": true
          }
        }
      ]
    }
  }
}
```

---

## 10. Query Collections with Banners

### Query
```graphql
query GetImageCollectionsWithBanners($filter: ImageCollectionFilterInput) {
  imageCollections(filter: $filter, first: 10) {
    edges {
      node {
        id
        name
        description
        channelId
        isActive
        banners(first: 10) {
          edges {
            node {
              id
              title
              image
              isActive
              position
              startDate
              endDate
            }
          }
        }
      }
    }
  }
}
```

### Variables
```json
{
  "filter": {
    "channelId": "1",
    "isActive": true
  }
}
```

---

## 11. Query Single Collection

### Query
```graphql
query GetImageCollection($id: ID!) {
  imageCollection(id: $id) {
    id
    name
    description
    channelId
    isActive
    createdAt
    updatedAt
  }
}
```

### Variables
```json
{
  "id": "3"
}
```

---

## Important Notes

### ID Format Reference
- **Channel ID for `createImageCollection` input**: use global ID, e.g. `Q2hhbm5lbDox` (`Channel:1`)
- **Collection IDs in responses / update / delete**: plain DB ID string, e.g. `"3"`
- **Banner IDs in responses / update / delete**: plain DB ID string, e.g. `"1"`
- **Banner image storage key**: use `uploadBannerImage.fileKey` (e.g. `banners/summer-2026/file.jpg`)

### Error Handling
All mutations return an `errors` array:
```json
{
  "errors": [
    {
      "field": "name",
      "message": "Name is required.",
      "code": "REQUIRED_FIELD_MISSING"
    }
  ]
}
```

### Permissions
- Requires `banner.manage_banners` permission
- Only staff users with this permission can modify banners

### DateTime Format
Use ISO 8601 format for dates:
- Example: `2024-06-15T00:00:00Z`
- Can include timezone information

---

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Cannot query field "collection"` | Wrong field name in response | Use `imageCollection` instead of `collection` |
| `Channel not found` | Invalid channel ID | Verify the base64-encoded channel ID exists |
| `Field 'id' expected a number` | Using base64 ID for collection/banner mutations | Use plain numeric string IDs returned by API (e.g. `"3"`, `"1"`) |
| `Unknown argument "channel" on field "imageCollections"` | Wrong listing argument | Use `imageCollections(filter: {...})`, not `channel:` |
| `Cannot query field "channel"` | Wrong field name | Use `channelId` instead of `channel { id name }` |
| `IMAGE_UPLOAD_ERROR` | Invalid multipart payload or invalid file type | Ensure GraphQL multipart upload format and valid image MIME/extension |
| `IMAGE_IN_USE` | Trying to delete file used by banner records | Remove/update dependent banners first or pass `force: true` |
| `IMAGE_NOT_FOUND` | File key does not exist in storage | Verify exact `fileKey` from upload response |
| `REQUIRED_FIELD_MISSING` | Missing required field | Check mutation Arguments section for required fields |

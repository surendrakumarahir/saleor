"""GraphQL mutations for Blog Management System."""

import json
import posixpath
import re
import secrets
import graphene
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from saleor.blog.models import (
    BlogAuditLog,
    BlogAuthor,
    BlogCategory,
    BlogComment,
    BlogCommentStatus,
    BlogPost,
    BlogPostFAQ,
    BlogPostRevision,
    BlogPostStatus,
    BlogRedirect,
    BlogTag,
)
from saleor.core.error_codes import UploadErrorCode
from saleor.core.utils import build_absolute_uri
from saleor.graphql.blog_errors import BlogError, BlogErrorCode
from saleor.graphql.blog_types import (
    BlogAuthorType,
    BlogCategoryType,
    BlogCommentStatusEnum,
    BlogCommentType,
    BlogPostRevisionType,
    BlogPostStatusEnum,
    BlogPostType,
    BlogTagType,
)
from saleor.graphql.core.types import Upload
from saleor.graphql.core.scalars import JSON
from saleor.graphql.core.utils import add_hash_to_file_name, from_global_id_or_error
from saleor.graphql.core.validators.file import validate_upload_file
from saleor.graphql.decorators import one_of_permissions_required

BLOG_PERMISSIONS = ["blog.manage_blog", "page.manage_pages"]


def _resolve_upload_from_request(info, file):
    if isinstance(file, UploadedFile):
        return file
    if hasattr(info.context, "FILES"):
        if file in info.context.FILES:
            return info.context.FILES[file]
        if str(file) in info.context.FILES:
            return info.context.FILES[str(file)]
    return file


def _get_input_data(input_obj):
    if isinstance(input_obj, dict):
        return input_obj
    if hasattr(input_obj, "kwargs"):
        return input_obj.kwargs
    res = {}
    for k in dir(input_obj):
        if k.startswith("_"):
            continue
        val = getattr(input_obj, k)
        if not isinstance(val, (graphene.Scalar, graphene.Field, graphene.InputField)) and not callable(val):
            res[k] = val
    return res


def _parse_id(id_val, type_name):
    if not id_val:
        return None
    try:
        _, pk = from_global_id_or_error(str(id_val), type_name, raise_error=False)
        return int(pk) if pk else int(id_val)
    except Exception:
        try:
            return int(id_val)
        except Exception:
            return None


def _log_audit(info, action, target_type, target_id, details=None):
    user = info.context.user if info.context.user and info.context.user.is_authenticated else None
    BlogAuditLog.objects.create(
        actor=user,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        details=details or {},
    )


def _sync_post_faqs(post: BlogPost, faqs_input):
    if faqs_input is None:
        return

    with transaction.atomic():
        existing_faqs = {faq.id: faq for faq in post.faqs.all()}
        retained_ids = set()

        for idx, raw_faq in enumerate(faqs_input):
            faq_data = _get_input_data(raw_faq)
            q = (faq_data.get("question") or "").strip()
            a = (faq_data.get("answer") or "").strip()
            if not q and not a:
                continue

            raw_id = faq_data.get("id")
            faq_pk = _parse_id(raw_id, "BlogPostFAQ") if raw_id else None
            sort_order = faq_data.get("sort_order") if faq_data.get("sort_order") is not None else idx

            if faq_pk and faq_pk in existing_faqs:
                faq_obj = existing_faqs[faq_pk]
                faq_obj.question = q
                faq_obj.answer = a
                faq_obj.sort_order = sort_order
                faq_obj.save(update_fields=["question", "answer", "sort_order", "updated_at"])
                retained_ids.add(faq_pk)
            else:
                new_faq = BlogPostFAQ.objects.create(
                    post=post,
                    question=q,
                    answer=a,
                    sort_order=sort_order,
                )
                retained_ids.add(new_faq.id)

        post.faqs.exclude(id__in=retained_ids).delete()


class BlogPostFAQInput(graphene.InputObjectType):
    id = graphene.ID(description="FAQ ID if updating existing FAQ.")
    question = graphene.String(required=True, description="FAQ question.")
    answer = graphene.String(required=True, description="FAQ answer.")
    sort_order = graphene.Int(default_value=0, description="Display order.")


class BlogPostCreateInput(graphene.InputObjectType):
    title = graphene.String(required=True, description="Post title.")
    slug = graphene.String(description="Unique post slug.")
    excerpt = graphene.String(description="Short summary.")
    content = graphene.String(description="Structured content (JSON or markdown).")
    content_html = graphene.String(description="Pre-rendered HTML.")
    status = BlogPostStatusEnum(default_value=BlogPostStatus.DRAFT)
    author_id = graphene.ID(description="Author ID.")
    primary_category_id = graphene.ID(description="Primary category ID.")
    category_ids = graphene.List(graphene.ID, description="Additional category IDs.")
    tag_ids = graphene.List(graphene.ID, description="Tag IDs.")
    featured_image = graphene.String(description="Featured image storage key or URL.")
    featured_image_alt = graphene.String()
    featured_image_caption = graphene.String()
    seo_title = graphene.String()
    seo_description = graphene.String()
    canonical_url = graphene.String()
    robots_index = graphene.Boolean(default_value=True)
    robots_follow = graphene.Boolean(default_value=True)
    og_title = graphene.String()
    og_description = graphene.String()
    og_image = graphene.String()
    is_featured = graphene.Boolean(default_value=False)
    reading_time_minutes = graphene.Int()
    allow_comments = graphene.Boolean(default_value=False)
    published_at = graphene.String()
    scheduled_at = graphene.String()
    recommended_books = JSON()
    table_of_contents = JSON()
    product_collections = JSON()
    faqs = graphene.List(BlogPostFAQInput, description="Optional dynamic list of FAQs.")


class BlogPostUpdateInput(graphene.InputObjectType):
    title = graphene.String()
    slug = graphene.String()
    excerpt = graphene.String()
    content = graphene.String()
    content_html = graphene.String()
    status = BlogPostStatusEnum()
    author_id = graphene.ID()
    primary_category_id = graphene.ID()
    category_ids = graphene.List(graphene.ID)
    tag_ids = graphene.List(graphene.ID)
    featured_image = graphene.String()
    featured_image_alt = graphene.String()
    featured_image_caption = graphene.String()
    seo_title = graphene.String()
    seo_description = graphene.String()
    canonical_url = graphene.String()
    robots_index = graphene.Boolean()
    robots_follow = graphene.Boolean()
    og_title = graphene.String()
    og_description = graphene.String()
    og_image = graphene.String()
    is_featured = graphene.Boolean()
    reading_time_minutes = graphene.Int()
    allow_comments = graphene.Boolean()
    published_at = graphene.String()
    scheduled_at = graphene.String()
    recommended_books = JSON()
    table_of_contents = JSON()
    product_collections = JSON()
    faqs = graphene.List(BlogPostFAQInput, description="Optional dynamic list of FAQs.")


class BlogPostCreate(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        input = BlogPostCreateInput(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, input):
        title = input.title.strip()
        slug = (input.slug or slugify(title)).strip()

        if not slug:
            slug = slugify(title) or f"post-{int(timezone.now().timestamp())}"

        if BlogPost.objects.filter(slug=slug).exists():
            return BlogPostCreate(
                errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Slug already exists.", field="slug")]
            )

        post = BlogPost(
            title=title,
            slug=slug,
            excerpt=input.excerpt or "",
            content=input.content or "",
            content_html=input.content_html or "",
            status=input.status or BlogPostStatus.DRAFT,
            featured_image_alt=input.featured_image_alt or "",
            featured_image_caption=input.featured_image_caption or "",
            seo_title=input.seo_title or "",
            seo_description=input.seo_description or "",
            canonical_url=input.canonical_url,
            robots_index=input.robots_index if input.robots_index is not None else True,
            robots_follow=input.robots_follow if input.robots_follow is not None else True,
            og_title=input.og_title or "",
            og_description=input.og_description or "",
            is_featured=bool(input.is_featured),
            allow_comments=bool(input.allow_comments),
            created_by=info.context.user if info.context.user.is_authenticated else None,
            updated_by=info.context.user if info.context.user.is_authenticated else None,
        )

        if input.featured_image:
            post.featured_image = input.featured_image
        if input.og_image:
            post.og_image = input.og_image

        if input.author_id:
            author_pk = _parse_id(input.author_id, "BlogAuthor")
            post.author = BlogAuthor.objects.filter(pk=author_pk).first()

        if input.primary_category_id:
            cat_pk = _parse_id(input.primary_category_id, "BlogCategory")
            post.primary_category = BlogCategory.objects.filter(pk=cat_pk).first()

        if input.reading_time_minutes:
            post.reading_time_minutes = input.reading_time_minutes
        else:
            post.calculate_reading_time()

        if input.status == BlogPostStatus.PUBLISHED:
            post.published_at = timezone.now() if not input.published_at else input.published_at
        elif input.published_at:
            post.published_at = input.published_at

        if input.scheduled_at:
            post.scheduled_at = input.scheduled_at

        if input.recommended_books:
            try:
                post.recommended_books = json.loads(input.recommended_books) if isinstance(input.recommended_books, str) else input.recommended_books
            except Exception:
                pass

        if input.table_of_contents:
            try:
                post.table_of_contents = json.loads(input.table_of_contents) if isinstance(input.table_of_contents, str) else input.table_of_contents
            except Exception:
                pass

        if hasattr(input, "product_collections") and input.product_collections is not None:
            try:
                post.product_collections = json.loads(input.product_collections) if isinstance(input.product_collections, str) else input.product_collections
            except Exception:
                pass

        post.save()

        if input.category_ids:
            cat_pks = [_parse_id(cid, "BlogCategory") for cid in input.category_ids if cid]
            post.categories.set([c for c in cat_pks if c])

        if input.tag_ids:
            tag_pks = [_parse_id(tid, "BlogTag") for tid in input.tag_ids if tid]
            post.tags.set([t for t in tag_pks if t])

        if hasattr(input, "faqs") and input.faqs is not None:
            _sync_post_faqs(post, input.faqs)

        # Create initial revision snapshot
        post.create_revision(info.context.user)
        _log_audit(info, "CREATE", "BlogPost", post.id, {"title": post.title, "slug": post.slug})

        return BlogPostCreate(post=post, errors=[])


class BlogPostUpdate(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        input = BlogPostUpdateInput(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, input):
        pk = _parse_id(id, "BlogPost")
        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostUpdate(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        data = _get_input_data(input)

        if "title" in data and data["title"] is not None:
            post.title = str(data["title"]).strip()

        if "slug" in data and data["slug"] is not None:
            new_slug = str(data["slug"]).strip()
            if new_slug != post.slug:
                if BlogPost.objects.filter(slug=new_slug).exclude(pk=post.pk).exists():
                    return BlogPostUpdate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Slug already exists.", field="slug")])
                # Record redirect mapping
                BlogRedirect.objects.update_or_create(
                    old_slug=post.slug,
                    defaults={"destination_slug": new_slug, "is_permanent": True},
                )
                post.slug = new_slug

        if "excerpt" in data:
            post.excerpt = data["excerpt"] or ""
        if "content" in data:
            post.content = data["content"] or ""
        if "content_html" in data:
            post.content_html = data["content_html"] or ""
        if "status" in data and data["status"] is not None:
            post.status = data["status"]
            if data["status"] == BlogPostStatus.PUBLISHED and not post.published_at:
                post.published_at = timezone.now()
        if "featured_image" in data:
            val = str(data["featured_image"]).strip() if data["featured_image"] else None
            post.featured_image = val
        if "featured_image_alt" in data:
            post.featured_image_alt = data["featured_image_alt"] or ""
        if "featured_image_caption" in data:
            post.featured_image_caption = data["featured_image_caption"] or ""
        if "seo_title" in data:
            post.seo_title = data["seo_title"] or ""
        if "seo_description" in data:
            post.seo_description = data["seo_description"] or ""
        if "canonical_url" in data:
            post.canonical_url = data["canonical_url"] or None
        if "robots_index" in data and data["robots_index"] is not None:
            post.robots_index = data["robots_index"]
        if "robots_follow" in data and data["robots_follow"] is not None:
            post.robots_follow = data["robots_follow"]
        if "og_title" in data:
            post.og_title = data["og_title"] or ""
        if "og_description" in data:
            post.og_description = data["og_description"] or ""
        if "og_image" in data:
            val = str(data["og_image"]).strip() if data["og_image"] else None
            post.og_image = val
        if "is_featured" in data and data["is_featured"] is not None:
            post.is_featured = data["is_featured"]
        if "allow_comments" in data and data["allow_comments"] is not None:
            post.allow_comments = data["allow_comments"]
        if "reading_time_minutes" in data and data["reading_time_minutes"] is not None:
            post.reading_time_minutes = data["reading_time_minutes"]
        elif "content" in data or "content_html" in data:
            post.calculate_reading_time()

        if "author_id" in data:
            author_pk = _parse_id(data["author_id"], "BlogAuthor")
            post.author = BlogAuthor.objects.filter(pk=author_pk).first() if author_pk else None

        if "primary_category_id" in data:
            cat_pk = _parse_id(data["primary_category_id"], "BlogCategory")
            post.primary_category = BlogCategory.objects.filter(pk=cat_pk).first() if cat_pk else None

        if "published_at" in data and data["published_at"] is not None:
            post.published_at = data["published_at"]
        if "scheduled_at" in data and data["scheduled_at"] is not None:
            post.scheduled_at = data["scheduled_at"]

        if "recommended_books" in data and data["recommended_books"] is not None:
            try:
                post.recommended_books = json.loads(data["recommended_books"]) if isinstance(data["recommended_books"], str) else data["recommended_books"]
            except Exception:
                pass

        if "table_of_contents" in data and data["table_of_contents"] is not None:
            try:
                post.table_of_contents = json.loads(data["table_of_contents"]) if isinstance(data["table_of_contents"], str) else data["table_of_contents"]
            except Exception:
                pass

        if "product_collections" in data and data["product_collections"] is not None:
            try:
                post.product_collections = json.loads(data["product_collections"]) if isinstance(data["product_collections"], str) else data["product_collections"]
            except Exception:
                pass

        post.updated_by = info.context.user if info.context.user.is_authenticated else None
        post.revision_number += 1
        post.save()

        if "category_ids" in data and data["category_ids"] is not None:
            cat_pks = [_parse_id(cid, "BlogCategory") for cid in data["category_ids"] if cid]
            post.categories.set([c for c in cat_pks if c])

        if "tag_ids" in data and data["tag_ids"] is not None:
            tag_pks = [_parse_id(tid, "BlogTag") for tid in data["tag_ids"] if tid]
            post.tags.set([t for t in tag_pks if t])

        if "faqs" in data and data["faqs"] is not None:
            _sync_post_faqs(post, data["faqs"])

        # Snapshot new revision
        post.create_revision(info.context.user)
        _log_audit(info, "UPDATE", "BlogPost", post.id, {"title": post.title, "revision": post.revision_number})

        return BlogPostUpdate(post=post, errors=[])


class BlogPostDelete(graphene.Mutation):
    success = graphene.Boolean(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogPost")
        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostDelete(success=False, errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        post_id = post.id
        title = post.title
        post.delete()
        _log_audit(info, "DELETE", "BlogPost", post_id, {"title": title})
        return BlogPostDelete(success=True, errors=[])


class BlogPostPublish(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogPost")
        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostPublish(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        post.status = BlogPostStatus.PUBLISHED
        if not post.published_at:
            post.published_at = timezone.now()
        post.save(update_fields=["status", "published_at", "updated_at"])
        _log_audit(info, "PUBLISH", "BlogPost", post.id)
        return BlogPostPublish(post=post, errors=[])


class BlogPostSchedule(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        scheduled_at = graphene.String(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, scheduled_at):
        pk = _parse_id(id, "BlogPost")
        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostSchedule(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        post.status = BlogPostStatus.SCHEDULED
        post.scheduled_at = scheduled_at
        post.save(update_fields=["status", "scheduled_at", "updated_at"])
        _log_audit(info, "SCHEDULE", "BlogPost", post.id, {"scheduled_at": str(scheduled_at)})
        return BlogPostSchedule(post=post, errors=[])


class BlogPostUnpublish(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogPost")
        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostUnpublish(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        post.status = BlogPostStatus.DRAFT
        post.save(update_fields=["status", "updated_at"])
        _log_audit(info, "UNPUBLISH", "BlogPost", post.id)
        return BlogPostUnpublish(post=post, errors=[])


class BlogPostArchive(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogPost")
        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostArchive(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        post.status = BlogPostStatus.ARCHIVED
        post.save(update_fields=["status", "updated_at"])
        _log_audit(info, "ARCHIVE", "BlogPost", post.id)
        return BlogPostArchive(post=post, errors=[])


class BlogPostDuplicate(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogPost")
        original = BlogPost.objects.filter(pk=pk).first()
        if not original:
            return BlogPostDuplicate(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        base_slug = f"{original.slug}-copy"
        slug = base_slug
        count = 1
        while BlogPost.objects.filter(slug=slug).exists():
            count += 1
            slug = f"{base_slug}-{count}"

        clone = BlogPost.objects.create(
            title=f"{original.title} (Copy)",
            slug=slug,
            excerpt=original.excerpt,
            content=original.content,
            content_html=original.content_html,
            status=BlogPostStatus.DRAFT,
            author=original.author,
            primary_category=original.primary_category,
            featured_image=original.featured_image,
            featured_image_alt=original.featured_image_alt,
            featured_image_caption=original.featured_image_caption,
            seo_title=original.seo_title,
            seo_description=original.seo_description,
            robots_index=original.robots_index,
            robots_follow=original.robots_follow,
            og_title=original.og_title,
            og_description=original.og_description,
            og_image=original.og_image,
            is_featured=False,
            reading_time_minutes=original.reading_time_minutes,
            recommended_books=original.recommended_books,
            table_of_contents=original.table_of_contents,
            created_by=info.context.user if info.context.user.is_authenticated else None,
        )
        clone.categories.set(original.categories.all())
        clone.tags.set(original.tags.all())
        clone.create_revision(info.context.user)
        _log_audit(info, "DUPLICATE", "BlogPost", clone.id, {"original_id": original.id})

        return BlogPostDuplicate(post=clone, errors=[])


class BlogPostRestoreRevision(graphene.Mutation):
    post = graphene.Field(BlogPostType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        revision_id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, revision_id):
        pk = _parse_id(id, "BlogPost")
        rev_pk = _parse_id(revision_id, "BlogPostRevision")

        post = BlogPost.objects.filter(pk=pk).first()
        if not post:
            return BlogPostRestoreRevision(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Post not found.", field="id")])

        rev = BlogPostRevision.objects.filter(pk=rev_pk, post=post).first()
        if not rev:
            return BlogPostRestoreRevision(errors=[BlogError(code=BlogErrorCode.REVISION_NOT_FOUND, message="Revision not found.", field="revision_id")])

        post.title = rev.title
        post.excerpt = rev.excerpt
        post.content = rev.content
        post.content_html = rev.content_html
        post.revision_number += 1
        post.updated_by = info.context.user if info.context.user.is_authenticated else None
        post.save(update_fields=["title", "excerpt", "content", "content_html", "revision_number", "updated_by", "updated_at"])

        post.create_revision(info.context.user)
        _log_audit(info, "RESTORE_REVISION", "BlogPost", post.id, {"revision_number": rev.revision_number})

        return BlogPostRestoreRevision(post=post, errors=[])


class UploadBlogMedia(graphene.Mutation):
    file_url = graphene.String(description="Absolute URL of uploaded file.")
    storage_key = graphene.String(description="Storage key of uploaded file.")
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        file = Upload(required=True, description="Image file to upload.")
        folder = graphene.String(default_value="posts", description="Folder under media/blog (e.g., posts, authors).")

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, file, folder="posts"):
        try:
            upload_file = _resolve_upload_from_request(info, file)
            if not upload_file:
                raise ValidationError("Received an empty file.")

            validate_upload_file(upload_file, UploadErrorCode, "file")

            clean_folder = (folder or "posts").strip().strip("/")
            if clean_folder not in {"posts", "authors", "og"}:
                clean_folder = "posts"

            target_dir = posixpath.join("blog", clean_folder)
            if hasattr(upload_file, "_name") and upload_file._name:
                upload_file._name = upload_file._name.replace(" ", "_")
                add_hash_to_file_name(upload_file)
                file_name = upload_file.name
            else:
                base, ext = posixpath.splitext(getattr(upload_file, "name", "upload.jpg") or "upload.jpg")
                base = base.replace(" ", "_")
                file_name = f"{base}_{secrets.token_hex(4)}{ext}"

            storage_key = posixpath.join(target_dir, file_name)
            saved_key = default_storage.save(storage_key, upload_file)
            file_url = build_absolute_uri(default_storage.url(saved_key))

            return UploadBlogMedia(file_url=file_url, storage_key=saved_key, errors=[])
        except ValidationError as e:
            msg = str(e)
            if hasattr(e, "message_dict"):
                messages = []
                for field_errs in e.message_dict.values():
                    if isinstance(field_errs, (list, tuple)):
                        messages.extend([str(item) for item in field_errs])
                    else:
                        messages.append(str(field_errs))
                msg = "; ".join(messages)
            elif hasattr(e, "messages"):
                msg = "; ".join(e.messages)
            elif hasattr(e, "message"):
                msg = e.message
            return UploadBlogMedia(
                errors=[BlogError(code=BlogErrorCode.MEDIA_UPLOAD_ERROR, message=msg, field="file")]
            )
        except Exception as e:
            return UploadBlogMedia(
                errors=[BlogError(code=BlogErrorCode.MEDIA_UPLOAD_ERROR, message=str(e), field="file")]
            )


class BlogCategoryCreate(graphene.Mutation):
    category = graphene.Field(BlogCategoryType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        name = graphene.String(required=True)
        slug = graphene.String()
        description = graphene.String()
        parent_id = graphene.ID()
        seo_title = graphene.String()
        seo_description = graphene.String()
        badge_color = graphene.String()
        is_active = graphene.Boolean(default_value=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, name, slug=None, description="", parent_id=None, seo_title="", seo_description="", badge_color="bg-emerald-50 text-emerald-700", is_active=True):
        name = name.strip()
        slug = (slug or slugify(name)).strip()
        if BlogCategory.objects.filter(slug=slug).exists():
            return BlogCategoryCreate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Category slug exists.", field="slug")])

        parent = None
        if parent_id:
            parent_pk = _parse_id(parent_id, "BlogCategory")
            parent = BlogCategory.objects.filter(pk=parent_pk).first()

        category = BlogCategory.objects.create(
            name=name,
            slug=slug,
            description=description or "",
            parent=parent,
            seo_title=seo_title or "",
            seo_description=seo_description or "",
            badge_color=badge_color or "bg-emerald-50 text-emerald-700",
            is_active=is_active,
        )
        _log_audit(info, "CREATE", "BlogCategory", category.id)
        return BlogCategoryCreate(category=category, errors=[])


class BlogCategoryUpdate(graphene.Mutation):
    category = graphene.Field(BlogCategoryType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()
        description = graphene.String()
        parent_id = graphene.ID()
        seo_title = graphene.String()
        seo_description = graphene.String()
        badge_color = graphene.String()
        is_active = graphene.Boolean()

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, **kwargs):
        pk = _parse_id(id, "BlogCategory")
        cat = BlogCategory.objects.filter(pk=pk).first()
        if not cat:
            return BlogCategoryUpdate(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Category not found.", field="id")])

        if "name" in kwargs and kwargs["name"] is not None:
            cat.name = kwargs["name"].strip()
        if "slug" in kwargs and kwargs["slug"] is not None:
            new_slug = kwargs["slug"].strip()
            if new_slug != cat.slug and BlogCategory.objects.filter(slug=new_slug).exclude(pk=cat.pk).exists():
                return BlogCategoryUpdate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Slug already exists.", field="slug")])
            cat.slug = new_slug
        if "description" in kwargs and kwargs["description"] is not None:
            cat.description = kwargs["description"]
        if "parent_id" in kwargs:
            pid = kwargs["parent_id"]
            if pid:
                parent_pk = _parse_id(pid, "BlogCategory")
                if parent_pk == cat.pk:
                    return BlogCategoryUpdate(errors=[BlogError(code=BlogErrorCode.CIRCULAR_CATEGORY_PARENT, message="Category cannot be its own parent.", field="parent_id")])
                cat.parent = BlogCategory.objects.filter(pk=parent_pk).first()
            else:
                cat.parent = None
        if "seo_title" in kwargs and kwargs["seo_title"] is not None:
            cat.seo_title = kwargs["seo_title"]
        if "seo_description" in kwargs and kwargs["seo_description"] is not None:
            cat.seo_description = kwargs["seo_description"]
        if "badge_color" in kwargs and kwargs["badge_color"] is not None:
            cat.badge_color = kwargs["badge_color"]
        if "is_active" in kwargs and kwargs["is_active"] is not None:
            cat.is_active = kwargs["is_active"]

        try:
            cat.save()
        except Exception as e:
            return BlogCategoryUpdate(errors=[BlogError(code=BlogErrorCode.CIRCULAR_CATEGORY_PARENT, message=str(e), field="parent_id")])

        _log_audit(info, "UPDATE", "BlogCategory", cat.id)
        return BlogCategoryUpdate(category=cat, errors=[])


class BlogCategoryDelete(graphene.Mutation):
    success = graphene.Boolean(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogCategory")
        cat = BlogCategory.objects.filter(pk=pk).first()
        if not cat:
            return BlogCategoryDelete(success=False, errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Category not found.", field="id")])
        cat.delete()
        _log_audit(info, "DELETE", "BlogCategory", pk)
        return BlogCategoryDelete(success=True, errors=[])


class BlogTagCreate(graphene.Mutation):
    tag = graphene.Field(BlogTagType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        name = graphene.String(required=True)
        slug = graphene.String()
        description = graphene.String()

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, name, slug=None, description=""):
        name = name.strip()
        slug = (slug or slugify(name)).strip()
        if BlogTag.objects.filter(slug=slug).exists():
            return BlogTagCreate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Tag slug exists.", field="slug")])

        tag = BlogTag.objects.create(name=name, slug=slug, description=description or "")
        _log_audit(info, "CREATE", "BlogTag", tag.id)
        return BlogTagCreate(tag=tag, errors=[])


class BlogTagUpdate(graphene.Mutation):
    tag = graphene.Field(BlogTagType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String()
        slug = graphene.String()
        description = graphene.String()

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, **kwargs):
        pk = _parse_id(id, "BlogTag")
        tag = BlogTag.objects.filter(pk=pk).first()
        if not tag:
            return BlogTagUpdate(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Tag not found.", field="id")])

        if "name" in kwargs and kwargs["name"] is not None:
            tag.name = kwargs["name"].strip()
        if "slug" in kwargs and kwargs["slug"] is not None:
            new_slug = kwargs["slug"].strip()
            if new_slug != tag.slug and BlogTag.objects.filter(slug=new_slug).exclude(pk=tag.pk).exists():
                return BlogTagUpdate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Slug exists.", field="slug")])
            tag.slug = new_slug
        if "description" in kwargs and kwargs["description"] is not None:
            tag.description = kwargs["description"]

        tag.save()
        _log_audit(info, "UPDATE", "BlogTag", tag.id)
        return BlogTagUpdate(tag=tag, errors=[])


class BlogTagDelete(graphene.Mutation):
    success = graphene.Boolean(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogTag")
        tag = BlogTag.objects.filter(pk=pk).first()
        if not tag:
            return BlogTagDelete(success=False, errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Tag not found.", field="id")])
        tag.delete()
        _log_audit(info, "DELETE", "BlogTag", pk)
        return BlogTagDelete(success=True, errors=[])


class BlogAuthorCreate(graphene.Mutation):
    author = graphene.Field(BlogAuthorType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        display_name = graphene.String(required=True)
        slug = graphene.String()
        bio = graphene.String()
        avatar = graphene.String()
        designation = graphene.String()
        social_links = JSON()

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, display_name, slug=None, bio="", avatar=None, designation="", social_links=None):
        name = display_name.strip()
        slug = (slug or slugify(name)).strip()
        if BlogAuthor.objects.filter(slug=slug).exists():
            return BlogAuthorCreate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Author slug exists.", field="slug")])

        parsed_social = {}
        if social_links:
            try:
                parsed_social = json.loads(social_links) if isinstance(social_links, str) else social_links
            except Exception:
                pass

        author = BlogAuthor.objects.create(
            display_name=name,
            slug=slug,
            bio=bio or "",
            avatar=avatar,
            designation=designation or "",
            social_links=parsed_social,
        )
        _log_audit(info, "CREATE", "BlogAuthor", author.id)
        return BlogAuthorCreate(author=author, errors=[])


class BlogAuthorUpdate(graphene.Mutation):
    author = graphene.Field(BlogAuthorType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        display_name = graphene.String()
        slug = graphene.String()
        bio = graphene.String()
        avatar = graphene.String()
        designation = graphene.String()
        social_links = JSON()

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, **kwargs):
        pk = _parse_id(id, "BlogAuthor")
        author = BlogAuthor.objects.filter(pk=pk).first()
        if not author:
            return BlogAuthorUpdate(errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Author not found.", field="id")])

        if "display_name" in kwargs and kwargs["display_name"] is not None:
            author.display_name = kwargs["display_name"].strip()
        if "slug" in kwargs and kwargs["slug"] is not None:
            new_slug = kwargs["slug"].strip()
            if new_slug != author.slug and BlogAuthor.objects.filter(slug=new_slug).exclude(pk=author.pk).exists():
                return BlogAuthorUpdate(errors=[BlogError(code=BlogErrorCode.SLUG_ALREADY_EXISTS, message="Slug exists.", field="slug")])
            author.slug = new_slug
        if "bio" in kwargs and kwargs["bio"] is not None:
            author.bio = kwargs["bio"]
        if "avatar" in kwargs and kwargs["avatar"] is not None:
            author.avatar = kwargs["avatar"]
        if "designation" in kwargs and kwargs["designation"] is not None:
            author.designation = kwargs["designation"]
        if "social_links" in kwargs and kwargs["social_links"] is not None:
            try:
                author.social_links = json.loads(kwargs["social_links"]) if isinstance(kwargs["social_links"], str) else kwargs["social_links"]
            except Exception:
                pass

        author.save()
        _log_audit(info, "UPDATE", "BlogAuthor", author.id)
        return BlogAuthorUpdate(author=author, errors=[])


class BlogAuthorDelete(graphene.Mutation):
    success = graphene.Boolean(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id):
        pk = _parse_id(id, "BlogAuthor")
        author = BlogAuthor.objects.filter(pk=pk).first()
        if not author:
            return BlogAuthorDelete(success=False, errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Author not found.", field="id")])
        author.delete()
        _log_audit(info, "DELETE", "BlogAuthor", pk)
        return BlogAuthorDelete(success=True, errors=[])


def _is_staff(info):
    context = getattr(info, "context", None)
    if not context:
        return False
    user = getattr(context, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_staff or user.has_perm("blog.manage_blog") or user.has_perm("page.manage_pages"))


class BlogCommentCreateInput(graphene.InputObjectType):
    post_id = graphene.ID(description="ID of the blog post.")
    post_slug = graphene.String(description="Slug of the blog post.")
    author_name = graphene.String(required=True, description="Name of the commenter.")
    author_email = graphene.String(description="Email of the commenter.")
    content = graphene.String(required=True, description="Comment text.")
    parent_id = graphene.ID(description="Optional parent comment ID for replies.")
    client_token = graphene.String(description="Client token for guest identification.")


class BlogCommentCreate(graphene.Mutation):
    comment = graphene.Field(BlogCommentType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        input = BlogCommentCreateInput(required=True)

    def mutate(self, info, input):
        data = _get_input_data(input)
        post_id = data.get("post_id")
        post_slug = data.get("post_slug")

        post = None
        if post_id:
            pk = _parse_id(post_id, "BlogPost")
            post = BlogPost.objects.filter(pk=pk).first()
        elif post_slug:
            post = BlogPost.objects.filter(slug=post_slug).first()

        if not post:
            return BlogCommentCreate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Blog post not found.", field="post_id")],
            )

        if not post.allow_comments:
            return BlogCommentCreate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.COMMENTS_DISABLED, message="Comments are disabled for this article.", field="post")],
            )

        content = (data.get("content") or "").strip()
        if len(content) < 3:
            return BlogCommentCreate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.REQUIRED_FIELD_MISSING, message="Comment content must be at least 3 characters long.", field="content")],
            )

        author_name = (data.get("author_name") or "").strip()
        if len(author_name) < 2:
            return BlogCommentCreate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.REQUIRED_FIELD_MISSING, message="Author name must be at least 2 characters long.", field="author_name")],
            )

        author_email = (data.get("author_email") or "").strip()
        client_token = (data.get("client_token") or "").strip()

        parent = None
        parent_id = data.get("parent_id")
        if parent_id:
            parent_pk = _parse_id(parent_id, "BlogComment")
            parent = BlogComment.objects.filter(pk=parent_pk, post=post).first()

        context = getattr(info, "context", None)
        user = getattr(context, "user", None) if context else None
        authenticated_user = user if (user and getattr(user, "is_authenticated", False)) else None

        status = BlogCommentStatus.APPROVED if _is_staff(info) else BlogCommentStatus.PENDING

        comment = BlogComment.objects.create(
            post=post,
            user=authenticated_user,
            author_name=author_name,
            author_email=author_email,
            content=content,
            status=status,
            parent=parent,
            client_token=client_token,
        )

        _log_audit(info, "CREATE", "BlogComment", comment.id, {"post": post.title, "author": author_name})
        return BlogCommentCreate(comment=comment, errors=[])


class BlogCommentStatusUpdate(graphene.Mutation):
    comment = graphene.Field(BlogCommentType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True, description="Comment ID.")
        status = BlogCommentStatusEnum(required=True, description="New status (PENDING, APPROVED, REJECTED).")

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, id, status):
        pk = _parse_id(id, "BlogComment")
        comment = BlogComment.objects.select_related("post").filter(pk=pk).first()
        if not comment:
            return BlogCommentStatusUpdate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Comment not found.", field="id")],
            )

        comment.status = status
        comment.save(update_fields=["status", "updated_at"])
        _log_audit(info, "STATUS_CHANGE", "BlogComment", comment.id, {"status": status})
        return BlogCommentStatusUpdate(comment=comment, errors=[])


class BlogCommentBulkUpdateStatus(graphene.Mutation):
    count = graphene.Int(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        ids = graphene.List(graphene.ID, required=True, description="List of comment IDs.")
        status = BlogCommentStatusEnum(required=True, description="New status.")

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, ids, status):
        pks = [_parse_id(i, "BlogComment") for i in ids if i]
        updated_count = BlogComment.objects.filter(pk__in=pks).update(status=status)
        _log_audit(info, "BULK_STATUS_CHANGE", "BlogComment", f"{len(pks)} items", {"status": status})
        return BlogCommentBulkUpdateStatus(count=updated_count, errors=[])


class BlogCommentUpdateInput(graphene.InputObjectType):
    content = graphene.String(description="Updated comment content.")
    status = BlogCommentStatusEnum(description="Updated moderation status (staff only).")
    is_pinned = graphene.Boolean(description="Pinned status (staff only).")


class BlogCommentUpdate(graphene.Mutation):
    comment = graphene.Field(BlogCommentType)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        input = BlogCommentUpdateInput(required=True)
        client_token = graphene.String(description="Client token for guest author verification.")

    def mutate(self, info, id, input, client_token=None):
        pk = _parse_id(id, "BlogComment")
        comment = BlogComment.objects.select_related("post").filter(pk=pk).first()
        if not comment:
            return BlogCommentUpdate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Comment not found.", field="id")],
            )

        is_staff_user = _is_staff(info)
        context = getattr(info, "context", None)
        user = getattr(context, "user", None) if context else None
        is_user_author = bool(user and getattr(user, "is_authenticated", False) and comment.user_id == user.id)
        is_token_author = bool(client_token and comment.client_token and comment.client_token == client_token)

        if not (is_staff_user or is_user_author or is_token_author):
            return BlogCommentUpdate(
                comment=None,
                errors=[BlogError(code=BlogErrorCode.PERMISSION_DENIED, message="You do not have permission to edit this comment.", field="id")],
            )

        data = _get_input_data(input)
        if "content" in data and data["content"] is not None:
            c = data["content"].strip()
            if len(c) < 3:
                return BlogCommentUpdate(
                    comment=None,
                    errors=[BlogError(code=BlogErrorCode.REQUIRED_FIELD_MISSING, message="Comment content must be at least 3 characters long.", field="content")],
                )
            comment.content = c

        if is_staff_user:
            if "status" in data and data["status"] is not None:
                comment.status = data["status"]
            if "is_pinned" in data and data["is_pinned"] is not None:
                comment.is_pinned = data["is_pinned"]

        comment.save()
        _log_audit(info, "UPDATE", "BlogComment", comment.id)
        return BlogCommentUpdate(comment=comment, errors=[])


class BlogCommentDelete(graphene.Mutation):
    success = graphene.Boolean(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        client_token = graphene.String(description="Client token for guest verification.")

    def mutate(self, info, id, client_token=None):
        pk = _parse_id(id, "BlogComment")
        comment = BlogComment.objects.filter(pk=pk).first()
        if not comment:
            return BlogCommentDelete(success=False, errors=[BlogError(code=BlogErrorCode.NOT_FOUND, message="Comment not found.", field="id")])

        is_staff_user = _is_staff(info)
        context = getattr(info, "context", None)
        user = getattr(context, "user", None) if context else None
        is_user_author = bool(user and getattr(user, "is_authenticated", False) and comment.user_id == user.id)
        is_token_author = bool(client_token and comment.client_token and comment.client_token == client_token)

        if not (is_staff_user or is_user_author or is_token_author):
            return BlogCommentDelete(
                success=False,
                errors=[BlogError(code=BlogErrorCode.PERMISSION_DENIED, message="Permission denied to delete this comment.", field="id")],
            )

        comment.delete()
        _log_audit(info, "DELETE", "BlogComment", pk)
        return BlogCommentDelete(success=True, errors=[])


class BlogCommentBulkDelete(graphene.Mutation):
    count = graphene.Int(required=True)
    errors = graphene.List(BlogError, required=True)

    class Arguments:
        ids = graphene.List(graphene.ID, required=True)

    @one_of_permissions_required(BLOG_PERMISSIONS)
    def mutate(self, info, ids):
        pks = [_parse_id(i, "BlogComment") for i in ids if i]
        deleted_count, _ = BlogComment.objects.filter(pk__in=pks).delete()
        _log_audit(info, "BULK_DELETE", "BlogComment", f"{len(pks)} items")
        return BlogCommentBulkDelete(count=deleted_count, errors=[])


class BlogMutations(graphene.ObjectType):
    """All blog mutations exposed through GraphQL."""

    blog_post_create = BlogPostCreate.Field()
    blog_post_update = BlogPostUpdate.Field()
    blog_post_delete = BlogPostDelete.Field()
    blog_post_publish = BlogPostPublish.Field()
    blog_post_schedule = BlogPostSchedule.Field()
    blog_post_unpublish = BlogPostUnpublish.Field()
    blog_post_archive = BlogPostArchive.Field()
    blog_post_duplicate = BlogPostDuplicate.Field()
    blog_post_restore_revision = BlogPostRestoreRevision.Field()
    upload_blog_media = UploadBlogMedia.Field()

    blog_category_create = BlogCategoryCreate.Field()
    blog_category_update = BlogCategoryUpdate.Field()
    blog_category_delete = BlogCategoryDelete.Field()

    blog_tag_create = BlogTagCreate.Field()
    blog_tag_update = BlogTagUpdate.Field()
    blog_tag_delete = BlogTagDelete.Field()

    blog_author_create = BlogAuthorCreate.Field()
    blog_author_update = BlogAuthorUpdate.Field()
    blog_author_delete = BlogAuthorDelete.Field()

    blog_comment_create = BlogCommentCreate.Field()
    blog_comment_status_update = BlogCommentStatusUpdate.Field()
    blog_comment_bulk_update_status = BlogCommentBulkUpdateStatus.Field()
    blog_comment_update = BlogCommentUpdate.Field()
    blog_comment_delete = BlogCommentDelete.Field()
    blog_comment_bulk_delete = BlogCommentBulkDelete.Field()

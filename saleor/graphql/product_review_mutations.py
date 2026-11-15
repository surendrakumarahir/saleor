"""GraphQL mutations for Product Review Management."""

import graphene
from django.utils import timezone

from saleor.graphql.core.utils import from_global_id_or_error
from saleor.graphql.product_review_errors import (
    ProductReviewError,
    ProductReviewErrorCode,
)
from saleor.graphql.product_review_types import (
    ProductReviewStatusEnum,
    ProductReviewType,
)
from saleor.product.models import Product, ProductReview, ProductReviewStatus
from saleor.product.utils.reviews import (
    check_is_verified_buyer,
    recalculate_product_rating,
)


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


def _is_staff(info):
    context = getattr(info, "context", None)
    if not context:
        return False
    user = getattr(context, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_staff or user.has_perm("product.manage_products"))


class ProductReviewCreateInput(graphene.InputObjectType):
    product_id = graphene.ID(description="Global ID or int of the product.")
    product_slug = graphene.String(description="Slug of the product.")
    user_name = graphene.String(required=True, description="Name of the reviewer.")
    user_email = graphene.String(description="Email of the reviewer.")
    rating = graphene.Int(required=True, description="Rating from 1 to 5.")
    title = graphene.String(description="Review title / headline.")
    content = graphene.String(required=True, description="Review text content.")
    images = graphene.List(graphene.String, description="Optional image URLs attached to review.")
    client_token = graphene.String(description="Client token for guest identification.")


class ProductReviewCreate(graphene.Mutation):
    review = graphene.Field(ProductReviewType)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        input = ProductReviewCreateInput(required=True)

    def mutate(self, info, input):
        product_id = getattr(input, "product_id", None)
        product_slug = getattr(input, "product_slug", None)

        product = None
        if product_id:
            pk = _parse_id(product_id, "Product")
            product = Product.objects.filter(pk=pk).first()
        elif product_slug:
            product = Product.objects.filter(slug=product_slug).first()

        if not product:
            return ProductReviewCreate(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.NOT_FOUND,
                        message="Product not found.",
                        field="product_id",
                    )
                ],
            )

        rating = getattr(input, "rating", None)
        if rating is None or rating < 1 or rating > 5:
            return ProductReviewCreate(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.INVALID_RATING,
                        message="Rating must be an integer between 1 and 5.",
                        field="rating",
                    )
                ],
            )

        content = (getattr(input, "content", "") or "").strip()
        if len(content) < 3:
            return ProductReviewCreate(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.REQUIRED_FIELD_MISSING,
                        message="Review content must be at least 3 characters long.",
                        field="content",
                    )
                ],
            )

        user_name = (getattr(input, "user_name", "") or "").strip()
        if not user_name:
            return ProductReviewCreate(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.REQUIRED_FIELD_MISSING,
                        message="Reviewer name is required.",
                        field="user_name",
                    )
                ],
            )

        user_email = (getattr(input, "user_email", "") or "").strip()
        context = getattr(info, "context", None)
        user = getattr(context, "user", None) if context else None
        auth_user = user if (user and getattr(user, "is_authenticated", False)) else None

        # Check verified buyer
        is_verified = check_is_verified_buyer(product.id, user=auth_user, email=user_email)

        # Create review
        review = ProductReview(
            product=product,
            user=auth_user,
            user_name=user_name,
            user_email=user_email or (auth_user.email if auth_user else ""),
            rating=rating,
            title=(getattr(input, "title", "") or "").strip(),
            content=content,
            status=ProductReviewStatus.PENDING,
            is_verified_buyer=is_verified,
            images=getattr(input, "images", []) or [],
            client_token=getattr(input, "client_token", "") or "",
        )
        review.save()

        return ProductReviewCreate(review=review, errors=[])


class ProductReviewStatusUpdate(graphene.Mutation):
    review = graphene.Field(ProductReviewType)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        status = ProductReviewStatusEnum(required=True)

    def mutate(self, info, id, status):
        if not _is_staff(info):
            return ProductReviewStatusUpdate(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.PERMISSION_DENIED,
                        message="Staff permissions required to moderate reviews.",
                        field="id",
                    )
                ],
            )

        pk = _parse_id(id, "ProductReview")
        review = ProductReview.objects.select_related("product").filter(pk=pk).first()
        if not review:
            return ProductReviewStatusUpdate(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.NOT_FOUND,
                        message="Review not found.",
                        field="id",
                    )
                ],
            )

        review.status = status
        review.save(update_fields=["status", "updated_at"])

        # Recalculate average rating & review count for the product
        recalculate_product_rating(review.product)

        return ProductReviewStatusUpdate(review=review, errors=[])


class ProductReviewBulkUpdateStatus(graphene.Mutation):
    count = graphene.Int(required=True)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        ids = graphene.List(graphene.ID, required=True)
        status = ProductReviewStatusEnum(required=True)

    def mutate(self, info, ids, status):
        if not _is_staff(info):
            return ProductReviewBulkUpdateStatus(
                count=0,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.PERMISSION_DENIED,
                        message="Staff permissions required for bulk review updates.",
                        field="ids",
                    )
                ],
            )

        pks = [_parse_id(i, "ProductReview") for i in ids if i]
        reviews = list(ProductReview.objects.filter(pk__in=pks).select_related("product"))
        updated_count = ProductReview.objects.filter(pk__in=pks).update(
            status=status, updated_at=timezone.now()
        )

        # Recalculate rating aggregates for each affected product
        affected_product_ids = {r.product_id for r in reviews}
        for pid in affected_product_ids:
            recalculate_product_rating(pid)

        return ProductReviewBulkUpdateStatus(count=updated_count, errors=[])


class ProductReviewDelete(graphene.Mutation):
    success = graphene.Boolean(required=True)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        client_token = graphene.String(description="Client token for guest verification.")

    def mutate(self, info, id, client_token=None):
        pk = _parse_id(id, "ProductReview")
        review = ProductReview.objects.select_related("product").filter(pk=pk).first()
        if not review:
            return ProductReviewDelete(
                success=False,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.NOT_FOUND,
                        message="Review not found.",
                        field="id",
                    )
                ],
            )

        is_staff_user = _is_staff(info)
        context = getattr(info, "context", None)
        user = getattr(context, "user", None) if context else None
        is_author = bool(user and getattr(user, "is_authenticated", False) and review.user_id == user.id)
        is_token_author = bool(client_token and review.client_token and review.client_token == client_token)

        if not (is_staff_user or is_author or is_token_author):
            return ProductReviewDelete(
                success=False,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.PERMISSION_DENIED,
                        message="Permission denied to delete this review.",
                        field="id",
                    )
                ],
            )

        product = review.product
        review.delete()

        # Recalculate product rating after deletion
        recalculate_product_rating(product)

        return ProductReviewDelete(success=True, errors=[])


class ProductReviewBulkDelete(graphene.Mutation):
    count = graphene.Int(required=True)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        ids = graphene.List(graphene.ID, required=True)

    def mutate(self, info, ids):
        if not _is_staff(info):
            return ProductReviewBulkDelete(
                count=0,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.PERMISSION_DENIED,
                        message="Staff permissions required to bulk delete reviews.",
                        field="ids",
                    )
                ],
            )

        pks = [_parse_id(i, "ProductReview") for i in ids if i]
        reviews = list(ProductReview.objects.filter(pk__in=pks).select_related("product"))
        affected_product_ids = {r.product_id for r in reviews}

        deleted_count, _ = ProductReview.objects.filter(pk__in=pks).delete()

        # Recalculate ratings
        for pid in affected_product_ids:
            recalculate_product_rating(pid)

        return ProductReviewBulkDelete(count=deleted_count, errors=[])


class ProductReviewAdminReply(graphene.Mutation):
    review = graphene.Field(ProductReviewType)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        id = graphene.ID(required=True)
        reply = graphene.String(required=True)

    def mutate(self, info, id, reply):
        if not _is_staff(info):
            return ProductReviewAdminReply(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.PERMISSION_DENIED,
                        message="Staff permissions required to add official reply.",
                        field="id",
                    )
                ],
            )

        pk = _parse_id(id, "ProductReview")
        review = ProductReview.objects.filter(pk=pk).first()
        if not review:
            return ProductReviewAdminReply(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.NOT_FOUND,
                        message="Review not found.",
                        field="id",
                    )
                ],
            )

        clean_reply = (reply or "").strip()
        review.admin_reply = clean_reply
        review.admin_replied_at = timezone.now() if clean_reply else None
        review.save(update_fields=["admin_reply", "admin_replied_at", "updated_at"])

        return ProductReviewAdminReply(review=review, errors=[])


class ProductReviewHelpful(graphene.Mutation):
    review = graphene.Field(ProductReviewType)
    errors = graphene.List(ProductReviewError, required=True)

    class Arguments:
        id = graphene.ID(required=True)

    def mutate(self, info, id):
        pk = _parse_id(id, "ProductReview")
        review = ProductReview.objects.filter(pk=pk).first()
        if not review:
            return ProductReviewHelpful(
                review=None,
                errors=[
                    ProductReviewError(
                        code=ProductReviewErrorCode.NOT_FOUND,
                        message="Review not found.",
                        field="id",
                    )
                ],
            )

        review.helpful_count += 1
        review.save(update_fields=["helpful_count", "updated_at"])

        return ProductReviewHelpful(review=review, errors=[])


class ProductReviewMutations(graphene.ObjectType):
    """All product review mutations exposed through GraphQL."""

    product_review_create = ProductReviewCreate.Field()
    product_review_status_update = ProductReviewStatusUpdate.Field()
    product_review_bulk_update_status = ProductReviewBulkUpdateStatus.Field()
    product_review_delete = ProductReviewDelete.Field()
    product_review_bulk_delete = ProductReviewBulkDelete.Field()
    product_review_admin_reply = ProductReviewAdminReply.Field()
    product_review_helpful = ProductReviewHelpful.Field()

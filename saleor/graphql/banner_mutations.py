"""GraphQL mutations for banner management."""

import posixpath

import graphene
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from graphql import GraphQLError

from saleor.banner.models import Banner, ImageCollection
from saleor.channel.models import Channel
from saleor.core.error_codes import UploadErrorCode
from saleor.graphql.decorators import one_of_permissions_required
from saleor.graphql.core.types import File, Upload
from saleor.graphql.core.validators.file import validate_upload_file
from saleor.graphql.banner_types import BannerType, ImageCollectionType
from saleor.graphql.banner_errors import BannerError, BannerErrorCode
from saleor.graphql.core.scalars import DateTime
from saleor.graphql.core.utils import add_hash_to_file_name, from_global_id_or_error


BANNER_UPLOAD_ROOT_DIR = "banners"


def _normalize_banner_folder(folder: str | None) -> str:
    if not folder:
        return BANNER_UPLOAD_ROOT_DIR

    clean_folder = folder.strip().strip("/")
    if clean_folder.startswith("media/"):
        clean_folder = clean_folder[6:]
    if not clean_folder:
        return BANNER_UPLOAD_ROOT_DIR

    normalized = posixpath.normpath(clean_folder)
    if normalized in {".", ""} or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("Invalid folder path.")

    if normalized == BANNER_UPLOAD_ROOT_DIR or normalized.startswith(
        f"{BANNER_UPLOAD_ROOT_DIR}/"
    ):
        return normalized

    return posixpath.join(BANNER_UPLOAD_ROOT_DIR, normalized)


def _resolve_upload_from_request(info, file):
    # GraphQL multipart uploads may arrive as FILES[file_key] or UploadedFile instance.
    if isinstance(file, UploadedFile):
        return file
    return info.context.FILES[file]


class CreateImageCollectionMutation(graphene.Mutation):
    """Create a new image collection."""

    image_collection = graphene.Field(ImageCollectionType)
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        name = graphene.String(required=True, description="Collection name.")
        description = graphene.String(description="Collection description.")
        channel_id = graphene.ID(required=True, description="Channel ID.")
        is_active = graphene.Boolean(
            default_value=True, description="Is collection active."
        )

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(self, info, name, channel_id, description=None, is_active=True):
        errors = []

        if not name:
            errors.append(
                BannerError(
                    code=BannerErrorCode.REQUIRED_FIELD_MISSING,
                    message="Name is required.",
                    field="name",
                )
            )

        try:
            _, channel_id_int = from_global_id_or_error(
                channel_id, "Channel", raise_error=True
            )
            channel = Channel.objects.get(pk=channel_id_int)
        except (GraphQLError, Channel.DoesNotExist):
            errors.append(
                BannerError(
                    code=BannerErrorCode.COLLECTION_NOT_FOUND,
                    message="Channel not found.",
                    field="channel_id",
                )
            )
            return CreateImageCollectionMutation(errors=errors)

        if errors:
            return CreateImageCollectionMutation(errors=errors)

        collection = ImageCollection.objects.create(
            name=name,
            description=description or "",
            channel=channel,
            is_active=is_active,
        )

        return CreateImageCollectionMutation(
            image_collection=collection, errors=[]
        )


class UpdateImageCollectionMutation(graphene.Mutation):
    """Update an existing image collection."""

    image_collection = graphene.Field(ImageCollectionType)
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        id = graphene.ID(required=True, description="Collection ID.")
        name = graphene.String(description="Collection name.")
        description = graphene.String(description="Collection description.")
        is_active = graphene.Boolean(description="Is collection active.")

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(self, info, id, name=None, description=None, is_active=None):
        errors = []

        try:
            collection = ImageCollection.objects.get(pk=id)
        except ImageCollection.DoesNotExist:
            errors.append(
                BannerError(
                    code=BannerErrorCode.COLLECTION_NOT_FOUND,
                    message="Collection not found.",
                    field="id",
                )
            )
            return UpdateImageCollectionMutation(errors=errors)

        if name is not None:
            collection.name = name
        if description is not None:
            collection.description = description
        if is_active is not None:
            collection.is_active = is_active

        collection.save()
        return UpdateImageCollectionMutation(
            image_collection=collection, errors=[]
        )


class DeleteImageCollectionMutation(graphene.Mutation):
    """Delete an image collection."""

    success = graphene.Boolean()
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        id = graphene.ID(required=True, description="Collection ID.")

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(self, info, id):
        errors = []

        try:
            collection = ImageCollection.objects.get(pk=id)
            collection.delete()
        except ImageCollection.DoesNotExist:
            errors.append(
                BannerError(
                    code=BannerErrorCode.COLLECTION_NOT_FOUND,
                    message="Collection not found.",
                    field="id",
                )
            )
            return DeleteImageCollectionMutation(success=False, errors=errors)

        return DeleteImageCollectionMutation(success=True, errors=[])


class CreateBannerMutation(graphene.Mutation):
    """Create a new banner."""

    banner = graphene.Field(BannerType)
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        title = graphene.String(required=True, description="Banner title.")
        description = graphene.String(description="Banner description.")
        image = graphene.String(
            description=(
                "Deprecated. Banner image URL/path. Prefer `imageKey` from "
                "`uploadBannerImage` mutation."
            )
        )
        image_key = graphene.String(
            description="Image storage key returned by `uploadBannerImage`."
        )
        alt_text = graphene.String(description="Image alt text.")
        link_url = graphene.String(description="Link URL.")
        link_text = graphene.String(description="Link text.")
        collection_id = graphene.ID(required=True, description="Collection ID.")
        custom_field_1 = graphene.String(description="Custom field 1.")
        custom_field_2 = graphene.String(description="Custom field 2.")
        custom_field_3 = graphene.String(description="Custom field 3.")
        key_values = graphene.String(
            description="Custom key-value pairs."
        )
        position = graphene.Int(description="Banner position.")
        is_active = graphene.Boolean(
            default_value=True, description="Is banner active."
        )
        start_date = DateTime(description="Start date/time.")
        end_date = DateTime(description="End date/time.")

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(
        self,
        info,
        title,
        collection_id,
        image=None,
        image_key=None,
        description=None,
        alt_text=None,
        link_url=None,
        link_text=None,
        custom_field_1=None,
        custom_field_2=None,
        custom_field_3=None,
        key_values=None,
        position=0,
        is_active=True,
        start_date=None,
        end_date=None,
    ):
        errors = []

        if not title:
            errors.append(
                BannerError(
                    code=BannerErrorCode.REQUIRED_FIELD_MISSING,
                    message="Title is required.",
                    field="title",
                )
            )

        if not image_key and not image:
            errors.append(
                BannerError(
                    code=BannerErrorCode.REQUIRED_FIELD_MISSING,
                    message="Provide `imageKey` or deprecated `image` value.",
                    field="image_key",
                )
            )

        if start_date and end_date and start_date >= end_date:
            errors.append(
                BannerError(
                    code=BannerErrorCode.INVALID_DATE_RANGE,
                    message="Start date must be before end date.",
                    field="start_date",
                )
            )

        try:
            collection = ImageCollection.objects.get(pk=collection_id)
        except ImageCollection.DoesNotExist:
            errors.append(
                BannerError(
                    code=BannerErrorCode.COLLECTION_NOT_FOUND,
                    message="Collection not found.",
                    field="collection_id",
                )
            )

        if errors:
            return CreateBannerMutation(errors=errors)

        banner = Banner.objects.create(
            title=title,
            description=description or "",
            alt_text=alt_text or "",
            link_url=link_url,
            link_text=link_text or "",
            custom_field_1=custom_field_1 or "",
            custom_field_2=custom_field_2 or "",
            custom_field_3=custom_field_3 or "",
            key_values=key_values or {},
            image_collection=collection,
            position=position,
            is_active=is_active,
            start_date=start_date,
            end_date=end_date,
        )

        if image_key:
            banner.image = image_key
        elif image and isinstance(image, str):
            banner.image = image

        banner.save()
        return CreateBannerMutation(banner=banner, errors=[])


class UpdateBannerMutation(graphene.Mutation):
    """Update an existing banner."""

    banner = graphene.Field(BannerType)
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        id = graphene.ID(required=True, description="Banner ID.")
        title = graphene.String(description="Banner title.")
        description = graphene.String(description="Banner description.")
        image = graphene.String(
            description=(
                "Deprecated. Banner image URL/path. Prefer `imageKey` from "
                "`uploadBannerImage` mutation."
            )
        )
        image_key = graphene.String(
            description="Image storage key returned by `uploadBannerImage`."
        )
        alt_text = graphene.String(description="Image alt text.")
        link_url = graphene.String(description="Link URL.")
        link_text = graphene.String(description="Link text.")
        custom_field_1 = graphene.String(description="Custom field 1.")
        custom_field_2 = graphene.String(description="Custom field 2.")
        custom_field_3 = graphene.String(description="Custom field 3.")
        key_values = graphene.String(
            description="Custom key-value pairs."
        )
        position = graphene.Int(description="Banner position.")
        is_active = graphene.Boolean(description="Is banner active.")
        start_date = DateTime(description="Start date/time.")
        end_date = DateTime(description="End date/time.")

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(
        self,
        info,
        id,
        title=None,
        description=None,
        image=None,
        image_key=None,
        alt_text=None,
        link_url=None,
        link_text=None,
        custom_field_1=None,
        custom_field_2=None,
        custom_field_3=None,
        key_values=None,
        position=None,
        is_active=None,
        start_date=None,
        end_date=None,
    ):
        errors = []

        if start_date and end_date and start_date >= end_date:
            errors.append(
                BannerError(
                    code=BannerErrorCode.INVALID_DATE_RANGE,
                    message="Start date must be before end date.",
                    field="start_date",
                )
            )

        try:
            banner = Banner.objects.get(pk=id)
        except Banner.DoesNotExist:
            errors.append(
                BannerError(
                    code=BannerErrorCode.BANNER_NOT_FOUND,
                    message="Banner not found.",
                    field="id",
                )
            )
            return UpdateBannerMutation(errors=errors)

        if errors:
            return UpdateBannerMutation(errors=errors)

        if title is not None:
            banner.title = title
        if description is not None:
            banner.description = description
        if image_key is not None:
            banner.image = image_key
        elif image is not None:
            banner.image = image
        if alt_text is not None:
            banner.alt_text = alt_text
        if link_url is not None:
            banner.link_url = link_url
        if link_text is not None:
            banner.link_text = link_text
        if custom_field_1 is not None:
            banner.custom_field_1 = custom_field_1
        if custom_field_2 is not None:
            banner.custom_field_2 = custom_field_2
        if custom_field_3 is not None:
            banner.custom_field_3 = custom_field_3
        if key_values is not None:
            banner.key_values = key_values
        if position is not None:
            banner.position = position
        if is_active is not None:
            banner.is_active = is_active
        if start_date is not None:
            banner.start_date = start_date
        if end_date is not None:
            banner.end_date = end_date

        banner.save()
        return UpdateBannerMutation(banner=banner, errors=[])


class DeleteBannerMutation(graphene.Mutation):
    """Delete a banner."""

    success = graphene.Boolean()
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        id = graphene.ID(required=True, description="Banner ID.")

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(self, info, id):
        errors = []

        try:
            banner = Banner.objects.get(pk=id)
            banner.delete()
        except Banner.DoesNotExist:
            errors.append(
                BannerError(
                    code=BannerErrorCode.BANNER_NOT_FOUND,
                    message="Banner not found.",
                    field="id",
                )
            )
            return DeleteBannerMutation(success=False, errors=errors)

        return DeleteBannerMutation(success=True, errors=[])


class UploadBannerImageMutation(graphene.Mutation):
    """Upload banner image to storage."""

    uploaded_file = graphene.Field(File)
    file_key = graphene.String(description="Storage key of uploaded banner image.")
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        file = Upload(
            required=True, description="Image file in a multipart request."
        )
        folder = graphene.String(
            description=(
                "Optional folder under media storage. If omitted uses `banners/`."
            )
        )

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(self, info, file, folder=None):
        try:
            file_data = _resolve_upload_from_request(info, file)
            if not file_data:
                raise ValidationError("Received an empty file.")
            validate_upload_file(file_data, UploadErrorCode, "file")
            add_hash_to_file_name(file_data)
            target_dir = _normalize_banner_folder(folder)
            storage_key = default_storage.save(
                posixpath.join(target_dir, file_data.name), file_data.file
            )
            return UploadBannerImageMutation(
                uploaded_file=File(
                    url=storage_key,
                    content_type=file_data.content_type,
                ),
                file_key=storage_key,
                errors=[],
            )
        except (KeyError, ValidationError, ValueError) as exc:
            return UploadBannerImageMutation(
                uploaded_file=None,
                file_key=None,
                errors=[
                    BannerError(
                        code=BannerErrorCode.IMAGE_UPLOAD_ERROR,
                        message=str(exc),
                        field="file",
                    )
                ],
            )


class DeleteBannerImageMutation(graphene.Mutation):
    """Delete uploaded banner image from storage."""

    success = graphene.Boolean(required=True)
    errors = graphene.List(BannerError, required=True)

    class Arguments:
        file_key = graphene.String(
            required=True, description="Storage key returned by upload mutation."
        )
        force = graphene.Boolean(
            default_value=False,
            description=(
                "Force deletion even if file key is referenced by banner records."
            ),
        )

    @one_of_permissions_required(["banner.manage_banners"])
    def mutate(self, info, file_key, force=False):
        normalized_key = (file_key or "").strip().strip("/")
        if not normalized_key.startswith(f"{BANNER_UPLOAD_ROOT_DIR}/"):
            return DeleteBannerImageMutation(
                success=False,
                errors=[
                    BannerError(
                        code=BannerErrorCode.INVALID_BANNER_DATA,
                        message=(
                            "Only files inside `banners/` are supported for deletion."
                        ),
                        field="file_key",
                    )
                ],
            )

        in_use = Banner.objects.filter(image=normalized_key).exists()
        if in_use and not force:
            return DeleteBannerImageMutation(
                success=False,
                errors=[
                    BannerError(
                        code=BannerErrorCode.IMAGE_IN_USE,
                        message=(
                            "Image is still used by one or more banners. "
                            "Pass `force: true` to delete anyway."
                        ),
                        field="file_key",
                    )
                ],
            )

        if not default_storage.exists(normalized_key):
            return DeleteBannerImageMutation(
                success=False,
                errors=[
                    BannerError(
                        code=BannerErrorCode.IMAGE_NOT_FOUND,
                        message="Image file not found.",
                        field="file_key",
                    )
                ],
            )

        default_storage.delete(normalized_key)
        return DeleteBannerImageMutation(success=True, errors=[])


class BannerMutations(graphene.ObjectType):
    """Mutations for banner management."""

    create_image_collection = CreateImageCollectionMutation.Field()
    update_image_collection = UpdateImageCollectionMutation.Field()
    delete_image_collection = DeleteImageCollectionMutation.Field()
    upload_banner_image = UploadBannerImageMutation.Field()
    delete_banner_image = DeleteBannerImageMutation.Field()
    create_banner = CreateBannerMutation.Field()
    update_banner = UpdateBannerMutation.Field()
    delete_banner = DeleteBannerMutation.Field()

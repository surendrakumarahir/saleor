from typing import List

import graphene

from ....permission.enums import ProductPermissions
from ....product.amazon_scraper import (
    fetch_amazon_page,
    normalize_amazon_url,
    parse_amazon_product,
)
from ...core.doc_category import DOC_CATEGORY_PRODUCTS
from ...core.fields import JSONString
from ...core.mutations import BaseMutation
from ...core.types import NonNullList, ProductError


class ExtractedAmazonProduct(graphene.ObjectType):
    asin = graphene.String(description="Amazon ASIN")
    url = graphene.String(description="Source Amazon URL")
    title = graphene.String(description="Product title")
    author = graphene.String(description="Author name")
    publisher = graphene.String(description="Publisher name")
    publication_date = graphene.String(description="Publication date")
    publication_year = graphene.String(description="Publication year")
    item_weight = graphene.String(description="Item weight")
    dimensions = graphene.String(description="Product dimensions")
    language = graphene.String(description="Language")
    selling_price = graphene.Float(description="Selling price in INR")
    mrp = graphene.Float(description="MRP / Original price in INR")
    description = graphene.String(description="Product description")
    specs = JSONString(description="Full extracted specifications")
    images = NonNullList(
        graphene.String, description="List of high-resolution product image URLs"
    )
    primary_image = graphene.String(description="Primary cover image URL")


class AmazonExtractError(graphene.ObjectType):
    url = graphene.String(description="Failed URL or ASIN")
    message = graphene.String(description="Error message")


class AmazonProductExtract(BaseMutation):
    success = graphene.Boolean(
        required=True,
        description="Whether extraction succeeded for at least one item",
    )
    products = NonNullList(
        ExtractedAmazonProduct, description="Extracted product objects"
    )
    extraction_errors = NonNullList(
        AmazonExtractError, description="Errors encountered during extraction"
    )

    class Arguments:
        urls = NonNullList(
            graphene.String,
            required=True,
            description="List of Amazon URLs or 10-character ASINs",
        )

    class Meta:
        description = "Extracts product information (title, author, publisher, specs, HD images) from Amazon India."
        doc_category = DOC_CATEGORY_PRODUCTS
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, /, **data):
        raw_urls = data.get("urls") or []
        clean_urls: List[str] = []
        for u in raw_urls:
            if isinstance(u, str) and u.strip():
                normalized = normalize_amazon_url(u.strip())
                if normalized.startswith("http"):
                    clean_urls.append(normalized)

        results = []
        errors = []

        for target_url in clean_urls:
            try:
                html, final_url = fetch_amazon_page(target_url)
                prod_data = parse_amazon_product(html, target_url, final_url)
                results.append(
                    ExtractedAmazonProduct(
                        asin=prod_data.get("asin"),
                        url=prod_data.get("url"),
                        title=prod_data.get("title"),
                        author=prod_data.get("author"),
                        publisher=prod_data.get("publisher"),
                        publication_date=prod_data.get("publicationDate"),
                        publication_year=prod_data.get("publicationYear"),
                        item_weight=prod_data.get("itemWeight"),
                        dimensions=prod_data.get("dimensions"),
                        language=prod_data.get("language"),
                        selling_price=prod_data.get("sellingPrice"),
                        mrp=prod_data.get("mrp"),
                        description=prod_data.get("description"),
                        specs=prod_data.get("specs"),
                        images=prod_data.get("images") or [],
                        primary_image=prod_data.get("primaryImage"),
                    )
                )
            except Exception as e:
                errors.append(
                    AmazonExtractError(
                        url=target_url, message=str(e) or "Failed to fetch Amazon page"
                    )
                )

        return cls(
            success=len(results) > 0,
            products=results,
            extraction_errors=errors,
        )

import json
import logging
from typing import List

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .amazon_scraper import (
    fetch_amazon_page,
    normalize_amazon_url,
    parse_amazon_product,
    proxy_amazon_image,
)

logger = logging.getLogger(__name__)


@csrf_exempt
def amazon_extract_view(request):
    """
    POST /api/amazon-extract/
    Accepts JSON body: {"urls": ["..."]} or {"url": "..."}
    Returns: {"success": True, "products": [...], "errors": [...]}
    """
    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body."}, status=400)

        raw_urls = body.get("urls") or []
        if isinstance(raw_urls, str):
            raw_urls = [raw_urls]
        elif not isinstance(raw_urls, list) and body.get("url"):
            raw_urls = [body["url"]]

        clean_urls: List[str] = []
        for u in raw_urls:
            if isinstance(u, str) and u.strip():
                normalized = normalize_amazon_url(u.strip())
                if normalized.startswith("http"):
                    clean_urls.append(normalized)

        if not clean_urls:
            return JsonResponse(
                {"error": "No valid Amazon URLs or ASINs provided."}, status=400
            )

        results = []
        errors = []

        for target_url in clean_urls:
            try:
                html, final_url = fetch_amazon_page(target_url)
                product_data = parse_amazon_product(html, target_url, final_url)
                results.append(product_data)
            except Exception as e:
                logger.error(f"Failed to scrape Amazon URL {target_url}: {e}", exc_info=True)
                errors.append(
                    {
                        "url": target_url,
                        "error": str(e) or "Failed to fetch Amazon product page.",
                    }
                )

        response_data = {
            "success": len(results) > 0,
            "products": results,
            "errors": errors,
        }
        res = JsonResponse(response_data, status=200)
        res["Access-Control-Allow-Origin"] = "*"
        return res

    except Exception as exc:
        logger.error(f"Unhandled error in amazon_extract_view: {exc}", exc_info=True)
        res = JsonResponse({"error": str(exc) or "Internal Server Error"}, status=500)
        res["Access-Control-Allow-Origin"] = "*"
        return res


def amazon_image_proxy_view(request):
    """
    GET /api/amazon-image-proxy/?url=...
    Streams image from Amazon avoiding CORS and hotlink issues in the dashboard.
    """
    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    image_url = request.GET.get("url")
    if not image_url or not image_url.startswith("http"):
        return HttpResponse("Invalid or missing image URL", status=400)

    try:
        content, content_type = proxy_amazon_image(image_url)
        response = HttpResponse(content, content_type=content_type)
        response["Access-Control-Allow-Origin"] = "*"
        response["Cache-Control"] = "public, max-age=86400, immutable"
        return response
    except Exception as exc:
        logger.error(f"Failed to proxy image {image_url}: {exc}")
        return HttpResponse(f"Image proxy error: {exc}", status=502)


def amazon_health_view(request):
    """
    GET /api/amazon-health/
    """
    res = JsonResponse(
        {
            "status": "ok",
            "service": "Saleor Amazon Scraper Python Service",
        }
    )
    res["Access-Control-Allow-Origin"] = "*"
    return res

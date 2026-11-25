import gzip
import html as html_lib
import json
import logging
import random
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests

import os

logger = logging.getLogger(__name__)

# Profiles with matched Client Hints and User-Agents to prevent bot detection
BROWSER_PROFILES = [
    {
        "name": "Safari-iPhone",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Referer": "https://www.amazon.in/",
        },
    },
    {
        "name": "Chrome-Android",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14; SM-S928B) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Referer": "https://www.amazon.in/",
        },
    },
    {
        "name": "Chrome-Windows",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://www.amazon.in/",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    },
    {
        "name": "Chrome-Mac",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": "en-IN,en;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://www.google.com/",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    },
    {
        "name": "Firefox-Windows",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
                "Gecko/20100101 Firefox/133.0"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-IN,en;q=0.8,en-US;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://www.google.com/",
        },
    },
]

IGNORE_AUTHOR_WORDS = {
    "follow",
    "author",
    "authors",
    "contributor",
    "contributors",
    "visit",
    "search",
    "amazon",
    "format",
    "edition",
}


def is_valid_author(cand: Optional[str]) -> bool:
    if not cand:
        return False
    lower = cand.lower().strip()
    if lower in IGNORE_AUTHOR_WORDS:
        return False
    invalid_phrases = [
        "see updates",
        "followed author",
        "your books",
        "follow",
        "visit amazon",
        "kindle edition",
        "paperback",
        "hardcover",
        "audiobook",
    ]
    if any(phrase in lower for phrase in invalid_phrases):
        return False
    return True


def is_amazon_captcha(html_text: Optional[str]) -> bool:
    if not html_text:
        return True
    lower = html_text.lower()
    return (
        "validatecaptcha" in lower
        or "type the characters you see in this image" in lower
        or "enter the characters you see below" in lower
        or "robot check" in lower
        or "api-services-support@amazon.com" in lower
        or ('<title dir="ltr">amazon.in</title>' in lower and 'id="producttitle"' not in lower)
    )


def has_product_title_content(html_text: Optional[str]) -> bool:
    if not html_text or len(html_text) < 10000:
        return False
    return bool(
        re.search(r'id=["\']productTitle["\']', html_text, re.I)
        or re.search(r'<h1[^>]*id=["\']title["\']', html_text, re.I)
        or re.search(r'property=["\']og:title["\']', html_text, re.I)
        or re.search(r'<meta\s+name=["\']title["\']', html_text, re.I)
        or re.search(r'TURBO_CHECKOUT_HEADER', html_text)
        or re.search(r'bylineContributor', html_text)
    )


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    cleaned = html_lib.unescape(cleaned)
    cleaned = (
        cleaned.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&rlm;", "")
        .replace("&lrm;", "")
        .replace("\u200e", "")
        .replace("\u200f", "")
    )
    # Collapse multiple whitespaces
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_asin_from_url(url_or_asin: Optional[str]) -> Optional[str]:
    if not url_or_asin:
        return None
    val = url_or_asin.strip()
    direct = re.match(r"^[A-Z0-9]{10}$", val, re.IGNORECASE)
    if direct:
        return direct.group(0).upper()
    match = re.search(
        r"(?:/dp/|/gp/product/|/asin/|ASIN=|/d/)([A-Z0-9]{10})",
        val,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()
    return None


def normalize_amazon_url(input_str: str) -> str:
    cleaned = input_str.strip()
    asin = extract_asin_from_url(cleaned)
    if asin and not cleaned.startswith("http"):
        return f"https://www.amazon.in/dp/{asin}"
    return cleaned


def fetch_amazon_page(url: str, timeout: int = 15) -> Tuple[str, str]:
    # 0. Check for Cloudflare Worker URL (Free, unblocked proxy)
    worker_url = (
        os.environ.get("CLOUDFLARE_WORKER_URL")
        or os.environ.get("AMAZON_CLOUDFLARE_WORKER_URL")
        or os.environ.get("AMAZON_WORKER_URL")
    )
    if worker_url:
        try:
            logger.info(f"Using Cloudflare Worker unblocker for {url}...")
            endpoint = f"{worker_url.rstrip('/')}/?url={urllib.parse.quote(url)}"
            resp = requests.get(
                endpoint,
                headers={"User-Agent": "SaleorAmazonImporter/2.0"},
                timeout=30,
            )
            if resp.status_code == 200 and not is_amazon_captcha(resp.text) and has_product_title_content(resp.text):
                logger.info(f"Cloudflare Worker successfully fetched {url}")
                return resp.text, url
            else:
                logger.warning(
                    f"Cloudflare Worker returned HTTP {resp.status_code}, captcha={is_amazon_captcha(resp.text)}, title={has_product_title_content(resp.text)}"
                )
        except Exception as cf_err:
            logger.warning(f"Cloudflare Worker request failed: {cf_err}")

    proxy_url = os.environ.get("AMAZON_SCRAPER_PROXY") or os.environ.get("SCRAPER_PROXY_URL")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    # 1. Try Chrome TLS & HTTP/2 impersonation (bypasses Amazon CloudFront WAF on datacenter IPs without proxies)
    try:
        from curl_cffi import requests as cffi_requests
        try:
            logger.info(f"Attempting Chrome TLS impersonation fetch for {url}...")
            cffi_resp = cffi_requests.get(
                url,
                impersonate="chrome131",
                timeout=timeout,
                headers={
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Referer": "https://www.google.com/",
                },
            )
            if cffi_resp.status_code == 200 and not is_amazon_captcha(cffi_resp.text) and has_product_title_content(cffi_resp.text):
                logger.info(f"Successfully fetched Amazon product page for {url} via Chrome impersonation.")
                return cffi_resp.text, str(cffi_resp.url)
        except Exception as cffi_err:
            logger.warning(f"Chrome impersonation attempt failed for {url}: {cffi_err}")
    except ImportError:
        pass

    last_error: Optional[Exception] = None

    for profile in BROWSER_PROFILES:
        session = requests.Session()
        if proxies:
            session.proxies.update(proxies)

        headers = profile["headers"]
        ua = headers["User-Agent"]

        try:
            resp = session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )
            resp.raise_for_status()

            if is_amazon_captcha(resp.text) or not has_product_title_content(resp.text):
                logger.warning(
                    f"Amazon response incomplete or CAPTCHA detected for {url} using profile {profile['name']}. Retrying with next profile..."
                )
                continue

            return resp.text, str(resp.url)

        except Exception as e:
            logger.warning(
                f"Scraper attempt failed for {url} with profile {profile['name']}: {e}"
            )
            last_error = e

    # Automatic unblocking fallback:
    # If direct requests are blocked by CAPTCHA (common on cloud/VPS providers like Hostinger),
    # fetch through the headless unblocking gateway with rendered HTML output.
    gateway_err_msg = ""
    try:
        logger.info(
            f"Direct attempts blocked or incomplete. Attempting unblocking gateway fallback for {url}..."
        )
        reader_url = f"https://r.jina.ai/{url}"
        reader_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "X-Return-Format": "html",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = requests.get(
            reader_url,
            headers=reader_headers,
            timeout=30,
            allow_redirects=True,
        )
        if resp.status_code == 200 and not is_amazon_captcha(resp.text) and has_product_title_content(resp.text):
            logger.info(
                f"Successfully fetched Amazon product page for {url} via unblocking gateway."
            )
            return resp.text, url
        else:
            gateway_err_msg = f"HTTP {resp.status_code}, captcha={is_amazon_captcha(resp.text)}, title_found={has_product_title_content(resp.text)}"
    except Exception as reader_err:
        gateway_err_msg = str(reader_err)
        logger.warning(f"Unblocking gateway fallback failed for {url}: {reader_err}")

    detail = f" [Gateway: {gateway_err_msg}]" if gateway_err_msg else ""
    raise RuntimeError(
        f"Amazon Anti-Bot Verification (CAPTCHA) blocked all requests.{detail} "
        "Server IP may be rate-limited by Amazon. Please set CLOUDFLARE_WORKER_URL or AMAZON_SCRAPER_PROXY in .env.prod."
    )


def parse_amazon_product(
    html: str, source_url: str, final_url: str = ""
) -> Dict[str, Any]:
    if is_amazon_captcha(html):
        raise RuntimeError(
            "Amazon anti-bot security (CAPTCHA) was returned instead of product page. "
            "Please configure AMAZON_SCRAPER_PROXY or retry."
        )

    url_to_examine = final_url or source_url
    asin = (
        extract_asin_from_url(url_to_examine)
        or extract_asin_from_url(source_url)
        or ""
    )

    if not asin:
        can_match = re.search(
            r'<link\s+rel="canonical"\s+href="[^"]*/dp/([A-Z0-9]{10})"',
            html,
            re.IGNORECASE,
        )
        if can_match:
            asin = can_match.group(1).upper()

    if not asin:
        inp_match = re.search(
            r'<(?:input|div)[^>]*(?:id="ASIN"|name="ASIN"|data-asin="([A-Z0-9]{10})")[^>]*value="?([A-Z0-9]{10})"?',
            html,
            re.IGNORECASE,
        )
        if inp_match:
            asin = (inp_match.group(1) or inp_match.group(2) or "").upper()

    # 1. Title Extraction
    title = ""
    title_m = (
        re.search(
            r'<span[^>]*id=["\']productTitle["\'][^>]*>(.*?)</span>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        or re.search(
            r'<h1[^>]*id=["\']title["\'][^>]*>.*?<span[^>]*>(.*?)</span>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        or re.search(
            r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']',
            html,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if title_m:
        title = clean_text(title_m.group(1))
    else:
        turbo = re.search(r'"TURBO_CHECKOUT_HEADER"\s*:\s*"Buy now:\s*(.*?)"', html)
        if turbo:
            title = clean_text(turbo.group(1))

    if not title:
        meta_m = re.search(
            r'<meta\s+name=["\']title["\']\s+content=["\'](.*?)["\']',
            html,
            re.IGNORECASE,
        )
        if meta_m:
            raw = clean_text(meta_m.group(1))
            raw = re.sub(r"^Buy\s+", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*\|\s*.*$", "", raw)
            raw = re.sub(r"\s+Book\s+Book\s+Online.*$", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s+Book\s+Online.*$", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r":\s*Amazon\.(in|com|co\.uk|de|ca).*$", "", raw, flags=re.IGNORECASE)
            if raw.strip():
                title = raw.strip()

    if not title:
        raw_t = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if raw_t:
            title = clean_text(raw_t.group(1))
            title = re.sub(
                r"^Buy\s+",
                "",
                title,
                flags=re.IGNORECASE,
            )
            title = re.sub(
                r":\s*Amazon\.(in|com|co\.uk|de|ca).*$",
                "",
                title,
                flags=re.IGNORECASE,
            ).strip()

    # 2. Author Extraction (with robust filtering)
    author = ""
    # Pattern A: author span with link or text
    author_matches = re.finditer(
        r'<span[^>]*class=["\'][^"\']*author[^"\']*["\'][^>]*>(.*?)</span>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for am in author_matches:
        span_content = am.group(1)
        a_tag = re.search(r"<a[^>]*>(.*?)</a>", span_content, re.IGNORECASE | re.DOTALL)
        if a_tag:
            cand = clean_text(a_tag.group(1))
            cand_clean = re.sub(r"\(Author\)", "", cand, flags=re.IGNORECASE).strip()
            if is_valid_author(cand_clean):
                author = cand_clean
                break
        else:
            cand = clean_text(span_content)
            cand_clean = re.sub(r"\(Author\)", "", cand, flags=re.IGNORECASE).strip()
            if is_valid_author(cand_clean):
                author = cand_clean
                break

    # Pattern B: byline contributor
    if not author:
        byline_m = re.search(
            r'id=["\']bylineInfo["\'][^>]*>(.*?)</div>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if byline_m:
            by_text = byline_m.group(1)
            by_link = re.search(
                r'by\s+<a[^>]*class=["\'][^"\']*contributorNameID[^"\']*["\'][^>]*>(.*?)</a>',
                by_text,
                re.IGNORECASE | re.DOTALL,
            ) or re.search(r"by\s+<a[^>]*>(.*?)</a>", by_text, re.IGNORECASE | re.DOTALL)
            if by_link:
                cand = clean_text(by_link.group(1))
                if is_valid_author(cand):
                    author = cand

    # Pattern C: contributorNameID everywhere
    if not author:
        contrib_m = re.search(
            r'class=["\'][^"\']*contributorNameID[^"\']*["\'][^>]*>(.*?)</a>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if contrib_m:
            cand = clean_text(contrib_m.group(1))
            if is_valid_author(cand):
                author = cand

    # Pattern D: Mobile bylineContributor
    if not author:
        byline_c = re.search(
            r'<a[^>]*id=["\']bylineContributor["\'][^>]*>(.*?)</a>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if byline_c:
            cand = clean_text(byline_c.group(1))
            cand_clean = re.sub(r"\(Author\)", "", cand, flags=re.IGNORECASE).strip()
            if is_valid_author(cand_clean):
                author = cand_clean

    # Pattern E: Author profile links /e/
    if not author:
        for m in re.finditer(
            r'<a[^>]*href=["\']/[^"\']+/e/[A-Z0-9]+[^"\']*["\'][^>]*>(.*?)</a>',
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            cand = clean_text(m.group(1))
            cand_clean = re.sub(r"\(Author\)", "", cand, flags=re.IGNORECASE).strip()
            if is_valid_author(cand_clean):
                author = cand_clean
                break

    # 3. Price & MRP Extraction
    selling_price = None
    mrp = None

    # Check targeted buybox/twister/apex price first (avoids sponsored ads)
    m_box_price = (
        re.search(r'"priceAmount"\s*:\s*([\d.]+)', html)
        or re.search(r'name=["\']items\[0\.base\]\[customerVisiblePrice\]\[amount\]["\']\s+value=["\']([\d.]+)["\']', html)
        or re.search(r'id=["\']twister-plus-price-data-price["\']\s+value=["\']([\d.]+)["\']', html)
        or re.search(r'id=["\']tp_price_block_total_price_in["\'].*?<span[^>]*class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>([\d,]+)', html, re.DOTALL)
        or re.search(r'id=["\'](?:corePriceDisplay_desktop_feature_div|corePrice_desktop|apex_desktop)["\'].*?<span[^>]*class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>([\d,]+)', html, re.DOTALL)
    )
    if m_box_price:
        try:
            selling_price = float(m_box_price.group(1).replace(",", ""))
        except ValueError:
            pass

    if selling_price is None:
        price_whole = re.search(
            r'<span[^>]*class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>([\d,]+)',
            html,
            re.IGNORECASE,
        )
        price_frac = re.search(
            r'<span[^>]*class=["\'][^"\']*a-price-fraction[^"\']*["\'][^>]*>(\d+)',
            html,
            re.IGNORECASE,
        )
        if price_whole:
            w = price_whole.group(1).replace(",", "")
            f = price_frac.group(1) if price_frac else "00"
            try:
                selling_price = float(f"{w}.{f}")
            except ValueError:
                pass

    if selling_price is None:
        offscreen = re.search(
            r'<span[^>]*class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>₹?\s*([\d,]+(?:\.\d+)?)',
            html,
            re.IGNORECASE,
        )
        if offscreen:
            try:
                selling_price = float(offscreen.group(1).replace(",", ""))
            except ValueError:
                pass

    mrp_m = (
        re.search(
            r'<span[^>]*class=["\'][^"\']*a-price\s+a-text-price[^"\']*["\'][^>]*>.*?<span[^>]*class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>₹?\s*([\d,]+(?:\.\d+)?)',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        or re.search(
            r'M\.R\.P\.:.*?<span[^>]*class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>₹?\s*([\d,]+(?:\.\d+)?)',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        or re.search(
            r'data-a-strike=["\']true["\'][^>]*><span[^>]*>₹?\s*([\d,]+(?:\.\d+)?)',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        or re.search(
            r'id=["\']listPrice["\'][^>]*>.*?₹?\s*([\d,]+(?:\.\d+)?)',
            html,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if mrp_m:
        try:
            mrp = float(mrp_m.group(1).replace(",", ""))
        except ValueError:
            pass

    if selling_price is not None and mrp is None:
        mrp = selling_price

    # 4. Specifications & Product Details Extraction
    specs: Dict[str, str] = {}

    # 4A. Detail Bullets: <li><span class="a-list-item"><span class="a-text-bold">KEY : </span><span>VALUE</span></span></li>
    bullet_matches = re.finditer(
        r'<span[^>]*class=["\'][^"\']*a-list-item[^"\']*["\'][^>]*>.*?<span[^>]*class=["\'][^"\']*a-text-bold[^"\']*["\'][^>]*>(.*?)</span>.*?<span>(.*?)</span>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for m in bullet_matches:
        k = clean_text(m.group(1)).rstrip(":").strip()
        v = clean_text(m.group(2)).strip()
        if k and v:
            specs[k] = v

    # 4B. RPI (Rich Product Information) Carousel Cards
    rpi_matches = re.finditer(
        r'rpi-attribute-label[^>]*>.*?<span>(.*?)</span>.*?rpi-attribute-value[^>]*>.*?<span>(.*?)</span>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for m in rpi_matches:
        k = clean_text(m.group(1)).rstrip(":").strip()
        v = clean_text(m.group(2)).strip()
        if k and v and k not in specs:
            specs[k] = v

    # 4C. Product Details Table (th / td)
    table_matches = re.finditer(
        r'<th[^>]*>(.*?)</th>.*?<td[^>]*>(.*?)</td>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for m in table_matches:
        k = clean_text(m.group(1)).rstrip(":").strip()
        v = clean_text(m.group(2)).strip()
        if k and v and k not in specs:
            specs[k] = v

    # Normalized field extraction
    raw_publisher = (
        specs.get("Publisher")
        or specs.get("Publisher:")
        or specs.get("Manufacturer")
        or specs.get("Brand")
        or ""
    )
    # Remove trailing edition or date info from publisher if present (e.g. "Shri Vinod Pustak Mandir; 2021st edition (1 January 2021)")
    publisher = re.sub(r";.*$", "", raw_publisher).strip()
    if not publisher:
        mob_pub = re.search(
            r'<span[^>]*class=["\'][^"\']*offer-display-feature-text-message[^"\']*["\'][^>]*>(.*?)</span>',
            html,
            re.IGNORECASE,
        )
        if mob_pub:
            publisher = clean_text(mob_pub.group(1))

    publication_date = (
        specs.get("Publication date")
        or specs.get("Publication date:")
        or specs.get("Publication Date")
        or specs.get("Date First Available")
        or ""
    )
    pub_year_m = re.search(r"\b(19\d\d|20\d\d)\b", publication_date) or re.search(
        r"\b(19\d\d|20\d\d)\b", raw_publisher
    )
    publication_year = pub_year_m.group(1) if pub_year_m else ""

    item_weight = (
        specs.get("Item Weight")
        or specs.get("Item Weight:")
        or specs.get("Weight")
        or ""
    )
    dimensions = (
        specs.get("Dimensions")
        or specs.get("Dimensions:")
        or specs.get("Product Dimensions")
        or specs.get("Package Dimensions")
        or ""
    )
    language = specs.get("Language") or specs.get("Language:") or ""

    # 5. Description
    description = ""
    desc_exp = re.search(
        r'data-a-expander-name=["\']book_description_expander["\'][^>]*>.*?<div[^>]*class=["\'][^"\']*a-expander-content[^"\']*["\'][^>]*>(.*?)</div>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if desc_exp:
        raw_desc = desc_exp.group(1)
        raw_desc = re.sub(r"<br\s*/?>", "\n", raw_desc, flags=re.IGNORECASE)
        raw_desc = re.sub(r"</p>", "\n\n", raw_desc, flags=re.IGNORECASE)
        description = clean_text(raw_desc)

    if not description:
        prod_desc = re.search(
            r'<div[^>]*id=["\']productDescription["\'][^>]*>(.*?)</div>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if prod_desc:
            raw_desc = prod_desc.group(1)
            raw_desc = re.sub(r"<br\s*/?>", "\n", raw_desc, flags=re.IGNORECASE)
            raw_desc = re.sub(r"</p>", "\n\n", raw_desc, flags=re.IGNORECASE)
            description = clean_text(raw_desc)

    if not description:
        feat_bullets = re.search(
            r'<div[^>]*id=["\']feature-bullets["\'][^>]*>(.*?)</div>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if feat_bullets:
            items = re.findall(
                r'<span[^>]*class=["\']a-list-item["\'][^>]*>(.*?)</span>',
                feat_bullets.group(1),
                re.IGNORECASE | re.DOTALL,
            )
            cleaned_items = [clean_text(it) for it in items if clean_text(it)]
            description = "\n\n".join(cleaned_items)

    # 6. Images Extraction (Comprehensive product gallery extractor)
    raw_images: List[str] = []

    # 6A. All hiRes images found in script/JSON blocks
    all_hires = re.findall(
        r'["\']hiRes["\']\s*:\s*["\'](https://[^"\'\s]+)["\']', html, re.IGNORECASE
    )
    raw_images.extend(all_hires)

    # 6B. Dynamic image blocks in main left column / imageBlock container
    left_col = re.search(
        r'id=["\'](?:imageBlock|main-image-container|altImages|imageBlockATF|leftCol)["\'][\s\S]*?(?:id=["\']centerCol["\']|id=["\']desktop_buybox["\']|$)',
        html,
        re.IGNORECASE,
    )
    if left_col:
        dyns = re.findall(
            r'data-a-dynamic-image=["\']({[^"\']+}?)["\']',
            left_col.group(0),
            re.IGNORECASE,
        )
        for dm in dyns:
            try:
                parsed = json.loads(html_lib.unescape(dm))
                raw_images.extend(parsed.keys())
            except Exception:
                pass
    else:
        # Fallback to all data-a-dynamic-image in page
        dyns = re.findall(
            r'data-a-dynamic-image=["\']({[^"\']+}?)["\']', html, re.IGNORECASE
        )
        for dm in dyns:
            try:
                parsed = json.loads(html_lib.unescape(dm))
                raw_images.extend(parsed.keys())
            except Exception:
                pass

    # 6C. Landing Image & Front Cover
    landing_hires = re.search(
        r'id=["\']landingImage["\'][^>]*data-old-hires=["\']([^"\'\s]+)["\']',
        html,
        re.IGNORECASE,
    )
    if landing_hires:
        raw_images.append(landing_hires.group(1))

    landing_src = re.search(
        r'id=["\']landingImage["\'][^>]*src=["\']([^"\'\s]+)["\']',
        html,
        re.IGNORECASE,
    )
    if landing_src:
        raw_images.append(landing_src.group(1))

    img_front_hires = re.search(
        r'id=["\']imgBlkFront["\'][^>]*data-old-hires=["\']([^"\'\s]+)["\']',
        html,
        re.IGNORECASE,
    )
    if img_front_hires:
        raw_images.append(img_front_hires.group(1))

    img_front = re.search(
        r'id=["\']imgBlkFront["\'][^>]*src=["\']([^"\'\s]+)["\']',
        html,
        re.IGNORECASE,
    )
    if img_front:
        raw_images.append(img_front.group(1))

    # 6D. Mobile image wrappers & direct Amazon product images
    for m in re.finditer(
        r'<img[^>]*class=["\'][^"\']*(?:fp-image-wrapper|main-image|a-dynamic-image)[^"\']*["\'][^>]*src=["\']([^"\'\s]+)["\']',
        html,
        re.IGNORECASE,
    ):
        raw_images.append(m.group(1))

    for m in re.finditer(
        r'https://images-(?:eu|na)\.ssl-images-amazon\.com/images/I/[A-Za-z0-9%_-]+\.jpg',
        html,
    ):
        raw_images.append(m.group(0))

    # 6E. Clean, normalize to SL1500, and deduplicate by Amazon image ID
    clean_images: List[str] = []
    seen_ids = set()

    for img in raw_images:
        if (
            not img
            or not img.startswith("http")
            or any(
                k in img
                for k in [
                    "sprite",
                    "transparent-pixel",
                    "play-button",
                    "grey-pixel",
                    "pixel",
                ]
            )
        ):
            continue

        # Convert thumbnails/medium resolutions to highest resolution SL1500
        high_res = re.sub(
            r"\._[A-Z0-9_,]+_(\.[a-z]+)$", r"._SL1500_\1", img, flags=re.IGNORECASE
        )

        # Extract Amazon Media ID (e.g., '81Ckzmobv9L' from 'https://.../images/I/81Ckzmobv9L._SL1500_.jpg')
        id_match = re.search(
            r"/images/I/([a-zA-Z0-9\-_+]+)(?:\._[A-Z0-9_,]+_)?(\.[a-z]+)$",
            high_res,
            re.IGNORECASE,
        )
        if id_match:
            img_id = id_match.group(1)
            if img_id not in seen_ids:
                seen_ids.add(img_id)
                clean_images.append(high_res)
        elif high_res not in seen_ids:
            seen_ids.add(high_res)
            clean_images.append(high_res)

    return {
        "asin": asin,
        "url": url_to_examine,
        "title": title or (f"Amazon Product {asin}" if asin else "Imported Amazon Product"),
        "author": author,
        "publisher": publisher,
        "publicationDate": publication_date,
        "publicationYear": publication_year,
        "itemWeight": item_weight,
        "dimensions": dimensions,
        "language": language,
        "sellingPrice": selling_price,
        "mrp": mrp,
        "description": description,
        "specs": specs,
        "images": clean_images,
        "primaryImage": clean_images[0] if clean_images else "",
    }


def proxy_amazon_image(image_url: str, timeout: int = 10) -> Tuple[bytes, str]:
    proxy_url = os.environ.get("AMAZON_SCRAPER_PROXY") or os.environ.get("SCRAPER_PROXY_URL")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.amazon.in/",
    }
    resp = requests.get(
        image_url,
        headers=headers,
        proxies=proxies,
        timeout=timeout,
        allow_redirects=True,
    )
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return resp.content, content_type

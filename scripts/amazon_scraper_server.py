#!/usr/bin/env python3
"""
Standalone Production Amazon Scraper & Image Proxy Server in Python
Runs independently on any port (default: 9005 or os.environ.get("PORT"))
"""
import os
import sys

# Add parent directory to path so it can import from saleor.product.amazon_scraper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from saleor.product.amazon_scraper import (
    fetch_amazon_page,
    normalize_amazon_url,
    parse_amazon_product,
    proxy_amazon_image,
)

import http.server
import json
import logging
import socketserver
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("amazon_scraper")

PORT = int(os.environ.get("PORT", 9005))


class AmazonScraperHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def _set_cors_headers(self, content_type="application/json"):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        if content_type:
            self.send_header("Content-Type", content_type)

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers(None)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("", "/health", "/api/amazon-health"):
            self.send_response(200)
            self._set_cors_headers("application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "ok",
                        "service": "Amazon Scraper Python Microservice",
                    }
                ).encode("utf-8")
            )
            return

        if path == "/api/amazon-image-proxy":
            url_list = query.get("url")
            image_url = url_list[0] if url_list else None
            if not image_url or not image_url.startswith("http"):
                self.send_response(400)
                self._set_cors_headers("text/plain")
                self.end_headers()
                self.wfile.write(b"Invalid or missing image URL")
                return

            try:
                content, content_type = proxy_amazon_image(image_url)
                self.send_response(200)
                self._set_cors_headers(content_type)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(502)
                self._set_cors_headers("text/plain")
                self.end_headers()
                self.wfile.write(f"Image proxy error: {e}".encode("utf-8"))
            return

        self.send_response(404)
        self._set_cors_headers("application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/amazon-extract":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                payload = json.loads(body_bytes.decode("utf-8") or "{}")
            except Exception:
                self.send_response(400)
                self._set_cors_headers("application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"error": "Invalid JSON body"}).encode("utf-8")
                )
                return

            raw_urls = payload.get("urls") or []
            if isinstance(raw_urls, str):
                raw_urls = [raw_urls]
            elif not isinstance(raw_urls, list) and payload.get("url"):
                raw_urls = [payload["url"]]

            clean_urls = [
                normalize_amazon_url(u.strip())
                for u in raw_urls
                if isinstance(u, str) and u.strip()
            ]
            clean_urls = [u for u in clean_urls if u.startswith("http")]

            if not clean_urls:
                self.send_response(400)
                self._set_cors_headers("application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"error": "No valid URLs or ASINs provided"}).encode(
                        "utf-8"
                    )
                )
                return

            results = []
            errors = []

            for target_url in clean_urls:
                try:
                    html, final_url = fetch_amazon_page(target_url)
                    prod = parse_amazon_product(html, target_url, final_url)
                    results.append(prod)
                except Exception as e:
                    logger.error(f"Failed to scrape {target_url}: {e}")
                    errors.append({"url": target_url, "error": str(e)})

            self.send_response(200)
            self._set_cors_headers("application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "success": len(results) > 0,
                        "products": results,
                        "errors": errors,
                    }
                ).encode("utf-8")
            )
            return

        self.send_response(404)
        self._set_cors_headers("application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AmazonScraperHTTPRequestHandler) as httpd:
        logger.info(f"Python Amazon Scraper Microservice running on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Stopping scraper server...")
            httpd.shutdown()


if __name__ == "__main__":
    main()

/**
 * Cloudflare Worker Amazon Unblocker Proxy (100% Free - 100k requests/day)
 * Used by Saleor 1-Click Amazon Product Importer
 */
export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const reqUrl = new URL(request.url);
    const targetUrl =
      reqUrl.searchParams.get("url") || reqUrl.searchParams.get("asin");

    if (!targetUrl) {
      return new Response(
        JSON.stringify({ error: "Missing 'url' or 'asin' query parameter" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const fullUrl = targetUrl.startsWith("http")
      ? targetUrl
      : `https://www.amazon.in/dp/${targetUrl}`;

    try {
      // Mobile Safari profile bypasses Amazon CloudFront WAF without CAPTCHA
      const amazonResp = await fetch(fullUrl, {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
          Accept:
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-IN,en;q=0.9",
          Referer: "https://www.amazon.in/",
        },
      });

      const bodyText = await amazonResp.text();

      return new Response(bodyText, {
        status: amazonResp.status,
        headers: {
          ...corsHeaders,
          "Content-Type": "text/html; charset=utf-8",
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  },
};

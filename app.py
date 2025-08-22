from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request
import re
import json
from urllib.parse import urljoin

BASE_URL = "https://time.com"

# --- Step 1: Fetch HTML ---
def fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TimeBot/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")

# --- Step 2: Parse HTML (basic regex) ---
def parse_latest_stories(html_text: str, limit: int = 6):
    """
    Parse HTML using regex only (no external libs).
    Extracts the first 6 article links under 'LATEST STORIES'.
    """
    stories = []
    seen = set()

    # Regex to capture anchors
    anchor_pattern = re.compile(
        r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<text>.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )

    # Article links look like: /6142934/...
    article_pattern = re.compile(r"/\d{7,}/")

    for match in anchor_pattern.finditer(html_text):
        href = match.group("href")
        text = match.group("text")

        # Normalize href
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = urljoin(BASE_URL, href)

        if not href.startswith(BASE_URL):
            continue
        if not article_pattern.search(href):
            continue

        # Strip HTML tags from text
        clean_title = re.sub(r"<[^>]*>", "", text, flags=re.DOTALL).strip()
        clean_title = re.sub(r"\s+", " ", clean_title)

        if not clean_title:
            continue

        if href not in seen:
            stories.append({"title": clean_title, "link": href})
            seen.add(href)

        if len(stories) >= limit:
            break

    return stories

# --- Step 3: API Handler ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/getTimeStories":
            try:
                html_text = fetch_html(BASE_URL)
                stories = parse_latest_stories(html_text, limit=6)

                if not stories:
                    response = {"error": "No stories found"}
                    self.send_response(502)
                else:
                    response = stories
                    self.send_response(200)

                payload = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            except Exception as e:
                msg = {"error": f"Unexpected error: {e}"}
                payload = json.dumps(msg).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found. Try /getTimeStories")

# --- Step 4: Run server ---
if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Server running at http://localhost:8000/getTimeStories")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

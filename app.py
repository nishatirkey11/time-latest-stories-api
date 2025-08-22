from flask import Flask, jsonify, Response
import urllib.request
import urllib.error
from urllib.parse import urljoin
import re
import html

app = Flask(__name__)

BASE_URL = "https://time.com"

def fetch_html(url: str) -> str:
    
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TimeLatestStoriesBot/1.0)"
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def strip_tags(text: str) -> str:
    no_tags = re.sub(r"<[^>]*>", "", text, flags=re.DOTALL)

    return html.unescape(no_tags).strip()


def parse_latest_stories(html_text: str, max_items: int = 6):
    
    stories = []
    seen_links = set()

    
    anchor_pattern = re.compile(
        r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<text>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    article_id_pattern = re.compile(r"/\d{7,}/", re.IGNORECASE)

    for m in anchor_pattern.finditer(html_text):
        href = m.group("href")
        text = m.group("text")

        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = urljoin(BASE_URL, href)

        if not href.startswith("https://time.com"):
            continue
        if not article_id_pattern.search(href):
            continue

        title = strip_tags(text)
        if not title:
            continue

        title = re.sub(r"\s+", " ", title).strip()

        if href not in seen_links:
            stories.append({"title": title, "link": href})
            seen_links.add(href)

        if len(stories) >= max_items:
            break

    return stories


@app.get("/getTimeStories")
def get_time_stories():
    try:
        page_html = fetch_html(BASE_URL)
        items = parse_latest_stories(page_html, max_items=6)

        if not items:
            return jsonify({"error": "No stories found. Page structure may have changed."}), 502

        return jsonify(items)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        return jsonify({"error": f"Failed to fetch Time.com: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@app.get("/")
def root():
    return Response(
        "OK. Use /getTimeStories to fetch latest 6 Time.com stories.",
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

#Configuration

CONFIG = {
    "BASE_URL": "https://time.com",
    "STORIES_TO_FETCH": 6,
    "REQUEST_TIMEOUT": 15,
    "USER_AGENT": "Mozilla/5.0 (compatible; TimeLatestStoriesBot/1.0; +http://example.com/bot)"
}

#Core Logic

def get_page_content(url):
    
    headers = {"User-Agent": CONFIG["USER_AGENT"]}
    response = requests.get(url, headers=headers, timeout=CONFIG["REQUEST_TIMEOUT"])
    response.raise_for_status()  
    return response.text

def extract_story_data(html_content):
    
    soup = BeautifulSoup(html_content, 'html.parser')
    articles = []
    processed_urls = set()
    
    
    for link_tag in soup.find_all('a', href=True):
        
        title = link_tag.get_text(strip=True)
        if not title:
            continue

        url = link_tag['href']
        
        
        if url.startswith('/'):
            url = urljoin(CONFIG["BASE_URL"], url)
            
        
        is_story_link = (
            url.startswith(CONFIG["BASE_URL"]) and 
            re.search(r'/\d{7,}/', url) and 
            url not in processed_urls
        )

        if is_story_link:
            articles.append({'title': title, 'link': url})
            processed_urls.add(url)
            
            
            if len(articles) >= CONFIG["STORIES_TO_FETCH"]:
                break
                
    return articles

#Flask Application Setup

app = Flask(__name__)

@app.route('/getTimeStories', methods=['GET'])
def stories_api_endpoint():
    """API endpoint to fetch the latest stories."""
    try:
        page_html = get_page_content(CONFIG["BASE_URL"])
        latest_stories = extract_story_data(page_html)
        
        if not latest_stories:
            error_message = "Could not find any stories. The website's structure may have changed."
            return jsonify({"error": error_message}), 502 

        return jsonify(latest_stories)

    except requests.exceptions.RequestException as e:
        
        error_message = f"Error fetching data from Time.com: {e}"
        return jsonify({"error": error_message}), 502
        
    except Exception as e:
        
        return jsonify({"error": f"An unexpected internal error occurred: {e}"}), 500

@app.route('/', methods=['GET'])
def index():
    """Root endpoint to confirm the service is running."""
    return "Service is active. Please use the /getTimeStories endpoint to get the latest articles."

#Main Execution

if __name__ == '__main__':
    
    app.run(host="0.0.0.0", port=5000, debug=True)

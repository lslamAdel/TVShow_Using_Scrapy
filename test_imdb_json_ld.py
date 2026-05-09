"""
Test script to find JSON-LD and other data sources for IMDB genres and description
"""
import json
import requests
from scrapy.http import HtmlResponse

# Test URL (Breaking Bad S1E1)
test_url = "https://www.imdb.com/title/tt0959621/"

print("Fetching IMDB page...")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    response = requests.get(test_url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # Parse with Scrapy
    scrapy_response = HtmlResponse(
        url=test_url,
        body=response.content,
        encoding='utf-8'
    )
    
    print("\n" + "="*80)
    print("EXTRACTING JSON-LD DATA")
    print("="*80)
    
    json_ld_scripts = scrapy_response.xpath(
        '//script[@type="application/ld+json"]/text()'
    ).getall()
    
    print(f"Found {len(json_ld_scripts)} JSON-LD scripts\n")
    
    for idx, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script)
            print(f"\n--- JSON-LD Block {idx+1} ---")
            if isinstance(data, list):
                for item in data:
                    item_type = item.get("@type", "Unknown")
                    print(f"Type: {item_type}")
                    if item_type in ["Movie", "TVEpisode"]:
                        print(f"  Name: {item.get('name', 'N/A')}")
                        print(f"  Genre: {item.get('genre', 'N/A')}")
                        print(f"  Description: {str(item.get('description', 'N/A'))[:100]}")
            else:
                item_type = data.get("@type", "Unknown")
                print(f"Type: {item_type}")
                if item_type in ["Movie", "TVEpisode"]:
                    print(f"  Name: {data.get('name', 'N/A')}")
                    print(f"  Genre: {data.get('genre', 'N/A')}")
                    print(f"  Description: {str(data.get('description', 'N/A'))[:100]}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
    
    print("\n" + "="*80)
    print("CHECKING OG META TAGS")
    print("="*80)
    
    og_tags = scrapy_response.css('meta[property^="og:"]').getall()
    for tag in og_tags[:10]:
        print(tag)
    
    print("\n" + "="*80)
    print("CHECKING OTHER META TAGS")
    print("="*80)
    
    meta_tags = scrapy_response.css('meta[name]').getall()
    for tag in meta_tags[:10]:
        print(tag)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

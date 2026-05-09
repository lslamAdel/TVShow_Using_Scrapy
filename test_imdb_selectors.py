"""
Test script to find correct CSS selectors for IMDB genres and description
"""
import scrapy
from scrapy.http import HtmlResponse
import requests

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
    print("TESTING GENRES SELECTORS")
    print("="*80)
    
    # Test all genre selectors
    selectors_to_test = [
        ('[data-testid="genres"] a span::text', "Primary data-testid genres"),
        ('.ipc-chip__text::text', "IPC chip text"),
        ('a[href*="genres="] span::text', "Genre search link span"),
        ('[data-testid="genres"]', "Genres container (raw)"),
        ('//span[@data-testid="genre"]//text()', "Genre spans via xpath"),
        ('span.ipc-chip::text', "IPC chip text alt"),
    ]
    
    for selector, desc in selectors_to_test:
        if selector.startswith('//'):
            result = scrapy_response.xpath(selector).getall()
        else:
            result = scrapy_response.css(selector).getall()
        print(f"\n{desc}:")
        print(f"  Selector: {selector}")
        print(f"  Found: {result if result else 'NONE'}")
    
    print("\n" + "="*80)
    print("TESTING DESCRIPTION SELECTORS")
    print("="*80)
    
    desc_selectors = [
        ('[data-testid="plot-xl"]::text', "Plot XL"),
        ('[data-testid="plot-l"]::text', "Plot L"),
        ('[data-testid="plot"]::text', "Plot"),
        ('//span[@data-testid="plot-xl"]/text()', "Plot XL xpath"),
        ('//div[@data-testid="plot"]//span/text()', "Plot div xpath"),
        ('//p[@data-testid="plot"]/text()', "Plot p xpath"),
        ('meta[name="description"]::attr(content)', "Meta description"),
    ]
    
    for selector, desc in desc_selectors:
        if selector.startswith('//'):
            result = scrapy_response.xpath(selector).get()
        else:
            result = scrapy_response.css(selector).get()
        print(f"\n{desc}:")
        print(f"  Selector: {selector}")
        if result:
            print(f"  Found: {result[:100]}...")
        else:
            print(f"  Found: NONE")
    
    # Also print some raw HTML around plot/genres sections for manual inspection
    print("\n" + "="*80)
    print("RAW HTML SNIPPETS - LOOKING FOR GENRES")
    print("="*80)
    
    # Get HTML around genres
    html_text = response.text
    if "genres" in html_text.lower():
        idx = html_text.lower().find("genres")
        print(html_text[max(0, idx-200):idx+300])
    
    print("\n" + "="*80)
    print("RAW HTML SNIPPETS - LOOKING FOR PLOT")
    print("="*80)
    
    if "plot" in html_text.lower():
        idx = html_text.lower().find("plot")
        print(html_text[max(0, idx-200):idx+400])

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

import scrapy
from TVShow_crawler.items import TvshowCrawlerItem
from urllib.parse import urljoin
import requests


class ShowSpider(scrapy.Spider):
    name = "shows"
    allowed_domains = ["seriesgraph.com"]
    start_urls = [
        "https://seriesgraph.com/all-shows/1"
    ]

    def parse(self,response):
        # Find all links to shows
        show_links = response.css('a[href*="/show/"]')
        seen_links = set()

        for link in show_links:
            href = link.css('::attr(href)').get()

            if href and href not in seen_links:
                seen_links.add(href)
                full_url = urljoin(response.url, href)
                
                # Extract show name from URL slug
                slug = href.split('/')[-1]
                if '-' in slug:
                    showname = slug.split('-', 1)[1].replace('-', ' ').title()
                else:
                    showname = slug.title()

                if showname and 'seriesgraph.com' in full_url:
                    item = TvshowCrawlerItem()
                    item['showname'] = showname
                    item['link'] = full_url

                    yield scrapy.Request(
                        full_url,
                        callback=self.parse_show,
                        meta={'item':item}
                    )

    def parse_show(self, response):
        item = response.meta['item']
        
        slug = response.url.split('/')[-1]
       
        # Extract rating
        rating = response.css('strong::text').get()
        if rating:

            item['rating'] = rating

        #-------------------------------------------------------------------------------------------------------------------------

        # Fetch data from API
        api_url = f'https://seriesgraph.com/api/shows/{slug}'
        try:
            api_resp = requests.get(api_url, timeout=5)
            if api_resp.status_code == 200:
                data = api_resp.json()
                
                
                # Extract poster
                poster_path = data.get('poster_path')
                if poster_path:
                    # Construct full poster URL from TMDB
                    poster_url = f'https://image.tmdb.org/t/p/w400{poster_path}'
                    item['poster'] = poster_url
        except Exception as e:
            self.logger.warning(f'Failed to fetch API data for {slug}: {e}')
        
        #-------------------------------------------------------------------------------------------------------------------------
        yield item
        
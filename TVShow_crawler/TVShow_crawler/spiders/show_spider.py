import re
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import scrapy
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from TVShow_crawler.items import TvshowCrawlerItem


class ShowSpider(scrapy.Spider):
    name = "shows"
    allowed_domains = ["seriesgraph.com", "imdb.com"]

    custom_settings = {
        "DOWNLOAD_DELAY"          : 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "DEFAULT_REQUEST_HEADERS" : {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_show_links = set()
        self.driver           = None
        self.total_pages      = 1  # TEST: Limited to 1 page for quick test

    # ── Selenium ──────────────────────────────────────────────────────────────

    def init_selenium(self):
        if self.driver:
            return
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")

        driver_path = self.settings.get("SELENIUM_DRIVER_EXECUTABLE_PATH")
        service = None
        if driver_path:
            p = Path(driver_path)
            if not p.is_absolute():
                p = Path(__file__).resolve().parents[2] / p
            if p.exists():
                service = Service(str(p))
            else:
                self.logger.warning(
                    f"ChromeDriver not found at {p}, falling back to webdriver-manager."
                )
        if service is None:
            service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.implicitly_wait(5)

    def closed(self, reason):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def make_selenium_response(self, url):
        try:
            self.init_selenium()
            self.driver.get(url)
            time.sleep(2)
            return HtmlResponse(
                url=url,
                body=self.driver.page_source,
                encoding="utf-8",
                request=scrapy.Request(url),
            )
        except Exception as exc:
            self.logger.warning(f"Selenium failed for {url}: {exc}")
            return None

    def extract_episode_data_from_d3(self) -> list[dict]:
        """
        Read D3 __data__ from every SVG rect.
        tconst is the IMDB title ID → build the full IMDB URL here.
        """
        return self.driver.execute_script("""
            const episodes = [];
            document.querySelectorAll('svg rect').forEach(r => {
                const d = r.__data__;
                if (d && d.tconst) {
                    episodes.push({
                        season       : d.season_number,
                        episode      : d.episode_number,
                        name         : d.name         || null,
                        vote_average : d.vote_average || null,
                        num_votes    : d.num_votes    || null,
                        air_date     : d.air_date     || null,
                        overview     : d.overview     || null,
                        runtime      : d.runtime      || null,
                        still_path   : d.still_path   || null,
                        imdb_url     : 'https://www.imdb.com/title/' + d.tconst + '/'
                    });
                }
            });
            return episodes;
        """)


    # ── Requests ──────────────────────────────────────────────────────────────

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        for page_num in range(1, self.total_pages + 1):
            yield scrapy.Request(
                f"https://seriesgraph.com/all-shows/{page_num}",
                callback=self.parse_show_list,
            )

    # ── seriesgraph parsers ───────────────────────────────────────────────────

    def parse_show_list(self, response):
        for href in response.css('a[href*="/show/"]::attr(href)').getall():
            url = response.urljoin(href)
            if url not in self._seen_show_links:
                self._seen_show_links.add(url)
                yield scrapy.Request(url, callback=self.parse_show)


    def parse_show(self, response):
        rendered = self.make_selenium_response(response.url)
        if rendered:
            response = rendered

        item          = TvshowCrawlerItem()
        item["link"]  = response.url

        # show name
        showname = response.css("h1::text, h3::text").get()
        if showname:
            item["showname"] = showname.strip()

        # overall rating
        rating_text = response.css(
            "strong::text, .ShowRating__value::text, .rating-value::text"
        ).get()
        if rating_text:
            m = re.search(r"([\d.]+)", rating_text.strip())
            if m:
                item["rating"] = float(m.group(1))

        # poster
        poster_url = None
        if showname:
            poster_url = response.xpath(
                "//img[@alt=$name]/@src", name=showname.strip()
            ).get()
        poster_url = poster_url or response.css(
            'meta[property="og:image"]::attr(content)'
        ).get()
        if poster_url:
            if "_next/image" in poster_url:
                parsed = urlparse(poster_url)
                q = parse_qs(parsed.query).get("url")
                if q:
                    poster_url = unquote(q[0])
            item["poster"] = response.urljoin(poster_url)

        # episodes from D3 __data__
        episodes = []
        try:
            episodes = self.extract_episode_data_from_d3()
        except Exception as exc:
            self.logger.warning(f"D3 extraction failed for {response.url}: {exc}")

        self.logger.info(
            f"Show: {showname or response.url} — {len(episodes)} episodes"
        )

        if not episodes:
            yield item
            return

        item["seasons"]       = max(ep["season"] for ep in episodes)
        item["episodes"]      = len(episodes)
        item["episode_names"] = [ep["name"] for ep in episodes if ep.get("name")]

        # Build the imdb_episodes list with all D3 data
        # No need for separate IMDB scraping - D3 data is already rich
        item["imdb_episodes"] = [
            {
                "imdb_url"      : ep["imdb_url"],
                "title"         : ep["name"],
                "season_number" : ep["season"],
                "episode_number": ep["episode"],
                "episode_rating": ep["vote_average"],
                "num_votes"     : ep["num_votes"],
                "air_date"      : ep["air_date"],
                "genres"        : None,  # D3 doesn't provide genres
                "description"   : ep.get("overview"),  # Use overview from D3
                "runtime"       : ep["runtime"],
                "still_path"    : ep["still_path"],
            }
            for ep in episodes
        ]

        yield item

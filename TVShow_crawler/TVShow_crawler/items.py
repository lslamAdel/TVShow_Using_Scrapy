import scrapy


class TvshowCrawlerItem(scrapy.Item):
    showname = scrapy.Field()
    link = scrapy.Field()
    rating = scrapy.Field()
    poster = scrapy.Field()


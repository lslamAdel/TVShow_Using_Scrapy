# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class TvshowCrawlerPipeline:
    def process_item(self, item, spider):

        adapter = ItemAdapter(item)

        if adapter.get('name'):
            adapter['name'] = " ".join(adapter['name'].split())
            
        if adapter.get('link') and not adapter['link'].startswith('http'):
            adapter['link'] = spider.starts_urls[0] + adapter['link']
        
        if adapter.get('plot'):
            adapter['plot'] = " ".join(adapter['plot'].split())
            
        if adapter.get('rating'):
            adapter['rating'] = " ".join(adapter['rating'].split())
            

        return item

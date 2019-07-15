from .base import WebCrawlerBase
from importlib import import_module

import scrapy
from invana_bot.utils.url import get_domain, get_absolute_url
from invana_bot.utils.spiders import get_crawler_from_list
from urllib.parse import urlparse
from invana_bot.traversals.generic import GenericLinkExtractor

TRAVERSAL_LINK_FROM_FIELD = "link_from_field"
TRAVERSAL_SAME_DOMAIN_FIELD = "same_domain"


class InvanaBotSingleWebCrawler(WebCrawlerBase):
    """
    This is generic spider
    """
    name = "InvanaBotSingleWebCrawler"

    def closed(self, reason):
        print("spider closed with payload:", reason, self.current_crawler.get('cti_id'))

    @staticmethod
    def run_extractor(response=None, extractor=None):
        extractor_type = extractor.get("extractor_type")
        extractor_id = extractor.get("extractor_id")

        driver_klass_module = import_module(f'invana_bot.extractors')
        driver_klass = getattr(driver_klass_module, extractor_type)

        if extractor_type is None:
            return {}

        else:
            extractor_object = driver_klass(response=response,
                                            extractor=extractor,
                                            extractor_id=extractor_id)

        data = extractor_object.run()
        return data

    @staticmethod
    def run_traversal(response=None, traversal=None, **kwargs):

        selector_type = traversal.get("selector_type")
        kwargs = {}
        if selector_type == "css":
            kwargs['restrict_css'] = (traversal.get("selector_value"),)
        elif selector_type == "xpath":
            kwargs['restrict_xpaths'] = (traversal.get("selector_value"),)
        elif selector_type == "css":
            kwargs['restrict_regex'] = (traversal.get("selector_value"),)

        kwargs['allow_domains'] = traversal.get("allow_domains", [])
        print("kwargssss", kwargs)

        return GenericLinkExtractor(**kwargs).extract_links(response=response)

    @staticmethod
    def get_subdocument_key(crawler=None, extractor_id=None):
        """
        element is the subdocument key name.

        :param crawler:
        :param extractor_id:
        :param selector_id:
        :return:
        """
        for extractor in crawler['extractors']:
            if extractor.get("extractor_id") == extractor_id:
                for selector in extractor.get('data_selectors', []):
                    if selector.get('selector_attribute') == 'element':
                        return selector.get("selector_id")
        return

    def post_parse(self, response=None):
        pass

    def parse_error(self, failure):
        pass

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=self.parse_error,
                dont_filter=True,
                meta={
                    "current_request_traversal_page_count": 0,
                    "current_crawler": self.current_crawler,
                    "spiders": self.spiders
                }
            )

    @staticmethod
    def is_this_request_from_same_traversal(response, traversal):
        """
        This mean the current request came from this  traversal,
        so we can put max pages condition on this, otherwise for different
        traversals of different spiders, adding max_page doest make sense.
        """
        traversal_id = traversal['traversal_id']
        current_request_traversal_id = response.meta.get('current_request_traversal_id', None)
        return current_request_traversal_id == traversal_id

    def parse(self, response=None):

        self.logger.info("======Parsing the url: {}".format(response.url))

        current_crawler = response.meta.get("current_crawler")
        spiders = response.meta.get("spiders")
        context = self.context

        if None in [spiders, current_crawler]:
            current_crawler = self.current_crawler
            spiders = self.spiders

        data = {}
        # TODO - check if there is a reasnos , otherwise it will end up
        for extractor in current_crawler['extractors']:
            extracted_data = self.run_extractor(response=response, extractor=extractor)
            data.update(extracted_data)

        if context is not None:
            data.update({"context": context})
        data['url'] = response.url
        data['domain'] = get_domain(response.url)
        data['context']['spider_id'] = current_crawler['spider_id']

        """
        if crawler_traversal_id is None, it means this response originated from the 
        request raised by the start urls. 

        If it is Not None, the request/response is raised some traversal strategy.
        """
        current_request_traversal_id = response.meta.get('current_request_traversal_id', None)
        current_request_traversal_page_count = response.meta.get('current_request_traversal_page_count', 0)

        """
        Note on current_request_spider_id:
        This can never be none, including the ones that are started by start_urls .
        """
        current_spider_id = current_crawler.get("spider_id")
        crawler_traversals = current_crawler.get('traversals', [])
        for traversal in crawler_traversals:
            next_spider_id = traversal['next_spider_id']
            next_crawler = get_crawler_from_list(spider_id=next_spider_id, spiders=spiders)

            traversal['allow_domains'] = next_crawler.get("allowed_domains", [])
            traversal_id = traversal['traversal_id']
            traversal_max_pages = traversal.get('max_pages', 1)

            traversal_links = []
            is_this_request_from_same_traversal = self.is_this_request_from_same_traversal(response, traversal)
            print("is_this_request_from_same_traversal", is_this_request_from_same_traversal)
            print("current_request_traversal_page_count", current_request_traversal_page_count)
            print("traversal_max_pages", traversal_max_pages)
            print(" current_request_traversal_page_count < traversal_max_pages",
                  current_request_traversal_page_count < traversal_max_pages)
            shall_traverse = False

            if current_request_traversal_id is None:
                """
                start urls will not have this traversal_id set, so we should allow then to traverse
                """
                shall_traverse = True

            elif is_this_request_from_same_traversal and current_request_traversal_page_count < traversal_max_pages:
                """
                This block will be valid for the traversals from same spider_id, ie., pagination of a crawler 
                """

                shall_traverse = True

            elif is_this_request_from_same_traversal:
                """
                """
                shall_traverse = True

            elif is_this_request_from_same_traversal is False and current_request_traversal_page_count < traversal_max_pages:
                """
                This for the crawler_a traversing to crawler_b, this is not pagination, but trsversing between 
                spiders.
                """
                shall_traverse = True
            print("shall_traverse: {}".format(traversal_id), shall_traverse)
            if shall_traverse:
                traversal_links = self.run_traversal(response=response, traversal=traversal)
                data[traversal_id] = {"traversal_urls": traversal_links}
                """
                Then validate for max_pages logic if traversal_id's traversal has any!.
                This is where the further traversal for this traversal_id  is decided 
                """
                max_pages = traversal.get("max_pages", 1)

                for link in traversal_links:

                    """
                    we are already incrementing, the last number, so using <= might make it 6 pages when 
                    max_pages is 5 
                    """
                    if current_request_traversal_page_count < max_pages:
                        print("=======current_request_traversal_page_count", current_request_traversal_page_count)
                        print("link", link)
                        print("-----------------------------------")
                        yield scrapy.Request(
                            link,
                            callback=self.parse,
                            errback=self.parse_error,
                            meta={
                                "current_crawler": next_crawler,
                                "spiders": spiders,
                                "current_request_traversal_id": traversal_id,
                                "current_request_traversal_page_count": current_request_traversal_page_count,

                            }
                        )
                    current_request_traversal_page_count += 1

            print("=================================================")
            print("====traversal_links", traversal_id, len(traversal_links))
            print("=================================================")

        yield data

        self.post_parse(response=response)
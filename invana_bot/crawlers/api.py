from .base import WebCrawlerBase
from invana_bot.utils.url import get_domain, get_absolute_url
from scrapy.utils.spider import iterate_spider_output
from invana_bot.utils.crawlers import get_crawler_from_list
import scrapy
import json


class GenericAPISpider(WebCrawlerBase):
    """

    start_urls: ["https://news.ycombinator.com/rss"]
    allowed_domains: ["news.ycombinator.com"]
    extra_url_param: token=xyz
    pagination_param: page



    NOTE: paginating parameter

    wordpress: ?paged=n
    blogger: ?start-index=n
    """
    name = "GenericAPISpider"
    extra_url_param = None
    pagination_param = None
    result_key = "result"

    def parse_error(self, failure):
        """
        https://stackoverflow.com/questions/31146046/how-do-i-catch-errors-with-scrapy-so-i-can-do-something-when-i-get-user-timeout
        :return:
        """
        pass

    def post_parse(self, response=None):
        pass

    @staticmethod
    def is_this_request_from_same_traversal(response, traversal):
        """
        This mean the current request came from this  traversal,
        so we can put max pages condition on this, otherwise for different
        traversals of different crawlers, adding max_page doest make sense.
        """
        traversal_id = traversal['traversal_id']
        current_request_traversal_id = response.meta.get('current_request_traversal_id', None)
        return current_request_traversal_id == traversal_id

    def parse(self, response):
        """This method is called for the nodes matching the provided tag name
        (itertag). Receives the response and an Selector for each node.
        Overriding this method is mandatory. Otherwise, you spider won't work.
        This method must return either a BaseItem, a Request, or a list
        containing any of them.
        """
        current_crawler = response.meta.get("current_crawler")
        crawlers = response.meta.get("crawlers")
        context = self.context or {}
        if None in [current_crawler]:
            current_crawler = self.current_crawler
            crawlers = self.crawlers

        try:
            jsonresponse = json.loads(response.body_as_unicode())
        except Exception as e:
            print(e)
            jsonresponse = {}

        if self.result_key is None:
            result_data = jsonresponse
        else:
            result_data = jsonresponse.get(self.result_key)

        data = {"url": response.url, "domain": get_domain(response.url), "data": result_data}

        context["crawler_id"] = current_crawler.get("crawler_id")
        data['context'] = context

        """
        if crawler_traversal_id is None, it means this response originated from the 
        request raised by the start urls. 

        If it is Not None, the request/response is raised some traversal strategy.
        """
        current_request_traversal_id = response.meta.get('current_request_traversal_id', None)
        """
        In xml crawling current_request_traversal_page_count starts from 1, because there is no page 0.
        """
        current_request_traversal_page_count = response.meta.get('current_request_traversal_page_count', 1)

        """
        Note on current_request_crawler_id:
        This can never be none, including the ones that are started by start_urls .
        """
        current_crawler_id = current_crawler.get("crawler_id")

        crawler_traversals = current_crawler.get('traversals', [])
        for traversal in crawler_traversals:
            next_crawler_id = traversal['next_crawler_id']
            iter_param = traversal['iter_param']

            next_crawler = get_crawler_from_list(crawler_id=next_crawler_id, crawlers=crawlers)

            traversal['allow_domains'] = next_crawler.get("allowed_domains", [])
            traversal_id = traversal['traversal_id']
            traversal_max_pages = traversal.get('max_pages', 1)

            traversal_links = []
            is_this_request_from_same_traversal = self.is_this_request_from_same_traversal(response, traversal)
            print("is_this_request_from_same_traversal", is_this_request_from_same_traversal)
            print("current_request_traversal_page_count", current_request_traversal_page_count)
            print("traversal_max_pages", traversal_max_pages)
            print(" current_request_traversal_page_count <= traversal_max_pages",
                  current_request_traversal_page_count <= traversal_max_pages)
            shall_traverse = False

            if current_request_traversal_id is None:
                """
                start urls will not have this traversal_id set, so we should allow then to traverse
                """
                shall_traverse = True

            elif is_this_request_from_same_traversal and current_request_traversal_page_count <= traversal_max_pages:
                """
                This block will be valid for the traversals from same crawler_id, ie., pagination of a crawler 
                """

                shall_traverse = True

            elif is_this_request_from_same_traversal:
                """
                """
                shall_traverse = True

            elif is_this_request_from_same_traversal is False and current_request_traversal_page_count <= \
                    traversal_max_pages:
                """
                This for the crawler_a traversing to crawler_b, this is not pagination, but trsversing between 
                crawlers.
                """
                shall_traverse = True
            print("shall_traverse: {}".format(traversal_id), shall_traverse)
            if shall_traverse:
                current_url = response.url
                clean_url_without_iter_param = current_url.split("?")[0] if "?" in current_url else current_url
                # this is already iterating, so ignore.
                print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", clean_url_without_iter_param)
                print("clean_url_without_iter_param", clean_url_without_iter_param)
                traversal_link = "{}?{}={}".format(clean_url_without_iter_param, iter_param,
                                                   current_request_traversal_page_count + 1)

                print("traversal_link", traversal_link)

                data[traversal_id] = {"traversal_urls": [traversal_link]}
                """
                Then validate for max_pages logic if traversal_id's traversal has any!.
                This is where the further traversal for this traversal_id  is decided 
                """
                max_pages = traversal.get("max_pages", 1)

                current_request_traversal_page_count += 1

                """
                we are already incrementing, the last number, so using <= might make it 6 pages when 
                max_pages is 5 
                """
                if current_request_traversal_page_count <= max_pages:
                    print("=======current_request_traversal_page_count", current_request_traversal_page_count)
                    print("-----------------------------------")
                    yield scrapy.Request(
                        traversal_link,
                        callback=self.parse,
                        errback=self.parse_error,
                        meta={
                            "current_crawler": next_crawler,
                            "crawlers": crawlers,
                            "current_request_traversal_id": traversal_id,
                            "current_request_traversal_page_count": current_request_traversal_page_count,

                        }
                    )

            print("=================================================")
            print("====traversal_links", traversal_id, len(traversal_links), traversal_links)
            print("=================================================")

        yield data

        self.post_parse(response=response)

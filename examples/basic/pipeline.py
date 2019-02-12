from invana_bot import InvanaWebCrawler

extractor = {
    "data_selectors": [
        {
            "id": "items",
            "selector": ".post-listing .post-item",
            "selector_attribute": "element",
            "multiple": True
        },
        {
            "id": "url",
            "selector": ".post-header h2 a",
            "selector_type": "css",
            "selector_attribute": "href",
            "parent_selector": "items",
            "multiple": False
        },
        {
            "id": "title",
            "selector": ".post-header h2 a",
            "selector_type": "css",
            "selector_attribute": "text",
            "parent_selector": "items",
            "multiple": False
        },
        {
            "id": "content",
            "selector": ".post-content",
            "selector_type": "css",
            "selector_attribute": "html",
            "parent_selector": "items",
            "multiple": False
        }
    ],
}
traversal = {
    "selector": ".next-posts-link",
    "selector_type": "css",
    "max_pages": 2

}
pipeline_data = {
    "pipeline_id": "search_pipeline",
    "pipeline": [
        {  # single pipe
            "pipe_id": "blog-list",
            "start_urls": ["https://blog.scrapinghub.com"],
            "data_extractors": [
                # {"default": "Invana::SearchEngineExtractor"},  # invana is namespace or the developer username
                extractor,  # invana is namespace or the developer username
            ],  # this will be converted into data_selectors when used by API.
            "traversals": [{
                "traversal_type": "pagination",
                "pagination": traversal,
                "next_pipe_id": "blog-list"
            }]
        }
    ],
    "context": {
        "client_id": "abc",
        "job_id": "123"
    }
}

if __name__ == '__main__':
    crawler = InvanaWebCrawler(
        cache_database_uri="mongodb://127.0.0.1",
        storage_database_uri="mongodb://127.0.0.1",
        cache_database="mongodb",
        storage_database="mongodb",
    )

    all_jobs = crawler.set_pipeline(
        pipeline=pipeline_data
    )
    crawler.start_jobs(jobs=all_jobs)
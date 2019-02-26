from invana_bot import InvanaWebCrawler

pipeline_data = {
    "pipeline_id": "generic_crawling_pipeline",
    "start_urls": ["https://www.migrocer.com"],
    "pipeline": [
        {  # single pipe
            "pipe_id": "blog-list",
            "data_extractors": [{
                "extractor_name": "CustomContentExtractor",
                "data_selectors": [
                    {
                        "id": "main_content",
                        "selector": "body",
                        "selector_type": "css",
                        "selector_attribute": "html",
                        "multiple": False
                    }
                ]
            }
            ],
            "traversals": [{
                "traversal_type": "same_domain",
                "next_pipe_id": "blog-list"
            }]
        }
    ],
}
context = {
    "extra_info": "2019-1-1 something",
    "author": "Ravi@Invana",

}

if __name__ == '__main__':
    crawler = InvanaWebCrawler(
        cache_database_uri="mongodb://127.0.0.1",
        storage_database_uri="mongodb://127.0.0.1",
        cache_database="mongodb",
        storage_database="mongodb",
    )

    all_jobs = crawler.create_jobs(
        pipeline=pipeline_data,
        context=context
    )
    crawler.start_jobs(jobs=all_jobs)
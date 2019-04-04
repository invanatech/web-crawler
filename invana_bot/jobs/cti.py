from .base import CTIJobGeneratorBase
from invana_bot.runners.cti import CTIFlowRunner
from datetime import datetime


class CTIJobGenerator(CTIJobGeneratorBase):
    """
        Invana-bot cti job generator
    """

    def create_job(self, cti_manifest=None, context=None, spider_cls=None):
        if context is None:
            context = {}
        if 'job_id' not in context.keys():
            context['job_id'] = self.job_id
            context['job_started'] = datetime.now()

        settings_from_manifest = cti_manifest.get("settings", {})
        actual_settings = self.settings
        actual_settings['DOWNLOAD_DELAY'] = settings_from_manifest.get("download_delay", 0)
        cti_runner = CTIFlowRunner(cti_manifest=cti_manifest,
                                   settings=actual_settings,
                                   job_id=self.job_id,
                                   context=context,
                                   spider_cls=spider_cls
                                   )
        job, errors = cti_runner.crawl()
        return {"crawler_job": job, "crawler_job_errors": errors, "runner": cti_runner}
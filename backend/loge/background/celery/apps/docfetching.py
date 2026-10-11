from onyx.background.celery.apps import app_base
from onyx.background.celery.apps.docfetching import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "loge.background.celery.tasks.log_export",
        ]
    )
)

from onyx.background.celery.apps import app_base
from onyx.background.celery.apps.heavy import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "loge.background.celery.tasks.doc_permission_syncing",
            "loge.background.celery.tasks.external_group_syncing",
            "loge.background.celery.tasks.cleanup",
            "loge.background.celery.tasks.query_history",
            "loge.background.celery.tasks.log_export",
        ]
    )
)

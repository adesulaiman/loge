from onyx.background.celery.apps import app_base
from onyx.background.celery.apps.light import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "loge.background.celery.tasks.doc_permission_syncing",
            "loge.background.celery.tasks.external_group_syncing",
            "loge.background.celery.tasks.ttl_management",
            "loge.background.celery.tasks.log_export",
        ]
    )
)

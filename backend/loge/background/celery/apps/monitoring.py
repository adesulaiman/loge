from onyx.background.celery.apps import app_base
from onyx.background.celery.apps.monitoring import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "loge.background.celery.tasks.tenant_provisioning",
            "loge.background.celery.tasks.log_export",
        ]
    )
)

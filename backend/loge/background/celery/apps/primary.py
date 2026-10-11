from onyx.background.celery.apps import app_base
from onyx.background.celery.apps.primary import celery_app

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "loge.background.celery.tasks.hooks",
            "loge.background.celery.tasks.doc_permission_syncing",
            "loge.background.celery.tasks.external_group_syncing",
            "loge.background.celery.tasks.cloud",
            "loge.background.celery.tasks.ttl_management",
            "loge.background.celery.tasks.usage_reporting",
            "loge.background.celery.tasks.license_notifications",
            "loge.background.celery.tasks.license_reclaim",
            "loge.background.celery.tasks.log_export",
            "loge.background.celery.tasks.sso_domain_revalidation",
        ]
    )
)

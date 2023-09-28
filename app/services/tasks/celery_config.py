from app.core.config import app

broker_url = app.celery_broker_url.unicode_string()
backend_url = app.celery_result_backend.unicode_string()
worker_send_task_event = False
task_ignore_result = True
# task will be killed after 60 seconds
task_time_limit = 60
# task will raise exception SoftTimeLimitExceeded after 50 seconds
task_soft_time_limit = 50
# task messages will be acknowledged after the task has been executed, not just before (the default behavior).
task_acks_late = True
# One worker taks 10 tasks from queue at a time and will increase the performance
worker_prefetch_multiplier = 10

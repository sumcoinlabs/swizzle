from celery import shared_task
from .services import run_newsroom

@shared_task(name="newsroom.tasks.poll_and_generate", ignore_result=True)
def poll_and_generate():
    return run_newsroom()

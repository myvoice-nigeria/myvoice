from celery.task import task


@task
def sample_task():
    print 'running sample task'

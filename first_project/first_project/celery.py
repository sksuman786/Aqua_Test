import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'first_project.settings')

app = Celery('first_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'auto-block-expired-recharges-every-hour': {
        'task': 'water_rental.tasks.auto_block_expired_recharges',
        'schedule': crontab(minute=0),  # Run every hour at minute 0
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    
# ------ esp -----
from celery.schedules import crontab

app.conf.beat_schedule.update({
'ping-all-devices-every-5-minutes': {
'task': 'water_rental.tasks.ping_all_devices', 'schedule': crontab(minute='*/5'), # every 5 minutes
},
})
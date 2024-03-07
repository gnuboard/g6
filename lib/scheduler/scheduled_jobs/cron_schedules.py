from lib.common import delete_old_records


cron_jobs = [
    {
        'job_id': 'cron_0',
        'job_func': delete_old_records,
        'expression': {'hour': 5, 'minute': 30, 'second': 0}
    },
]



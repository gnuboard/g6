import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from .scheduled_jobs import cron_jobs, interval_jobs, date_jobs

from core.settings import settings

class Scheduler:
    """
    예약 작업을 관리할 스케줄러 생성
    https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html

    lib/scheduler/scheduled_jobs의 
    cron_schedules.py, interval_schedules.py, date_schedules.py에 작업을 등록합니다.
    - cron_schedules.py: 매일 특정 시간에 반복할 작업을 등록합니다.
    - interval_schedules.py: 일정 간격으로 반복할 작업을 등록합니다.
    - date_schedules.py: 특정 날짜와 시간에 한 번만 실행할 작업을 등록합니다.
    """
    FLAG_DELETE_TIME = 10   # 단위: 초
    flag_file_path = "data/flag.txt"
    job_ids = set()
    total_trigger_jobs = {
        "cron": cron_jobs,
        "interval": interval_jobs,
        "date": date_jobs,
    }

    def __init__(self) -> None:
        """
        스케줄러를 생성하고 시작합니다.
        기본적으로 BackgroundScheduler를 사용합니다.
        """
        self.background_scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        self.background_scheduler.start()

    def add_jobs(self, trigger_type: str) -> None:
        """
        트리거별 작업을 스케줄러에 등록합니다.
        """
        trigger_jobs = self.total_trigger_jobs[trigger_type]
        for job_info in trigger_jobs:
            job_id, job_func, expression = job_info.values()
            self.background_scheduler.add_job(trigger=trigger_type, func=job_func, **expression)
            self.job_ids.add(job_id)

    def add_all_jobs(self) -> None:
        """
        모든 트리거들의 작업을 스케줄러에 모두 등록합니다.
        """
        for trigger_type in self.total_trigger_jobs.keys():
            self.add_jobs(trigger_type=trigger_type)

    @classmethod
    def is_flag_exist(cls) -> bool:
        """
        스케줄러 등록 확인용 파일의 유뮤를 확인합니다.
        """
        return os.path.exists(cls.flag_file_path)
    
    @classmethod
    def is_flag_valid(cls) -> bool:
        """
        파일 생성 시간과 삭제 예정 시간을 비교하여 스케줄러 등록 확인용 파일이 유효한지 확인합니다.
        - 삭제 예정 시간: Scheduler.FLAG_DELETE_TIME (단위: second)
        - 삭제 예정 시간을 초과한 경우 False를 반환합니다.
        """
        file_creation_time = os.path.getmtime(cls.flag_file_path)
        current_time = time.time()
        if current_time - file_creation_time > cls.FLAG_DELETE_TIME:
            return False
        return True

    @classmethod
    def create_flag(cls) -> None:
        """
        스케줄러 등록 확인용 파일을 생성합니다.
        """
        with open(cls.flag_file_path, "w") as f:
            f.write("Scheduler task has been registered.")

    @classmethod
    def remove_flag(cls) -> None:
        """
        스케줄러 등록 확인용 파일을 삭제합니다.
        """
        if os.path.exists(cls.flag_file_path):
            os.remove(cls.flag_file_path)

    def run_scheduler(self) -> None:
        """
        스케줄러를 실행합니다.
        - --workers 옵션으로 여러 프로세스 실행시 
          예약 작업이 중복 등록되는 것을 방지하기 위해 flag를 이용합니다.
        - flag 파일 생성 여부와 파일의 유효성을 확인하여 스케줄 작업 등록 여부를 결정합니다.
        """
        time.sleep(0.1)
        if self.is_flag_exist() and self.is_flag_valid():
            return

        run_date = datetime.now() + timedelta(seconds=self.FLAG_DELETE_TIME)
        self.add_all_jobs()
        self.background_scheduler.add_job(
            trigger="date", func=self.remove_flag, run_date=run_date
        )
        self.create_flag()
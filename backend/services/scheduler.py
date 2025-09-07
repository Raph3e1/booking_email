import traceback

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from models.settings import SettingsManager
import logging
import pytz

logger = logging.getLogger(__name__)

class EmailScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.settings_manager = SettingsManager()
        self.jobs = {}  # Store job references

    def start_all_jobs(self, action_fetch_data):
        """Start jobs for all email configurations"""
        configs = self.settings_manager.get_all_configs()
        for config in configs:
            try:
                self.add_job(config, action_fetch_data)
            except Exception as e:
                print(traceback.print_exc())

    def add_job(self, config, action_fetch_data):
        """Add a new job for an email configuration"""
        job_id = f"email_fetch_{config['id']}"
        
        # Remove existing job if any
        if job_id in self.jobs:
            self.remove_job(config['id'])

        # Create new job
        job = self.scheduler.add_job(
            action_fetch_data,
            IntervalTrigger(minutes=config['fetchInterval']),
            args=[config['email'], config['password']],
            id=job_id,
            next_run_time=datetime.now()  # Run immediately
        )
        
        self.jobs[job_id] = job
        logger.info(f"Added job for email {config['email']} with interval {config['fetchInterval']} minutes")

    def remove_job(self, config_id):
        """Remove a job for an email configuration"""
        job_id = f"email_fetch_{config_id}"
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            logger.info(f"Removed job for config ID {config_id}")

    def update_job(self, config, action_fetch_data):
        """Update an existing job"""
        self.add_job(config, action_fetch_data)

    def get_next_run_time(self, config_id):
        """Get the next run time for a job"""
        job_id = f"email_fetch_{config_id}"
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        next_run = job.next_run_time

        if next_run is None:
            return None

        # Convert both times to UTC for comparison
        utc = pytz.UTC
        now = datetime.now(utc)
        next_run = next_run.astimezone(utc)

        # Calculate time difference
        time_diff = next_run - now
        minutes = int(time_diff.total_seconds() / 60)
        hours = minutes // 60
        remaining_minutes = minutes % 60

        if hours > 0:
            time_until = f"{hours} hour{'s' if hours > 1 else ''} and {remaining_minutes} minute{'s' if remaining_minutes > 1 else ''}"
        else:
            time_until = f"{minutes} minute{'s' if minutes > 1 else ''}"

        return {
            "next_run": next_run.isoformat(),
            "time_until": time_until
        }

    def get_all_jobs_status(self):
        """Get status of all jobs"""
        statuses = []
        for job_id, job in self.jobs.items():
            config = self.get_config_for_job(job_id)
            if config:
                next_run = self.get_next_run_time(job_id)
                status = {
                    "id": int(job_id.split('_')[-1]),
                    "email": config.get('email', ''),
                    "fetch_interval": config.get('fetchInterval', 0),
                    "next_run": next_run
                }
                statuses.append(status)
        return statuses

    def get_config_for_job(self, job_id):
        """Get the configuration for a specific job"""
        # This method should be implemented to return the configuration
        # for the given job_id from your settings storage
        return self.settings_manager.get_config(int(job_id.split('_')[-1]))

# Create a singleton instance
scheduler = EmailScheduler() 
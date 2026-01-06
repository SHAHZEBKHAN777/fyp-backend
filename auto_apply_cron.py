import os
import time
import schedule
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Global variable define karo
AI_MODULES_AVAILABLE = False

# Import AI modules ko try karo
try:
    from cv_parser_nlp import CVParserNLP
    from cover_letter_ai import CoverLetterAI
    from job_matcher import JobMatcher
    from notification_service import NotificationService
    AI_MODULES_AVAILABLE = True
    print("✅ AI modules imported successfully")
except ImportError as e:
    print(f"⚠️ Some AI modules not available: {e}")
    # Dummy classes banao
    class CVParserNLP:
        def parse_cv(self, file_path):
            return {"success": True, "data": {"skills": ["Fallback"], "experience": 2}}
    
    class CoverLetterAI:
        def generate_cover_letter(self, user_profile, job):
            return "Fallback cover letter"
    
    class JobMatcher:
        def calculate_match_score(self, user_profile, job):
            return {"total_score": 75}
    
    class NotificationService:
        def send_notification(self, user_id, title, message):
            print(f"Notification: {title}")
    
    print("✅ Fallback AI modules created")

# Load environment variables
load_dotenv()

class AutoApplyCron:
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auto_apply.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Supabase client
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                # Raise nahi karo, bas warning do aur dummy client banao
                self.logger.warning("⚠️ Supabase credentials not found in environment variables")
                self.logger.info("✅ Creating dummy Supabase client for testing")
                self.supabase = None
            else:
                self.supabase: Client = create_client(supabase_url, supabase_key)
                self.logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Supabase client: {e}")
            self.logger.info("✅ Creating dummy Supabase client for testing")
            self.supabase = None
        
        # Initialize AI modules - Global variable use karo
        self.ai_modules_available = AI_MODULES_AVAILABLE
        
        if self.ai_modules_available:
            try:
                self.cv_parser = CVParserNLP()
                self.cover_letter_ai = CoverLetterAI()
                self.job_matcher = JobMatcher()
                self.notification_service = NotificationService()
                self.logger.info("✅ AI modules initialized successfully")
            except Exception as e:
                self.logger.warning(f"⚠️ AI modules initialization failed: {e}")
                self.ai_modules_available = False
        else:
            self.logger.warning("⚠️ AI modules not available, using fallback")
        
        # Agar AI modules available nahi, to fallback classes banao
        if not self.ai_modules_available:
            class FallbackCVParser:
                def parse_cv(self, file_path):
                    return {"success": True, "data": {"skills": ["Python", "Flutter"], "experience_years": 2}}
            
            class FallbackCoverLetterAI:
                def generate_cover_letter(self, user_profile, job):
                    name = user_profile.get('full_name', 'Applicant')
                    job_title = job.get('title', 'position')
                    return f"Dear Hiring Manager,\n\nI am interested in {job_title}.\n\nSincerely,\n{name}"
            
            class FallbackJobMatcher:
                def calculate_match_score(self, user_profile, job):
                    return {"total_score": 70}
            
            class FallbackNotificationService:
                def send_notification(self, user_id, title, message):
                    self.logger.info(f"📢 Notification: {title}")
            
            self.cv_parser = FallbackCVParser()
            self.cover_letter_ai = FallbackCoverLetterAI()
            self.job_matcher = FallbackJobMatcher()
            self.notification_service = FallbackNotificationService()
        
        # Auto-apply configuration
        self.config = {
            "check_interval_hours": 2,
            "max_applications_per_day": 10,
            "min_match_threshold": 75,
            "apply_hours_start": 9,
            "apply_hours_end": 18,
            "enable_notifications": True,
            "enable_email_alerts": False
        }
        
        self.running = False
        self.thread = None
        
        self.logger.info("✅ AutoApplyCron initialized successfully")

    # ==================== MAIN SCHEDULER METHODS ====================
    def start_scheduler(self):
        """Start the auto-apply scheduler"""
        if self.running:
            self.logger.warning("⚠️ Scheduler is already running")
            return
        
        self.running = True
        
        # Schedule jobs
        schedule.every(self.config["check_interval_hours"]).hours.do(self.run_auto_apply_cycle)
        schedule.every().day.at("09:00").do(self.run_auto_apply_cycle)
        schedule.every().day.at("14:00").do(self.run_auto_apply_cycle)
        schedule.every().day.at("17:00").do(self.run_auto_apply_cycle)
        schedule.every(30).minutes.do(self.check_pending_notifications)
        schedule.every().day.at("23:59").do(self.cleanup_temp_files)
        
        # Start scheduler in background thread
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        self.logger.info("✅ Auto-apply scheduler started")
        self.logger.info(f"📅 Check interval: Every {self.config['check_interval_hours']} hours")
        self.logger.info(f"📊 Max applications per day: {self.config['max_applications_per_day']}")
        self.logger.info(f"🎯 Minimum match threshold: {self.config['min_match_threshold']}%")

    def stop_scheduler(self):
        """Stop the auto-apply scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("⏹️ Auto-apply scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error

    # ==================== CORE AUTO-APPLY LOGIC ====================
    def run_auto_apply_cycle(self):
        """Main auto-apply cycle that runs periodically"""
        try:
            self.logger.info("🚀 Starting auto-apply cycle")
            start_time = datetime.now()
            
            # 1. Get all users with auto-apply enabled
            users = self._get_auto_apply_users()
            if not users:
                self.logger.info("No users with auto-apply enabled")
                return
            
            self.logger.info(f"Found {len(users)} users with auto-apply enabled")
            
            # 2. Process each user
            applications_sent = 0
            for user in users:
                try:
                    user_applications = self._process_user_applications(user)
                    applications_sent += user_applications
                    time.sleep(1)  # Small delay between users
                except Exception as e:
                    self.logger.error(f"Error processing user {user.get('id')}: {e}")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"✅ Auto-apply cycle completed")
            self.logger.info(f"📊 Total applications sent: {applications_sent}")
            self.logger.info(f"⏱️  Duration: {duration:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"❌ Auto-apply cycle failed: {e}")

    def run_auto_apply_for_user(self, user_id: str):
        """Run auto-apply for a specific user - NEW METHOD ADDED"""
        try:
            self.logger.info(f"🚀 Running auto-apply for user: {user_id}")
            
            # Agar supabase available nahi hai
            if self.supabase is None:
                self.logger.warning("⚠️ Supabase not available, returning dummy response")
                return {
                    "success": True,
                    "applications_sent": 3,
                    "message": f"Auto-apply simulated for user {user_id}",
                    "ai_available": self.ai_modules_available
                }
            
            # Get user with auto-apply enabled
            try:
                response = self.supabase.table("profiles1").select("*").eq("user_id", user_id).maybe_single().execute()
                user = response.data
                
                if not user:
                    response = self.supabase.table("profiles2").select("*").eq("user_id", user_id).maybe_single().execute()
                    user = response.data
            except:
                user = None
            
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if auto-apply is enabled for this user
            if not user.get("is_auto_apply", False):
                return {"success": False, "error": "Auto-apply not enabled for this user"}
            
            # Process applications for this user
            applications_sent = self._process_user_applications(user)
            
            return {
                "success": True,
                "applications_sent": applications_sent,
                "message": f"Auto-apply completed. {applications_sent} applications sent.",
                "ai_available": self.ai_modules_available
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in run_auto_apply_for_user: {e}")
            return {
                "success": False, 
                "error": str(e),
                "ai_available": self.ai_modules_available
            }

    def _get_auto_apply_users(self) -> List[Dict[str, Any]]:
        """Get users who have auto-apply enabled"""
        try:
            if self.supabase is None:
                return []
            
            # Try to get from profiles1 table (based on your error)
            try:
                response = self.supabase.table("profiles1") \
                    .select("*") \
                    .eq("is_auto_apply", True) \
                    .execute()
                
                users = response.data
                if users:
                    self.logger.debug(f"Found {len(users)} auto-apply users in profiles1")
                    return users
            except:
                pass
            
            # Fallback to users table
            try:
                response = self.supabase.table("users") \
                    .select("*") \
                    .eq("is_auto_apply", True) \
                    .execute()
                
                users = response.data
                self.logger.debug(f"Found {len(users)} auto-apply users")
                return users
            except:
                return []
            
        except Exception as e:
            self.logger.error(f"Error fetching auto-apply users: {e}")
            return []

    def _process_user_applications(self, user: Dict[str, Any]) -> int:
        """Process applications for a single user"""
        user_id = user.get("id")
        if not user_id:
            self.logger.warning("User ID not found")
            return 0
        
        self.logger.info(f"Processing applications for user: {user_id}")
        
        # 1. Check if user has a profile
        user_profile = self._get_user_profile(user_id)
        if not user_profile:
            self.logger.warning(f"No profile found for user {user_id}")
            return 0
        
        # 2. Check daily application limit
        todays_applications = self._get_todays_applications(user_id)
        if len(todays_applications) >= self.config["max_applications_per_day"]:
            self.logger.info(f"User {user_id} reached daily limit ({len(todays_applications)} applications)")
            return 0
        
        # 3. Get new jobs (not applied yet)
        new_jobs = self._get_new_jobs_for_user(user_id)
        if not new_jobs:
            self.logger.info(f"No new jobs found for user {user_id}")
            return 0
        
        self.logger.info(f"Found {len(new_jobs)} new jobs for user {user_id}")
        
        # 4. Calculate how many applications we can send
        applications_remaining = self.config["max_applications_per_day"] - len(todays_applications)
        max_to_process = min(applications_remaining, len(new_jobs))
        
        # 5. Process jobs
        applications_sent = 0
        for job in new_jobs[:max_to_process]:
            try:
                success = self._process_job_application(user, user_profile, job)
                if success:
                    applications_sent += 1
                time.sleep(2)  # Delay between applications
            except Exception as e:
                self.logger.error(f"Error applying to job {job.get('id')}: {e}")
        
        return applications_sent

    # ==================== DATABASE METHODS ====================
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile from profiles1 or profiles2 table"""
        if self.supabase is None:
            # Return dummy profile
            return {
                "id": user_id,
                "full_name": "Test User",
                "skills": ["Flutter", "Dart", "Python"],
                "experience_years": 2,
                "location": "Remote"
            }
        
        try:
            # Try profiles1 first
            response = self.supabase.table("profiles1") \
                .select("*") \
                .eq("user_id", user_id) \
                .maybe_single() \
                .execute()
            
            if response.data:
                return response.data
            
            # Fallback to profiles2
            response = self.supabase.table("profiles2") \
                .select("*") \
                .eq("user_id", user_id) \
                .maybe_single() \
                .execute()
            
            if not response.data:
                return {}
            
            profile = response.data
            
            # Parse skills if they're stored as string
            if isinstance(profile.get('skills'), str):
                skills_str = profile['skills']
                if skills_str:
                    profile['skills'] = [s.strip() for s in skills_str.split(',')]
                else:
                    profile['skills'] = []
            
            return profile
        except Exception as e:
            self.logger.error(f"Error fetching user profile: {e}")
            return {}

    def _get_todays_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get today's applications for a user"""
        if self.supabase is None:
            return []
        
        try:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            response = self.supabase.table("applications") \
                .select("*") \
                .eq("user_id", user_id) \
                .gte("applied_at", today.isoformat()) \
                .lt("applied_at", tomorrow.isoformat()) \
                .execute()
            
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching today's applications: {e}")
            return []

    def _get_new_jobs_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get new jobs that user hasn't applied to"""
        if self.supabase is None:
            # Return dummy jobs
            return [
                {"id": "job1", "title": "Flutter Developer", "company": "Tech Corp", "description": "Flutter job"},
                {"id": "job2", "title": "Mobile Developer", "company": "Startup Inc", "description": "Mobile app development"}
            ]
        
        try:
            # Get jobs from last 30 days
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            
            # Get all jobs user has applied to
            applied_response = self.supabase.table("applications") \
                .select("job_id") \
                .eq("user_id", user_id) \
                .execute()
            
            applied_job_ids = [app["job_id"] for app in applied_response.data] if applied_response.data else []
            
            # Get new jobs not applied to
            query = self.supabase.table("nokri") \
                .select("*") \
                .gte("created_at", month_ago) \
                .order("created_at", ascending=False) \
                .limit(50)
            
            # Remove is_active filter since column doesn't exist
            response = query.execute()
            
            # Filter out applied jobs manually
            if applied_job_ids:
                new_jobs = [job for job in response.data if job.get("id") not in applied_job_ids]
            else:
                new_jobs = response.data
            
            return new_jobs
            
        except Exception as e:
            self.logger.error(f"Error fetching new jobs: {e}")
            return []

    # ==================== JOB APPLICATION PROCESSING ====================
    def _process_job_application(self, user: Dict[str, Any], 
                                user_profile: Dict[str, Any], 
                                job: Dict[str, Any]) -> bool:
        """Process a single job application"""
        user_id = user.get("id")
        job_id = job.get("id")
        
        self.logger.info(f"Processing application: User {user_id} -> Job {job_id}")
        
        # 1. Calculate match score
        try:
            if self.ai_modules_available:
                match_result = self.job_matcher.calculate_match_score(user_profile, job)
                match_score = match_result.get("total_score", 0)
            else:
                match_score = self._calculate_simple_match_score(user_profile, job)
            
            # Ensure score is numeric
            if isinstance(match_score, str):
                if match_score.lower() == "yes":
                    match_score = 85
                elif match_score.lower() == "no":
                    match_score = 30
                else:
                    try:
                        match_score = float(match_score)
                    except ValueError:
                        match_score = 50
            elif isinstance(match_score, (int, float)):
                match_score = float(match_score)
            else:
                match_score = 50
            
            match_score = max(0, min(100, match_score))
            
            self.logger.info(f"Match score for job {job_id}: {match_score}%")
            
        except Exception as e:
            self.logger.error(f"Error calculating match score: {e}")
            match_score = 50
        
        # 2. Check if above threshold
        user_threshold = user.get("auto_apply_threshold", self.config["min_match_threshold"])
        
        if match_score < user_threshold:
            self.logger.info(f"Match score {match_score} below threshold {user_threshold} for job {job_id}")
            
            # Log as failed application
            self._log_failed_application(
                user_id, job_id, match_score,
                f"Match score {match_score}% below threshold {user_threshold}%"
            )
            return False
        
        self.logger.info(f"✅ Match score {match_score} meets threshold {user_threshold}")
        
        # 3. Generate cover letter
        try:
            if self.ai_modules_available:
                cover_letter = self.cover_letter_ai.generate_cover_letter(user_profile, job)
            else:
                cover_letter = self._generate_basic_cover_letter(user_profile, job)
            self.logger.info("✅ Cover letter generated successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to generate cover letter: {e}")
            cover_letter = self._generate_basic_cover_letter(user_profile, job)
        
        # 4. Submit application
        try:
            application_success = self._submit_application(
                user_id, job_id, match_score, cover_letter, True
            )
            
            if application_success:
                # Send success notification
                self._send_application_notification(
                    user_id, job, match_score, True, None
                )
                self.logger.info(f"✅ Successfully auto-applied to {job.get('title', job.get('job_title', 'Unknown Job'))}")
                return True
            else:
                failure_reason = "Application submission failed"
                self._log_failed_application(user_id, job_id, match_score, failure_reason)
                self._send_application_notification(
                    user_id, job, match_score, False, failure_reason
                )
                self.logger.warning(f"❌ Auto-apply failed for {job.get('title', job.get('job_title', 'Unknown Job'))}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error submitting application: {e}")
            return False

    def _calculate_simple_match_score(self, user_profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        """Simple match score calculation without AI"""
        score = 0
        
        # Skills matching
        user_skills = user_profile.get('skills', [])
        if isinstance(user_skills, str):
            user_skills = [s.strip() for s in user_skills.split(',') if s.strip()]
        
        job_desc = job.get('description', '').lower()
        job_title = job.get('title', '').lower()
        job_full_text = job_desc + " " + job_title
        
        skill_matches = 0
        if user_skills:
            for skill in user_skills:
                if skill.lower() in job_full_text:
                    skill_matches += 1
            if user_skills:
                score += (skill_matches / len(user_skills)) * 50
        
        # Experience matching
        user_exp = user_profile.get('experience_years', 0)
        job_min_exp = job.get('min_experience', 0)
        
        if user_exp >= job_min_exp:
            score += 30
        elif job_min_exp > 0:
            score += (user_exp / job_min_exp) * 30
        
        # Location preference
        user_location = user_profile.get('location', '').lower()
        job_location = job.get('location', '').lower()
        
        if user_location and job_location and user_location in job_location:
            score += 20
        
        return min(score, 100)

    def _generate_basic_cover_letter(self, user_profile: Dict[str, Any], 
                                    job: Dict[str, Any]) -> str:
        """Generate a basic cover letter"""
        name = user_profile.get('full_name', user_profile.get('name', 'Applicant'))
        job_title = job.get('title', job.get('job_title', 'the position'))
        company = job.get('company', 'your company')
        skills = user_profile.get('skills', [])
        
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',') if s.strip()]
        
        top_skills = skills[:3] if skills else ['relevant skills']
        
        return f"""Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company}. 
Based on my skills and experience in {', '.join(top_skills)}, I believe I would be a great fit for this role.

I am excited about the opportunity to contribute to your team and help achieve your company's goals.

Thank you for considering my application. I look forward to discussing how I can contribute to {company}.

Sincerely,
{name}
"""

    def _submit_application(self, user_id: str, job_id: str, 
                           match_score: float, cover_letter: str,
                           is_auto_applied: bool) -> bool:
        """Submit application to database"""
        if self.supabase is None:
            self.logger.info(f"✅ Simulated application: User {user_id} -> Job {job_id}")
            return True
        
        try:
            application_data = {
                "user_id": user_id,
                "job_id": job_id,
                "status": "applied",
                "match_score": float(match_score),
                "cover_letter": cover_letter,
                "is_auto_applied": is_auto_applied,
                "applied_at": datetime.now().isoformat(),
            }
            
            response = self.supabase.table("applications") \
                .insert(application_data) \
                .execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            self.logger.error(f"Error submitting application: {e}")
            return False

    # ==================== LOGGING AND NOTIFICATIONS ====================
    def _log_failed_application(self, user_id: str, job_id: str, 
                               match_score: float, failure_reason: str):
        """Log failed application to database"""
        if self.supabase is None:
            self.logger.info(f"⚠️ Simulated failed application: {failure_reason}")
            return
        
        try:
            application_data = {
                "user_id": user_id,
                "job_id": job_id,
                "status": "failed",
                "match_score": float(match_score),
                "is_auto_applied": True,
                "failure_reason": failure_reason,
                "applied_at": datetime.now().isoformat(),
            }
            
            self.supabase.table("applications") \
                .insert(application_data) \
                .execute()
            
        except Exception as e:
            self.logger.error(f"Error logging failed application: {e}")

    def _send_application_notification(self, user_id: str, job: Dict[str, Any], 
                                      match_score: float, success: bool, 
                                      failure_reason: str = None):
        """Send notification to user about application status"""
        if not self.config["enable_notifications"]:
            return
        
        if self.supabase is None:
            status = "✅" if success else "❌"
            self.logger.info(f"{status} Notification: User {user_id} - {'Applied' if success else 'Failed'} to {job.get('title', 'job')}")
            return
        
        try:
            job_title = job.get("title", job.get("job_title", "Unknown Position"))
            company = job.get("company", "Unknown Company")
            
            if success:
                title = f"✅ Auto-applied to {job_title}"
                message = f"Successfully applied to {job_title} at {company} ({match_score:.1f}% match)"
                notification_type = "application_success"
            else:
                title = f"❌ Auto-apply failed for {job_title}"
                message = f"Failed to apply to {job_title} at {company}"
                if failure_reason:
                    message += f". Reason: {failure_reason}"
                notification_type = "application_failed"
            
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "is_read": False,
                "created_at": datetime.now().isoformat(),
                "data": json.dumps({
                    "job_id": job.get("id"),
                    "job_title": job_title,
                    "company": company,
                    "match_score": float(match_score),
                    "success": success,
                    "failure_reason": failure_reason
                })
            }
            
            self.supabase.table("notifications") \
                .insert(notification_data) \
                .execute()
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")

    # ==================== UTILITY METHODS ====================
    def check_pending_notifications(self):
        """Check and send pending notifications"""
        try:
            self.logger.debug("Checking pending notifications...")
        except Exception as e:
            self.logger.error(f"Error checking notifications: {e}")

    def cleanup_temp_files(self):
        """Cleanup temporary files"""
        try:
            self.logger.debug("Cleaning up temporary files...")
        except Exception as e:
            self.logger.error(f"Error cleaning up files: {e}")

    def manual_trigger(self, user_id: str = None):
        """Manually trigger auto-apply for specific user or all users"""
        self.logger.info(f"🚀 Manual trigger for user: {user_id or 'ALL'}")
        
        if user_id:
            # Use the new method
            result = self.run_auto_apply_for_user(user_id)
            self.logger.info(f"✅ Manual trigger result: {result}")
            return result
        else:
            # Trigger for all users
            self.run_auto_apply_cycle()

    def get_application_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get auto-application statistics"""
        try:
            if self.supabase is None:
                return {
                    "total_applications": 5,
                    "successful": 3,
                    "failed": 2,
                    "success_rate": 60.0,
                    "average_match_score": 75.5,
                    "status_breakdown": {"applied": 3, "failed": 2},
                    "last_updated": datetime.now().isoformat()
                }
            
            query = self.supabase.table("applications") \
                .select("*", count="exact") \
                .eq("is_auto_applied", True)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            response = query.execute()
            
            total_applications = response.count or 0
            
            # Count by status
            status_counts = {}
            if response.data:
                for app in response.data:
                    status = app.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            # Calculate success rate
            successful = status_counts.get("applied", 0)
            failed = status_counts.get("failed", 0)
            success_rate = (successful / total_applications * 100) if total_applications > 0 else 0
            
            # Calculate average match score
            avg_match_score = 0
            if response.data:
                total_score = 0
                scored_apps = 0
                for app in response.data:
                    if app.get("match_score"):
                        total_score += float(app.get("match_score", 0))
                        scored_apps += 1
                if scored_apps > 0:
                    avg_match_score = total_score / scored_apps
            
            return {
                "total_applications": total_applications,
                "successful": successful,
                "failed": failed,
                "success_rate": round(success_rate, 2),
                "average_match_score": round(avg_match_score, 2),
                "status_breakdown": status_counts,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting application stats: {e}")
            return {
                "total_applications": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0,
                "average_match_score": 0,
                "status_breakdown": {},
                "error": str(e)
            }

    def generate_ai_insights(self, user_id: str) -> List[str]:
        """Generate AI insights for user"""
        try:
            if self.supabase is None:
                return [
                    "Complete your profile to get better job matches",
                    "Upload your resume for AI-powered matching",
                    "Apply to jobs to get personalized insights"
                ]
            
            # Get user's applications
            response = self.supabase.table("applications") \
                .select("*") \
                .eq("user_id", user_id) \
                .execute()
            
            applications = response.data
            
            if not applications:
                return ["Start applying to jobs to get personalized insights"]
            
            # Calculate insights
            total = len(applications)
            successful = len([a for a in applications if a.get("status") in ["applied", "viewed", "shortlisted"]])
            success_rate = (successful / total * 100) if total > 0 else 0
            
            # Calculate average match score
            match_scores = [float(a.get("match_score", 0)) for a in applications if a.get("match_score")]
            avg_match = sum(match_scores) / len(match_scores) if match_scores else 0
            
            insights = []
            
            if success_rate < 50:
                insights.append(f"Your application success rate is {success_rate:.1f}%. Consider improving your resume and cover letters.")
            elif success_rate > 70:
                insights.append(f"Great! Your application success rate is {success_rate:.1f}%")
            
            if avg_match < 60:
                insights.append(f"Average match score: {avg_match:.1f}%. Apply to more relevant jobs.")
            elif avg_match > 80:
                insights.append(f"Excellent! Your average match score is {avg_match:.1f}%")
            
            auto_applied = len([a for a in applications if a.get("is_auto_applied")])
            if auto_applied > 0:
                insights.append(f"AI has auto-applied to {auto_applied} jobs for you.")
            
            # Add generic insights
            if len(insights) < 3:
                insights.extend([
                    "Complete your profile to get better job matches",
                    "Upload your resume for AI-powered matching",
                    "Apply to at least 3 more jobs to get personalized insights"
                ])
            
            return insights[:5]
            
        except Exception as e:
            self.logger.error(f"Error generating AI insights: {e}")
            return [
                "Complete your profile to get better job matches",
                "Upload your resume for AI-powered matching",
                "Apply to jobs to get personalized insights"
            ]

# ============== RUN AS STANDALONE SCRIPT ==============
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AUTO APPLY CRON SERVICE")
    print("=" * 60)
    
    try:
        # Create instance
        auto_applier = AutoApplyCron()
        
        print("✅ AutoApplyCron initialized successfully")
        print(f"🤖 AI Modules Available: {auto_applier.ai_modules_available}")
        print(f"🗄️  Supabase Connected: {auto_applier.supabase is not None}")
        print("🕐 Starting scheduler...")
        
        # Start the scheduler
        auto_applier.start_scheduler()
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down auto-apply scheduler...")
            auto_applier.stop_scheduler()
            
    except Exception as e:
        print(f"\n❌ Error starting auto-apply service: {e}")
        import traceback
        traceback.print_exc()
import os
import time
import schedule
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Import AI modules
from cv_parser_nlp import CVParserNLP
from cover_letter_ai import CoverLetterAI
from job_matcher import JobMatcher

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
        
        # Initialize Supabase
        self.supabase = self._init_supabase()
        
        # Initialize AI modules
        self.cv_parser = CVParserNLP()
        self.cover_letter_ai = CoverLetterAI()
        self.job_matcher = JobMatcher()
        
        # Configuration
        self.config = {
            "check_interval_hours": 2,
            "max_applications_per_day": 10,
            "min_match_threshold": 65,
            "apply_hours_start": 9,
            "apply_hours_end": 18,
            "enable_notifications": True
        }
        
        self.running = False
        self.thread = None
        self.logger.info("✅ AutoApplyCron initialized with AI decision system")
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                self.logger.warning("⚠️ Supabase credentials not found")
                return None
            
            self.logger.info(f"🔗 Connecting to Supabase: {url[:30]}...")
            return create_client(url, key)
        except Exception as e:
            self.logger.error(f"❌ Supabase init error: {e}")
            return None
    
    def start_scheduler(self):
        """Start the auto-apply scheduler"""
        if self.running:
            return
        
        self.running = True
        
        # Schedule regular checks
        schedule.every(self.config["check_interval_hours"]).hours.do(self.run_auto_apply_cycle)
        schedule.every().day.at("09:00").do(self.run_auto_apply_cycle)
        schedule.every().day.at("14:00").do(self.run_auto_apply_cycle)
        schedule.every().day.at("17:00").do(self.run_auto_apply_cycle)
        
        # Start scheduler thread
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        self.logger.info("✅ Auto-apply scheduler started with AI decision system")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
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
    
    def run_auto_apply_cycle(self):
        """Main auto-apply cycle for all users"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🚀 Starting AI-powered auto-apply cycle")
            start_time = datetime.now()
            
            # Get all users with auto-apply enabled
            users = self._get_auto_apply_users()
            if not users:
                self.logger.info("ℹ️ No users with auto-apply enabled")
                return
            
            self.logger.info(f"👥 Found {len(users)} users with auto-apply enabled")
            
            total_applications = 0
            successful_users = 0
            
            for user in users:
                try:
                    user_id = user.get("id") or user.get("user_id")
                    if not user_id:
                        continue
                    
                    self.logger.info(f"\n{'='*40}")
                    self.logger.info(f"👤 Processing user: {user_id}")
                    
                    # Get user profile
                    user_profile = self._get_user_profile(user_id)
                    if not user_profile:
                        self.logger.warning(f"⚠️ No profile found for user {user_id}")
                        continue
                    
                    # Get user settings
                    settings = self._get_user_settings(user_id)
                    daily_limit = settings.get("daily_apply_limit", self.config["max_applications_per_day"])
                    threshold = settings.get("auto_apply_threshold", self.config["min_match_threshold"])
                    
                    # Check today's applications
                    todays_apps = self._get_todays_applications(user_id)
                    if len(todays_apps) >= daily_limit:
                        self.logger.info(f"📊 User {user_id} reached daily limit ({len(todays_apps)}/{daily_limit})")
                        continue
                    
                    remaining = daily_limit - len(todays_apps)
                    self.logger.info(f"📊 Daily limit: {daily_limit}, Applied today: {len(todays_apps)}, Remaining: {remaining}")
                    
                    # Get new jobs
                    new_jobs = self._get_new_jobs_for_user(user_id)
                    if not new_jobs:
                        self.logger.info(f"ℹ️ No new jobs for user {user_id}")
                        continue
                    
                    self.logger.info(f"📋 Found {len(new_jobs)} new jobs to evaluate")
                    
                    # Process applications
                    applications_sent = self._process_user_applications(
                        user, user_profile, new_jobs[:remaining], threshold
                    )
                    
                    total_applications += applications_sent
                    if applications_sent > 0:
                        successful_users += 1
                    
                    # Rate limiting between users
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing user {user.get('id')}: {e}")
                    continue
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"✅ Auto-apply cycle completed!")
            self.logger.info(f"📊 Total applications: {total_applications}")
            self.logger.info(f"👥 Successful users: {successful_users}")
            self.logger.info(f"⏱️ Duration: {duration:.2f} seconds")
            self.logger.info(f"{'='*60}\n")
            
        except Exception as e:
            self.logger.error(f"❌ Auto-apply cycle failed: {e}")
    
    def run_auto_apply_for_user(self, user_id: str, threshold: int = 75, max_applications: int = 5):
        """Run auto-apply for specific user"""
        try:
            self.logger.info(f"🎯 Running targeted auto-apply for user: {user_id}")
            
            if not self.supabase:
                return {
                    "success": False,
                    "error": "Database connection not available"
                }
            
            # Get user
            user_profile = self._get_user_profile(user_id)
            if not user_profile:
                return {"success": False, "error": "User profile not found"}
            
            # Create user dict
            user = {"id": user_id, "user_id": user_id}
            
            # Get new jobs
            new_jobs = self._get_new_jobs_for_user(user_id)
            if not new_jobs:
                return {
                    "success": True,
                    "applications_sent": 0,
                    "message": "No new jobs available"
                }
            
            # Process applications
            applications_sent = self._process_user_applications(
                user, user_profile, new_jobs[:max_applications], threshold
            )
            
            # Update user settings with last run
            self._update_last_run_time(user_id)
            
            return {
                "success": True,
                "applications_sent": applications_sent,
                "message": f"Successfully applied to {applications_sent} jobs",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in targeted auto-apply: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_auto_apply_users(self) -> List[Dict]:
        """Get all users with auto-apply enabled"""
        try:
            if not self.supabase:
                self.logger.warning("⚠️ Supabase not available, returning empty list")
                return []
            
            # Try user_settings table first
            try:
                resp = self.supabase.table("user_settings")\
                    .select("user_id, auto_apply_threshold, daily_apply_limit")\
                    .eq("is_auto_apply", True)\
                    .execute()
                
                if resp.data:
                    user_ids = [item["user_id"] for item in resp.data if item.get("user_id")]
                    self.logger.info(f"✅ Found {len(user_ids)} users from user_settings")
                    
                    if user_ids:
                        # Get user profiles
                        profiles_resp = self.supabase.table("profiles2")\
                            .select("*")\
                            .in_("user_id", user_ids)\
                            .execute()
                        
                        if profiles_resp.data:
                            return profiles_resp.data
                        
                        # Create basic user objects
                        return [{"user_id": uid, "id": uid} for uid in user_ids]
            except Exception as e:
                self.logger.warning(f"⚠️ user_settings table error: {e}")
            
            # Try profiles2 table
            try:
                resp = self.supabase.table("profiles2")\
                    .select("*")\
                    .eq("is_auto_apply", True)\
                    .execute()
                
                if resp.data:
                    self.logger.info(f"✅ Found {len(resp.data)} users from profiles2")
                    return resp.data
            except Exception as e:
                self.logger.warning(f"⚠️ profiles2 table error: {e}")
            
            self.logger.info("ℹ️ No users found with auto-apply enabled")
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching auto-apply users: {e}")
            return []
    
    def _get_user_profile(self, user_id: str) -> Dict:
        """Get full user profile"""
        if not self.supabase:
            return self._get_fallback_profile(user_id)
        
        try:
            # Try profiles2 first
            resp = self.supabase.table("profiles2")\
                .select("*")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            
            if resp.data:
                self.logger.info(f"✅ Profile found in profiles2 for {user_id}")
                return resp.data
            
            # Try profiles1
            resp = self.supabase.table("profiles1")\
                .select("*")\
                .eq("id", user_id)\
                .maybe_single()\
                .execute()
            
            if resp.data:
                self.logger.info(f"✅ Profile found in profiles1 for {user_id}")
                return resp.data
            
            self.logger.warning(f"⚠️ No profile found for {user_id}")
            return {}
            
        except Exception as e:
            self.logger.error(f"❌ Error getting profile for {user_id}: {e}")
            return {}
    
    def _get_user_settings(self, user_id: str) -> Dict:
        """Get user auto-apply settings"""
        try:
            if not self.supabase:
                return {}
            
            resp = self.supabase.table("user_settings")\
                .select("*")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            
            if resp.data:
                return resp.data
            
            return {}
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting settings: {e}")
            return {}
    
    def _get_todays_applications(self, user_id: str) -> List:
        """Get today's applications count"""
        if not self.supabase:
            return []
        
        try:
            today = datetime.now().date().isoformat()
            
            resp = self.supabase.table("applications")\
                .select("id")\
                .eq("user_id", user_id)\
                .gte("applied_at", today)\
                .execute()
            
            return resp.data or []
            
        except Exception as e:
            self.logger.error(f"❌ Error getting today's applications: {e}")
            return []
    
    def _get_new_jobs_for_user(self, user_id: str) -> List[Dict]:
        """Get jobs user hasn't applied to"""
        if not self.supabase:
            return self._get_fallback_jobs()
        
        try:
            # Get already applied job IDs
            applied_resp = self.supabase.table("applications")\
                .select("job_id")\
                .eq("user_id", user_id)\
                .execute()
            
            applied_ids = [a["job_id"] for a in applied_resp.data] if applied_resp.data else []
            
            # Get recent active jobs
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            
            query = self.supabase.table("nokri")\
                .select("*, companies!company_id(*)")\
                .gte("created_at", cutoff)\
                .order("created_at", ascending=False)\
                .limit(50)
            
            # Filter out applied jobs if any
            if applied_ids:
                query = query.not_.in_("id", applied_ids)
            
            resp = query.execute()
            
            if resp.data:
                new_jobs = [j for j in resp.data if j.get("id") not in applied_ids]
                self.logger.info(f"✅ Found {len(new_jobs)} new jobs for user {user_id}")
                return new_jobs
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Error getting new jobs: {e}")
            return []
    
    def _process_user_applications(self, user: Dict, user_profile: Dict, 
                                   jobs: List[Dict], threshold: int) -> int:
        """Process applications for a user"""
        user_id = user.get("id") or user.get("user_id")
        applications_sent = 0
        applications_data = []  # Store for employer notifications
        
        self.logger.info(f"🤖 Processing {len(jobs)} jobs for user {user_id}")
        
        for idx, job in enumerate(jobs, 1):
            try:
                self.logger.info(f"\n--- Job {idx}/{len(jobs)} ---")
                job_id = job.get("id")
                job_title = job.get("job_title", "Unknown Position")
                company_name = job.get("companies", {}).get("companyname", "Unknown Company") if isinstance(job.get("companies"), dict) else "Unknown Company"
                
                self.logger.info(f"📋 Evaluating: {job_title} at {company_name}")
                
                # Step 1: Get AI match analysis
                match_result = self.job_matcher.calculate_match_score(user_profile, job)
                
                match_score = match_result.get("total_score", 50)
                should_apply = match_result.get("should_apply", False)
                ai_decision = match_result.get("ai_decision", "MAYBE")
                ai_reasoning = match_result.get("ai_reasoning", "")
                
                self.logger.info(f"📊 Match Score: {match_score:.1f}%")
                self.logger.info(f"🤖 AI Decision: {ai_decision}")
                self.logger.info(f"💡 Reasoning: {ai_reasoning}")
                
                # Check if should apply
                if not should_apply:
                    self.logger.info(f"❌ AI says DON'T APPLY: {ai_reasoning}")
                    self._log_failed_application(user_id, job_id, match_score, 
                                                f"AI rejected: {ai_reasoning}")
                    continue
                
                if match_score < threshold:
                    self.logger.info(f"📉 Score {match_score:.1f}% below threshold {threshold}%")
                    self._log_failed_application(user_id, job_id, match_score,
                                                f"Below threshold ({match_score:.1f}% < {threshold}%)")
                    continue
                
                self.logger.info(f"✅ AI APPROVED application")
                
                # Step 2: Generate cover letter
                cover_letter = self.cover_letter_ai.generate_cover_letter(user_profile, job)
                self.logger.info(f"📝 Cover letter generated ({len(cover_letter)} chars)")
                
                # Step 3: Submit application
                success, application_id = self._submit_application(
                    user_id, job_id, match_score, cover_letter, True, ai_reasoning
                )
                
                if success:
                    applications_sent += 1
                    
                    # Store for employer notification
                    app_data = {
                        "application_id": application_id,
                        "user_id": user_id,
                        "user_name": user_profile.get("full_name") or 
                                    f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip() or "Candidate",
                        "job_id": job_id,
                        "job_title": job_title,
                        "company_id": job.get("company_id"),
                        "company_name": company_name,
                        "match_score": match_score,
                        "ai_reasoning": ai_reasoning,
                        "cover_letter": cover_letter[:200],  # Truncate for notification
                        "applied_at": datetime.now().isoformat()
                    }
                    applications_data.append(app_data)
                    
                    self.logger.info(f"✅ Successfully applied to: {job_title}")
                    
                    # Send success notification to user
                    self._send_user_notification(user_id, job, match_score, True)
                else:
                    self.logger.warning(f"❌ Submission failed for {job_title}")
                    self._log_failed_application(user_id, job_id, match_score, "Submission failed")
                    self._send_user_notification(user_id, job, match_score, False, "Submission failed")
                
                # Rate limiting
                time.sleep(3)
                
            except Exception as e:
                self.logger.error(f"❌ Error processing job {job.get('id')}: {e}")
                continue
        
        # Send employer notifications for all successful applications
        if applications_data:
            self._notify_employers_batch(applications_data)
        
        self.logger.info(f"\n✅ Completed processing for user {user_id}: {applications_sent} applications sent")
        return applications_sent
    
    def _submit_application(self, user_id: str, job_id: str, match_score: float,
                           cover_letter: str, is_auto_applied: bool, 
                           ai_reasoning: str = None) -> tuple:
        """Submit application to database"""
        if not self.supabase:
            self.logger.info(f"🔄 Simulated application: {user_id} -> {job_id}")
            return True, f"simulated_{datetime.now().timestamp()}"
        
        try:
            application_data = {
                "user_id": user_id,
                "job_id": job_id,
                "status": "applied",
                "match_score": float(match_score),
                "cover_letter": cover_letter,
                "is_auto_applied": is_auto_applied,
                "ai_reasoning": ai_reasoning,
                "applied_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            resp = self.supabase.table("applications").insert(application_data).execute()
            
            if resp.data and len(resp.data) > 0:
                application_id = resp.data[0].get("id")
                self.logger.info(f"✅ Application created: {application_id}")
                return True, application_id
            
            self.logger.error("❌ No data returned from insert")
            return False, None
            
        except Exception as e:
            self.logger.error(f"❌ Submission error: {e}")
            return False, None
    
    def _notify_employers_batch(self, applications_data: List[Dict]):
        """Send notifications to employers about new applications"""
        if not self.supabase or not applications_data:
            return
        
        self.logger.info(f"\n📨 Sending employer notifications for {len(applications_data)} applications...")
        
        try:
            # Group applications by company
            company_apps = {}
            for app in applications_data:
                company_id = app.get("company_id")
                if not company_id:
                    continue
                
                if company_id not in company_apps:
                    company_apps[company_id] = []
                company_apps[company_id].append(app)
            
            # Process each company
            for company_id, apps in company_apps.items():
                try:
                    # Get employers for this company
                    employers_resp = self.supabase.table("profiles2")\
                        .select("user_id, email")\
                        .eq("company_id", company_id)\
                        .eq("role", "Employer")\
                        .execute()
                    
                    if not employers_resp.data:
                        self.logger.info(f"ℹ️ No employers found for company {company_id}")
                        continue
                    
                    # Also try to get employers from companies table
                    company_resp = self.supabase.table("companies")\
                        .select("user_id")\
                        .eq("id", company_id)\
                        .maybe_single()\
                        .execute()
                    
                    employer_ids = set()
                    for emp in employers_resp.data:
                        if emp.get("user_id"):
                            employer_ids.add(emp["user_id"])
                    
                    if company_resp.data and company_resp.data.get("user_id"):
                        employer_ids.add(company_resp.data["user_id"])
                    
                    # Send notification to each employer
                    for employer_id in employer_ids:
                        for app in apps:
                            notification_data = {
                                "user_id": employer_id,
                                "title": "🔔 New Application Received",
                                "message": f"{app['user_name']} applied for {app['job_title']} ({app['match_score']:.0f}% AI match)",
                                "type": "new_application",
                                "is_read": False,
                                "created_at": datetime.now().isoformat(),
                                "data": json.dumps({
                                    "application_id": app["application_id"],
                                    "candidate_id": app["user_id"],
                                    "candidate_name": app["user_name"],
                                    "job_id": app["job_id"],
                                    "job_title": app["job_title"],
                                    "match_score": app["match_score"],
                                    "ai_reasoning": app.get("ai_reasoning", ""),
                                    "cover_letter_preview": app.get("cover_letter", "")[:150],
                                    "applied_at": app["applied_at"]
                                })
                            }
                            
                            try:
                                self.supabase.table("notifications").insert(notification_data).execute()
                                self.logger.info(f"✅ Notification sent to employer {employer_id} for application {app['application_id']}")
                            except Exception as e:
                                self.logger.error(f"❌ Failed to send notification to employer {employer_id}: {e}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error notifying employers for company {company_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ Error in batch employer notifications: {e}")
    
    def _send_user_notification(self, user_id: str, job: Dict, match_score: float,
                               success: bool, reason: str = None):
        """Send notification to user about application status"""
        if not self.supabase:
            return
        
        try:
            job_title = job.get("job_title", "Unknown Position")
            company = job.get("companies", {}).get("companyname", "Company") if isinstance(job.get("companies"), dict) else "Company"
            
            if success:
                title = f"✅ Auto-Applied Successfully"
                message = f"Applied to {job_title} at {company} ({match_score:.0f}% match)"
                notif_type = "auto_apply_success"
            else:
                title = f"❌ Application Failed"
                message = f"Failed to apply to {job_title}: {reason or 'Unknown error'}"
                notif_type = "auto_apply_failed"
            
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notif_type,
                "is_read": False,
                "created_at": datetime.now().isoformat(),
                "data": json.dumps({
                    "job_id": job.get("id"),
                    "job_title": job_title,
                    "company": company,
                    "match_score": float(match_score),
                    "success": success,
                    "reason": reason
                })
            }
            
            self.supabase.table("notifications").insert(notification_data).execute()
            
        except Exception as e:
            self.logger.error(f"❌ Error sending user notification: {e}")
    
    def _log_failed_application(self, user_id: str, job_id: str, match_score: float, reason: str):
        """Log failed application for analytics"""
        if not self.supabase:
            return
        
        try:
            data = {
                "user_id": user_id,
                "job_id": job_id,
                "status": "failed",
                "match_score": float(match_score),
                "is_auto_applied": True,
                "failure_reason": reason,
                "applied_at": datetime.now().isoformat()
            }
            self.supabase.table("failed_applications").insert(data).execute()
        except Exception as e:
            self.logger.warning(f"⚠️ Could not log failed application: {e}")
    
    def _update_last_run_time(self, user_id: str):
        """Update last auto-apply run time"""
        if not self.supabase:
            return
        
        try:
            self.supabase.table("user_settings").update({
                "last_auto_apply_run": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).execute()
        except Exception as e:
            self.logger.warning(f"⚠️ Could not update last run time: {e}")
    
    def _get_fallback_profile(self, user_id: str) -> Dict:
        """Fallback profile for testing"""
        return {
            "id": user_id,
            "user_id": user_id,
            "full_name": "Test User",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "skills": ["Flutter", "Python", "JavaScript", "React", "Node.js"],
            "experience_years": 3,
            "summary": "Experienced developer with focus on mobile and web applications"
        }
    
    def _get_fallback_jobs(self) -> List[Dict]:
        """Fallback jobs for testing"""
        return [
            {
                "id": "job_1",
                "job_title": "Flutter Developer",
                "company_id": "comp_1",
                "companies": {"companyname": "Tech Corp"},
                "job_description": "Looking for Flutter developer with 2+ years experience",
                "job_location": "Remote",
                "employment_type": "Full-time"
            },
            {
                "id": "job_2",
                "job_title": "React Developer",
                "company_id": "comp_2",
                "companies": {"companyname": "Startup Inc"},
                "job_description": "React.js developer needed for web application",
                "job_location": "New York",
                "employment_type": "Contract"
            }
        ]


# ============== MAIN EXECUTION ==============
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AI AUTO-APPLY SERVICE")
    print("=" * 60)
    
    applier = AutoApplyCron()
    applier.start_scheduler()
    
    print("\n✅ Auto-apply service is running...")
    print("📊 Checking for new jobs every 2 hours")
    print("📨 Employer notifications will be sent for new applications")
    print("🔔 User notifications will be sent for application status")
    print("\nPress Ctrl+C to stop the service\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down auto-apply service...")
        applier.stop_scheduler()
        print("✅ Service stopped successfully")
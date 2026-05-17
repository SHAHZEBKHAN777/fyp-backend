import json
from datetime import datetime
from typing import Dict, List, Any
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class EmployerService:
    def __init__(self):
        """Initialize employer service"""
        self.supabase = self._init_supabase()
        self.notification_service = None  # Will be set by main server
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                logger.warning("⚠️ Supabase credentials not found")
                return None
            
            return create_client(url, key)
        except Exception as e:
            logger.error(f"❌ Supabase init error: {e}")
            return None
    
    def get_employer_applications(self, employer_id: str, status: str = None) -> List[Dict]:
        """Get all applications for employer's jobs"""
        try:
            if not self.supabase:
                return []
            
            # Get employer's companies
            companies_resp = self.supabase.table("companies")\
                .select("id")\
                .eq("user_id", employer_id)\
                .execute()
            
            if not companies_resp.data:
                logger.info(f"ℹ️ No companies found for employer {employer_id}")
                return []
            
            company_ids = [c["id"] for c in companies_resp.data]
            
            # Get jobs for these companies
            jobs_resp = self.supabase.table("nokri")\
                .select("id")\
                .in_("company_id", company_ids)\
                .execute()
            
            if not jobs_resp.data:
                return []
            
            job_ids = [j["id"] for j in jobs_resp.data]
            
            # Get applications with details
            query = self.supabase.table("applications")\
                .select("*, profiles2!user_id(*), nokri!job_id(*, companies!company_id(*))")\
                .in_("job_id", job_ids)\
                .order("applied_at", ascending=False)
            
            if status:
                query = query.eq("status", status)
            
            resp = query.execute()
            
            if resp.data:
                # Format applications
                formatted_apps = []
                for app in resp.data:
                    formatted_app = {
                        "application_id": app.get("id"),
                        "job_id": app.get("job_id"),
                        "job_title": app.get("nokri", {}).get("job_title", "Unknown"),
                        "company": app.get("nokri", {}).get("companies", {}).get("companyname", "Unknown"),
                        "candidate_id": app.get("user_id"),
                        "candidate_name": self._get_candidate_name(app.get("profiles2", {})),
                        "candidate_email": app.get("profiles2", {}).get("email", ""),
                        "candidate_skills": app.get("profiles2", {}).get("skills", []),
                        "match_score": app.get("match_score", 0),
                        "status": app.get("status", "applied"),
                        "cover_letter": app.get("cover_letter", ""),
                        "ai_reasoning": app.get("ai_reasoning", ""),
                        "is_auto_applied": app.get("is_auto_applied", False),
                        "applied_at": app.get("applied_at", ""),
                        "updated_at": app.get("updated_at", "")
                    }
                    formatted_apps.append(formatted_app)
                
                logger.info(f"✅ Found {len(formatted_apps)} applications for employer {employer_id}")
                return formatted_apps
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Error getting employer applications: {e}")
            return []
    
    def update_application_status(self, application_id: str, status: str, 
                                  employer_id: str, feedback: str = None) -> Dict:
        """Update application status (shortlist/reject)"""
        try:
            if not self.supabase:
                return {"success": False, "error": "Database not connected"}
            
            # Validate status
            valid_statuses = ["viewed", "shortlisted", "rejected", "interview_scheduled"]
            if status not in valid_statuses:
                return {"success": False, "error": f"Invalid status. Use: {valid_statuses}"}
            
            # Verify employer owns this application
            app_resp = self.supabase.table("applications")\
                .select("id, job_id, user_id, nokri!job_id(company_id, companies!company_id(user_id))")\
                .eq("id", application_id)\
                .maybe_single()\
                .execute()
            
            if not app_resp.data:
                return {"success": False, "error": "Application not found"}
            
            app_data = app_resp.data
            
            # Check if employer owns the job
            company_owner = app_data.get("nokri", {}).get("companies", {}).get("user_id")
            if company_owner != employer_id:
                return {"success": False, "error": "Unauthorized: You don't own this job posting"}
            
            # Update application status
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if feedback:
                update_data["employer_feedback"] = feedback
            
            self.supabase.table("applications")\
                .update(update_data)\
                .eq("id", application_id)\
                .execute()
            
            # Send notification to candidate
            candidate_id = app_data.get("user_id")
            job_title = app_data.get("nokri", {}).get("job_title", "the position")
            
            self._send_status_notification(candidate_id, application_id, job_title, status, feedback)
            
            logger.info(f"✅ Application {application_id} updated to {status}")
            
            return {
                "success": True,
                "message": f"Application {status} successfully",
                "notification_sent": True
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating application status: {e}")
            return {"success": False, "error": str(e)}
    
    def get_application_detail(self, application_id: str, employer_id: str) -> Dict:
        """Get detailed application with candidate info"""
        try:
            if not self.supabase:
                return {}
            
            resp = self.supabase.table("applications")\
                .select("*, profiles2!user_id(*), nokri!job_id(*, companies!company_id(*))")\
                .eq("id", application_id)\
                .maybe_single()\
                .execute()
            
            if not resp.data:
                return {}
            
            app = resp.data
            
            # Verify employer ownership
            company_owner = app.get("nokri", {}).get("companies", {}).get("user_id")
            if company_owner != employer_id:
                return {"error": "Unauthorized"}
            
            return {
                "application_id": app.get("id"),
                "candidate": {
                    "id": app.get("user_id"),
                    "name": self._get_candidate_name(app.get("profiles2", {})),
                    "email": app.get("profiles2", {}).get("email"),
                    "skills": app.get("profiles2", {}).get("skills", []),
                    "experience": app.get("profiles2", {}).get("experience_years"),
                    "location": app.get("profiles2", {}).get("location"),
                    "profile_image": app.get("profiles2", {}).get("profile_image_url")
                },
                "job": {
                    "id": app.get("job_id"),
                    "title": app.get("nokri", {}).get("job_title"),
                    "company": app.get("nokri", {}).get("companies", {}).get("companyname")
                },
                "match_score": app.get("match_score"),
                "status": app.get("status"),
                "cover_letter": app.get("cover_letter"),
                "ai_reasoning": app.get("ai_reasoning"),
                "is_auto_applied": app.get("is_auto_applied"),
                "applied_at": app.get("applied_at"),
                "feedback": app.get("employer_feedback")
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting application detail: {e}")
            return {}
    
    def get_application_stats(self, employer_id: str) -> Dict:
        """Get application statistics for employer dashboard"""
        try:
            applications = self.get_employer_applications(employer_id)
            
            stats = {
                "total": len(applications),
                "new": 0,
                "viewed": 0,
                "shortlisted": 0,
                "rejected": 0,
                "auto_applied": 0,
                "average_match": 0
            }
            
            total_match = 0
            
            for app in applications:
                status = app.get("status")
                if status == "applied":
                    stats["new"] += 1
                elif status == "viewed":
                    stats["viewed"] += 1
                elif status == "shortlisted":
                    stats["shortlisted"] += 1
                elif status == "rejected":
                    stats["rejected"] += 1
                
                if app.get("is_auto_applied"):
                    stats["auto_applied"] += 1
                
                match = app.get("match_score", 0)
                if match:
                    total_match += match
            
            if stats["total"] > 0:
                stats["average_match"] = round(total_match / stats["total"], 1)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {}
    
    def _get_candidate_name(self, profile: Dict) -> str:
        """Get full name from profile"""
        if not profile:
            return "Unknown Candidate"
        
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        full = profile.get("full_name", "")
        
        if full:
            return full
        elif first or last:
            return f"{first} {last}".strip()
        else:
            return "Unknown Candidate"
    
    def _send_status_notification(self, candidate_id: str, application_id: str,
                                  job_title: str, status: str, feedback: str = None):
        """Send notification to candidate about status change"""
        try:
            if not self.supabase:
                return
            
            # Determine notification content based on status
            if status == "shortlisted":
                title = "🎉 Application Shortlisted!"
                message = f"Congratulations! Your application for {job_title} has been shortlisted."
                notif_type = "application_shortlisted"
            elif status == "rejected":
                title = "Application Update"
                message = f"Your application for {job_title} was not selected at this time."
                notif_type = "application_rejected"
            elif status == "viewed":
                title = "Application Viewed"
                message = f"Your application for {job_title} has been viewed by the employer."
                notif_type = "application_viewed"
            elif status == "interview_scheduled":
                title = "📅 Interview Scheduled!"
                message = f"Interview scheduled for {job_title} position."
                notif_type = "interview_scheduled"
            else:
                title = "Application Status Updated"
                message = f"Your application for {job_title} has been updated to {status}."
                notif_type = "application_status_updated"
            
            if feedback:
                message += f" Feedback: {feedback}"
            
            notification_data = {
                "user_id": candidate_id,
                "title": title,
                "message": message,
                "type": notif_type,
                "is_read": False,
                "created_at": datetime.now().isoformat(),
                "data": json.dumps({
                    "application_id": application_id,
                    "job_title": job_title,
                    "status": status,
                    "feedback": feedback,
                    "updated_at": datetime.now().isoformat()
                })
            }
            
            self.supabase.table("notifications").insert(notification_data).execute()
            logger.info(f"✅ Status notification sent to candidate {candidate_id}")

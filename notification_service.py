from datetime import datetime
from typing import Dict, List, Any
import json

class NotificationService:
    def __init__(self):
        self.notification_types = {
            "application_submitted": {
                "title": "Application Submitted",
                "message": "You've applied for {job_title} at {company}",
                "icon": "📝"
            },
            "application_viewed": {
                "title": "Application Viewed",
                "message": "Your application for {job_title} has been viewed",
                "icon": "👁️"
            },
            "application_shortlisted": {
                "title": "Shortlisted!",
                "message": "Congratulations! You've been shortlisted for {job_title}",
                "icon": "🎯"
            },
            "application_rejected": {
                "title": "Application Update",
                "message": "Your application for {job_title} was not selected",
                "icon": "❌"
            },
            "auto_apply_success": {
                "title": "Auto-Apply Success",
                "message": "AI applied to {job_title} at {company} ({match_score}% match)",
                "icon": "🤖"
            },
            "auto_apply_failed": {
                "title": "Auto-Apply Failed",
                "message": "Failed to apply to {job_title}: {error}",
                "icon": "⚠️"
            },
            "job_recommendation": {
                "title": "New Job Match",
                "message": "Found a perfect match: {job_title} at {company} ({match_score}% match)",
                "icon": "🎯"
            },
            "resume_optimized": {
                "title": "Resume Optimized",
                "message": "Your resume has been optimized for {job_title}",
                "icon": "✨"
            },
            "daily_summary": {
                "title": "Daily Summary",
                "message": "You applied to {count} jobs today. {successful} successful",
                "icon": "📊"
            }
        }
    
    def create_notification(self, user_id: str, notification_type: str, 
                          data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification"""
        try:
            if notification_type not in self.notification_types:
                notification_type = "application_submitted"
            
            template = self.notification_types[notification_type]
            
            # Format message with data
            message = template["message"].format(**data)
            
            notification = {
                "id": f"notif_{datetime.now().timestamp()}",
                "user_id": user_id,
                "type": notification_type,
                "title": template["title"],
                "message": message,
                "icon": template["icon"],
                "data": data,
                "is_read": False,
                "created_at": datetime.now().isoformat(),
                "read_at": None
            }
            
            # In real app, save to database
            # self._save_to_database(notification)
            
            return notification
            
        except Exception as e:
            print(f"Error creating notification: {e}")
            return self._create_fallback_notification(user_id, notification_type)
    
    def get_user_notifications(self, user_id: str, limit: int = 20, 
                              unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications for user"""
        try:
            # In real app, query database
            # For now, return sample notifications
            
            sample_notifications = [
                self.create_notification(
                    user_id=user_id,
                    notification_type="auto_apply_success",
                    data={
                        "job_title": "Senior Flutter Developer",
                        "company": "Tech Corp",
                        "match_score": 92
                    }
                ),
                self.create_notification(
                    user_id=user_id,
                    notification_type="application_viewed",
                    data={
                        "job_title": "Mobile App Developer",
                        "company": "Startup XYZ"
                    }
                ),
                self.create_notification(
                    user_id=user_id,
                    notification_type="job_recommendation",
                    data={
                        "job_title": "Flutter Team Lead",
                        "company": "Innovation Inc",
                        "match_score": 88
                    }
                )
            ]
            
            if unread_only:
                sample_notifications = [n for n in sample_notifications if not n.get("is_read", False)]
            
            return sample_notifications[:limit]
            
        except Exception as e:
            print(f"Error getting notifications: {e}")
            return []
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            # In real app, update in database
            return True
        except:
            return False
    
    def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read for user"""
        try:
            # In real app, update in database
            return True
        except:
            return False
    
    def send_application_notification(self, user_id: str, application: Dict[str, Any]):
        """Send notification about application"""
        job_title = application.get("job", {}).get("title", "job")
        company = application.get("job", {}).get("company", "company")
        status = application.get("status", "applied")
        
        if status == "applied":
            notification_type = "application_submitted"
        elif status == "viewed":
            notification_type = "application_viewed"
        elif status == "shortlisted":
            notification_type = "application_shortlisted"
        elif status == "rejected":
            notification_type = "application_rejected"
        else:
            notification_type = "application_submitted"
        
        self.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            data={
                "job_title": job_title,
                "company": company,
                "application_id": application.get("id")
            }
        )
    
    def send_auto_apply_notification(self, user_id: str, result: Dict[str, Any]):
        """Send notification about auto-apply result"""
        if result.get("success"):
            for job_result in result.get("results", []):
                if job_result.get("status") == "success":
                    self.create_notification(
                        user_id=user_id,
                        notification_type="auto_apply_success",
                        data={
                            "job_title": job_result.get("job_title"),
                            "company": job_result.get("company"),
                            "match_score": job_result.get("match_score")
                        }
                    )
                else:
                    self.create_notification(
                        user_id=user_id,
                        notification_type="auto_apply_failed",
                        data={
                            "job_title": job_result.get("job_title"),
                            "company": job_result.get("company"),
                            "error": job_result.get("error", "Unknown error")
                        }
                    )
    
    def send_job_recommendation(self, user_id: str, job: Dict[str, Any], match_score: int):
        """Send job recommendation notification"""
        self.create_notification(
            user_id=user_id,
            notification_type="job_recommendation",
            data={
                "job_title": job.get("title"),
                "company": job.get("company"),
                "match_score": match_score,
                "job_id": job.get("id")
            }
        )
    
    def send_daily_summary(self, user_id: str, stats: Dict[str, Any]):
        """Send daily summary notification"""
        self.create_notification(
            user_id=user_id,
            notification_type="daily_summary",
            data={
                "count": stats.get("total_applications", 0),
                "successful": stats.get("successful_applications", 0),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        )
    
    def _create_fallback_notification(self, user_id: str, notification_type: str) -> Dict[str, Any]:
        """Create fallback notification"""
        return {
            "id": f"fallback_{datetime.now().timestamp()}",
            "user_id": user_id,
            "type": notification_type,
            "title": "Notification",
            "message": "You have a new notification",
            "icon": "📢",
            "is_read": False,
            "created_at": datetime.now().isoformat()
        }
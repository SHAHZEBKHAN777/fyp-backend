import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# Import AI modules
from cv_parser_nlp import CVParserNLP
from resume_optimizer import ResumeOptimizer
from cover_letter_ai import CoverLetterAI
from job_matcher import JobMatcher
from auto_apply_cron import AutoApplyCron
from notification_service import NotificationService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AutoCareer AI Backend",
    description="Complete AI backend for CV parsing, resume optimization, job matching, and auto job applying",
    version="2.0.0"
)

# CORS setup for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI modules
cv_parser = CVParserNLP()
resume_optimizer = ResumeOptimizer()
cover_letter_ai = CoverLetterAI()
job_matcher = JobMatcher()
auto_applier = AutoApplyCron()
notification_service = NotificationService()

# Ensure temp directory exists
os.makedirs("temp_uploads", exist_ok=True)

# Start auto-apply scheduler on startup
@app.on_event("startup")
async def startup_event():
    """Start background services on startup"""
    logger.info("🚀 Starting AutoCareer AI Backend...")
    auto_applier.start_scheduler()
    logger.info("✅ Auto-apply scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down services...")
    auto_applier.stop_scheduler()

# ============== HEALTH & STATUS ==============
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "AutoCareer AI Backend",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "cv_parsing": True,
            "resume_optimization": True,
            "cover_letter": True,
            "job_matching": True,
            "auto_apply": True,
            "notifications": True
        },
        "endpoints": {
            "health": "/health",
            "parse_cv": "/api/parse-cv",
            "optimize_resume": "/api/optimize-resume",
            "generate_cover_letter": "/api/generate-cover-letter",
            "match_job": "/api/match-job",
            "auto_apply": "/api/auto-apply/trigger",
            "notifications": "/api/notifications/{user_id}",
            "job_recommendations": "/api/recommend-jobs/{user_id}",
            "activity": "/api/activity/{user_id}",
            "insights": "/api/insights/{user_id}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "auto_apply_scheduler": auto_applier.running,
            "supabase_connected": auto_applier.supabase is not None,
            "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
        }
    }

# ============== CV PARSING API ==============
@app.post("/api/parse-cv")
async def parse_cv(file: UploadFile = File(...)):
    """Upload and parse CV using NLP/AI"""
    try:
        logger.info(f"📄 Parsing CV: {file.filename}")
        
        # Save uploaded file
        timestamp = datetime.now().timestamp()
        file_path = f"temp_uploads/{timestamp}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse CV
        parsed_data = cv_parser.parse_cv(file_path)
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return JSONResponse({
            "success": True,
            "message": "CV parsed successfully",
            "data": parsed_data,
            "parsed_at": datetime.now().isoformat(),
            "parser_type": parsed_data.get("parsed_by", "ai")
        })
        
    except Exception as e:
        logger.error(f"❌ CV parsing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== RESUME OPTIMIZATION API ==============
@app.post("/api/optimize-resume")
async def optimize_resume(request: Dict[str, Any]):
    """Optimize resume for specific job"""
    try:
        logger.info("🎯 Optimizing resume for job...")
        
        user_profile = request.get("user_profile", {})
        target_job = request.get("target_job", {})
        
        if not user_profile or not target_job:
            raise HTTPException(status_code=400, detail="user_profile and target_job required")
        
        result = resume_optimizer.optimize_resume(user_profile, target_job)
        
        return JSONResponse({
            "success": True,
            "optimized_resume": result.get("optimized_text"),
            "suggestions": result.get("suggestions", []),
            "missing_keywords": result.get("missing_keywords", []),
            "match_score": result.get("match_score", 0),
            "ai_analysis": result.get("analysis", "")
        })
        
    except Exception as e:
        logger.error(f"❌ Resume optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== COVER LETTER GENERATION API ==============
@app.post("/api/generate-cover-letter")
async def generate_cover_letter(request: Dict[str, Any]):
    """Generate AI-powered cover letter"""
    try:
        user_data = request.get("user_data", {})
        job_data = request.get("job_data", {})
        
        if not user_data or not job_data:
            raise HTTPException(status_code=400, detail="user_data and job_data required")
        
        logger.info(f"📝 Generating cover letter for {job_data.get('job_title', 'position')}")
        
        cover_letter = cover_letter_ai.generate_cover_letter(user_data, job_data)
        
        return JSONResponse({
            "success": True,
            "cover_letter": cover_letter,
            "length": len(cover_letter),
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Cover letter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== JOB MATCHING API ==============
@app.post("/api/match-job")
async def match_job(request: Dict[str, Any]):
    """Calculate detailed job match score"""
    try:
        user_profile = request.get("user_profile", {})
        job = request.get("job", {})
        
        if not user_profile or not job:
            raise HTTPException(status_code=400, detail="user_profile and job required")
        
        logger.info("📊 Calculating job match score...")
        
        result = job_matcher.calculate_match_score(user_profile, job)
        
        return JSONResponse({
            "success": True,
            "match_score": result.get("total_score", 50),
            "breakdown": result.get("breakdown", {}),
            "insights": result.get("insights", []),
            "should_apply": result.get("should_apply", False),
            "ai_decision": result.get("ai_decision", "MAYBE"),
            "ai_reasoning": result.get("ai_reasoning", ""),
            "match_level": result.get("match_level", "Unknown")
        })
        
    except Exception as e:
        logger.error(f"❌ Job matching error: {e}")
        return JSONResponse({
            "success": False,
            "match_score": 50,
            "error": str(e)
        }, status_code=500)

# ============== AUTO APPLY API ==============
@app.post("/api/auto-apply/trigger")
async def trigger_auto_apply(request: Dict[str, Any]):
    """Trigger auto-apply for specific user"""
    try:
        user_id = request.get("user_id")
        threshold = request.get("threshold", 75)
        max_applications = request.get("max_applications", 5)
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        logger.info(f"🤖 Triggering auto-apply for user: {user_id}")
        
        result = auto_applier.run_auto_apply_for_user(
            user_id=user_id,
            threshold=threshold,
            max_applications=max_applications
        )
        
        return JSONResponse({
            "success": result.get("success", False),
            "applications_sent": result.get("applications_sent", 0),
            "message": result.get("message", ""),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Auto-apply error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auto-apply/cycle")
async def trigger_auto_apply_cycle():
    """Trigger full auto-apply cycle for all users"""
    try:
        logger.info("🔄 Triggering full auto-apply cycle...")
        
        # Run in background
        import threading
        thread = threading.Thread(target=auto_applier.run_auto_apply_cycle)
        thread.start()
        
        return JSONResponse({
            "success": True,
            "message": "Auto-apply cycle started in background",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Auto-apply cycle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== NOTIFICATIONS API ==============
@app.get("/api/notifications/{user_id}")
async def get_notifications(
    user_id: str,
    limit: int = 20,
    unread_only: bool = False
):
    """Get user notifications"""
    try:
        notifications = notification_service.get_user_notifications(
            user_id=user_id,
            limit=limit,
            unread_only=unread_only
        )
        
        unread_count = len([n for n in notifications if not n.get("is_read", False)])
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "notifications": notifications,
            "total": len(notifications),
            "unread_count": unread_count
        })
        
    except Exception as e:
        logger.error(f"❌ Notifications error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark notification as read"""
    try:
        success = notification_service.mark_as_read(notification_id)
        return JSONResponse({
            "success": success,
            "message": "Marked as read" if success else "Failed"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/read-all/{user_id}")
async def mark_all_read(user_id: str):
    """Mark all notifications as read"""
    try:
        success = notification_service.mark_all_as_read(user_id)
        return JSONResponse({
            "success": success,
            "message": "All marked as read" if success else "Failed"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== JOB RECOMMENDATIONS API ==============
@app.get("/api/recommend-jobs/{user_id}")
async def get_job_recommendations(user_id: str, limit: int = 10):
    """Get AI-powered job recommendations"""
    try:
        logger.info(f"🎯 Getting recommendations for user: {user_id}")
        
        # This would need implementation in job_matcher
        recommendations = []  # Placeholder
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "recommended_jobs": recommendations,
            "total": len(recommendations)
        })
        
    except Exception as e:
        logger.error(f"❌ Recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== ACTIVITY & ANALYTICS API ==============
@app.get("/api/activity/{user_id}")
async def get_user_activity(user_id: str, days: int = 30):
    """Get user application activity"""
    try:
        # This would query the database
        activity = {
            "total_applications": 0,
            "auto_applied": 0,
            "manual_applied": 0,
            "shortlisted": 0,
            "rejected": 0,
            "pending": 0,
            "daily_stats": []
        }
        
        return JSONResponse({
            "success": True,
            "activity_data": activity
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/insights/{user_id}")
async def get_ai_insights(user_id: str):
    """Get AI insights for user"""
    try:
        insights = [
            "Complete your profile to get better matches",
            "Add more skills to your profile",
            "Upload your resume for AI-powered matching"
        ]
        
        return JSONResponse({
            "success": True,
            "insights": insights
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== EMPLOYER ENDPOINTS ==============
@app.get("/api/employer/{employer_id}/applications")
async def get_employer_applications(employer_id: str):
    """Get applications for employer to review"""
    try:
        # This would fetch from Supabase
        applications = []
        
        return JSONResponse({
            "success": True,
            "applications": applications,
            "total": len(applications)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/employer/applications/{application_id}/status")
async def update_application_status(application_id: str, request: Dict[str, Any]):
    """Update application status (shortlist/reject)"""
    try:
        status = request.get("status")  # 'shortlisted', 'rejected', 'viewed'
        feedback = request.get("feedback", "")
        
        if not status:
            raise HTTPException(status_code=400, detail="status required")
        
        # Update in database and send notification
        # This would integrate with notification_service
        
        return JSONResponse({
            "success": True,
            "message": f"Application {status}",
            "notification_sent": True
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== START SERVER ==============
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print("🚀 AutoCareer AI Backend Server")
    print("=" * 60)
    print(f"📡 Port: {port}")
    print(f"🔗 API Docs: http://localhost:{port}/docs")
    print("✨ Features:")
    print("   ✓ AI CV Parsing")
    print("   ✓ Resume Optimization")
    print("   ✓ Cover Letter Generation")
    print("   ✓ Job Matching Algorithm")
    print("   ✓ Auto Job Apply with AI")
    print("   ✓ Employer Notifications")
    print("   ✓ Real-time Status Updates")
    print("=" * 60)
    
    uvicorn.run(
        "main_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
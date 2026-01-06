import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AutoCareer AI Backend",
    description="Complete AI backend for CV parsing, resume optimization, and auto job applying",
    version="1.0.0"
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

# ============== HEALTH & STATUS ==============
@app.get("/")
async def root():
    return {
        "service": "AutoCareer AI Backend",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "cv_parse": "/api/parse-cv",
            "optimize_resume": "/api/optimize-resume",
            "generate_cover_letter": "/api/generate-cover-letter",
            "match_score": "/api/match-job",
            "match_jobs": "/api/match-jobs/{user_id}",
            "activity_status": "/api/activity/{user_id}",
            "notifications": "/api/notifications/{user_id}",
            "job_recommendations": "/api/recommend-jobs/{user_id}"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ============== CV PARSING API ==============
@app.post("/api/parse-cv")
async def parse_cv_endpoint(file: UploadFile = File(...)):
    """Upload CV and extract information using NLP"""
    try:
        logger.info(f"Processing CV: {file.filename}")
        
        # Save uploaded file temporarily
        file_path = f"temp_uploads/{datetime.now().timestamp()}_{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse CV using NLP
        parsed_data = cv_parser.parse_cv(file_path)
        
        # Cleanup temp file
        os.remove(file_path)
        
        return JSONResponse({
            "success": True,
            "message": "CV parsed successfully",
            "data": parsed_data,
            "parsed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"CV parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"CV parsing failed: {str(e)}")

# ============== RESUME OPTIMIZATION API ==============
@app.post("/api/optimize-resume")
async def optimize_resume_endpoint(request_data: dict):
    """Optimize resume for specific job"""
    try:
        logger.info("Optimizing resume...")
        
        user_data = request_data.get("user_profile", {})
        target_job = request_data.get("target_job", {})
        
        optimization_result = resume_optimizer.optimize_resume(
            user_data=user_data,
            target_job=target_job
        )
        
        return JSONResponse({
            "success": True,
            "optimized_resume": optimization_result.get("optimized_text"),
            "suggestions": optimization_result.get("suggestions", []),
            "missing_keywords": optimization_result.get("missing_keywords", []),
            "match_score": optimization_result.get("match_score", 0),
            "ai_analysis": optimization_result.get("analysis", "")
        })
        
    except Exception as e:
        logger.error(f"Resume optimization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

# ============== COVER LETTER GENERATION API ==============
@app.post("/api/generate-cover-letter")
async def generate_cover_letter_endpoint(request_data: dict):
    """Generate AI-powered cover letter"""
    try:
        user_data = request_data.get("user_data", {})
        job_data = request_data.get("job_data", {})
        
        logger.info(f"Generating cover letter for {job_data.get('title', 'job')}")
        
        cover_letter = cover_letter_ai.generate_cover_letter(
            user_profile=user_data,
            job_details=job_data
        )
        
        return JSONResponse({
            "success": True,
            "cover_letter": cover_letter,
            "generated_at": datetime.now().isoformat(),
            "length_chars": len(cover_letter)
        })
        
    except Exception as e:
        logger.error(f"Cover letter generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")

# ============== JOB MATCH SCORE API ==============
@app.post("/api/match-job")
async def calculate_match_score_endpoint(request_data: dict):
    """Calculate match score between user and job"""
    try:
        logger.info("📊 Calculating job match score...")
        
        user_profile = request_data.get("user_profile", {})
        job = request_data.get("job", {})
        
        # Calculate match score
        match_result = job_matcher.calculate_match_score(user_profile, job)
        
        # Get the score
        match_score = match_result.get("total_score", 50)
        
        # Ensure numeric score
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
        
        match_score = max(0, min(100, float(match_score)))
        
        return JSONResponse({
            "success": True,
            "match_score": match_score,
            "match_details": match_result.get("breakdown", {}),
            "insights": match_result.get("insights", []),
            "message": f"Match score calculated: {match_score}%"
        })
        
    except Exception as e:
        logger.error(f"❌ Job match calculation error: {str(e)}")
        return JSONResponse({
            "success": False,
            "match_score": 50,
            "error": str(e)
        }, status_code=500)

# ============== JOB RECOMMENDATIONS API ==============
@app.get("/api/recommend-jobs/{user_id}")
async def recommend_jobs_endpoint(
    user_id: str,
    limit: int = 10
):
    """Get AI-recommended jobs for user"""
    try:
        logger.info(f"Getting recommendations for user: {user_id}")
        
        recommendations = job_matcher.get_recommended_jobs(
            user_id=user_id,
            limit=limit
        )
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "recommended_jobs": recommendations,
            "total_recommendations": len(recommendations),
            "recommendation_date": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Job recommendation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

# ============== NOTIFICATIONS API ==============
@app.get("/api/notifications/{user_id}")
async def get_notifications_endpoint(
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
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "notifications": notifications,
            "total": len(notifications),
            "unread_count": len([n for n in notifications if not n.get("is_read", False)])
        })
        
    except Exception as e:
        logger.error(f"Notifications error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Notifications failed: {str(e)}")

# ============== AUTO APPLY TRIGGER ==============
@app.post("/api/auto-apply/trigger")
async def trigger_auto_apply_endpoint(request_data: dict):
    """Trigger auto apply process"""
    try:
        user_id = request_data.get("user_id")
        threshold = request_data.get("threshold", 75)
        max_applications = request_data.get("max_applications", 5)
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")
        
        # Run auto apply
        result = await auto_applier.run_auto_apply_for_user(
            user_id=user_id,
            threshold=threshold,
            max_applications=max_applications
        )
        
        return JSONResponse({
            "success": True,
            "result": result,
            "triggered_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Auto apply trigger error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Auto apply failed: {str(e)}")

# ============== GET USER ACTIVITY ==============
@app.get("/api/activity/{user_id}")
async def get_activity_status(
    user_id: str,
    days: int = 30
):
    """Get user's application activity"""
    try:
        activity_data = auto_applier.get_user_activity(
            user_id=user_id,
            days=days
        )
        
        return JSONResponse({
            "success": True,
            "activity_data": activity_data,
            "retrieved_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Activity fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Activity fetch failed: {str(e)}")

# ============== GET AI INSIGHTS ==============
@app.get("/api/insights/{user_id}")
async def get_ai_insights_endpoint(user_id: str):
    """Get AI insights for user"""
    try:
        insights = auto_applier.generate_ai_insights(user_id)
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Insights error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Insights failed: {str(e)}")

# ============== START SERVER ==============
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    logger.info("=" * 50)
    logger.info("🚀 Starting AutoCareer AI Backend Server")
    logger.info(f"📡 Port: {port}")
    logger.info("💡 Available AI Features:")
    logger.info("   ✓ CV Parsing with NLP")
    logger.info("   ✓ Resume Optimization")
    logger.info("   ✓ AI Cover Letter Generation")
    logger.info("   ✓ Job Matching Algorithm")
    logger.info("   ✓ Auto Job Apply")
    logger.info("   ✓ AI Insights & Recommendations")
    logger.info("   ✓ Notifications System")
    logger.info("=" * 50)
    
    uvicorn.run(
        "main_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
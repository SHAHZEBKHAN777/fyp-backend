import os
import json
import numpy as np
from typing import Dict, List, Any, Tuple
import openai
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import logging

load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai = bool(self.api_key)
        
        if self.use_openai:
            openai.api_key = self.api_key
            logger.info("✅ OpenAI configured for job matching")
        else:
            logger.warning("⚠️  OPENAI_API_KEY not found, using basic matching")
        
        # Embedding cache to avoid repeated API calls
        self.embedding_cache = {}
        
        # Skill weights for different job categories
        self.skill_weights = {
            "technical": 0.4,
            "soft": 0.2,
            "experience": 0.25,
            "education": 0.15
        }
    
    def calculate_match_score(self, user_profile: Dict, job: Dict) -> Dict[str, Any]:
        """
        Calculate comprehensive match score using AI embeddings + GPT reasoning
        Returns detailed match analysis
        """
        try:
            # Step 1: Prepare text for embedding
            resume_text = self._prepare_resume_text(user_profile)
            job_text = self._prepare_job_text(job)
            
            # Step 2: Get embeddings and calculate semantic similarity
            if self.use_openai:
                resume_embedding = self._get_embedding(resume_text)
                job_embedding = self._get_embedding(job_text)
                similarity_score = self._calculate_similarity(resume_embedding, job_embedding)
            else:
                similarity_score = self._calculate_basic_match(user_profile, job)
            
            # Step 3: Get AI reasoning and decision
            ai_result = self._get_ai_decision(user_profile, job, similarity_score)
            
            # Step 4: Calculate skill-specific matches
            skill_match = self._calculate_skill_match(user_profile, job)
            experience_match = self._calculate_experience_match(user_profile, job)
            education_match = self._calculate_education_match(user_profile, job)
            
            # Step 5: Calculate weighted final score
            final_score = (
                similarity_score * 0.3 +
                ai_result.get("score", similarity_score) * 0.3 +
                skill_match * 0.2 +
                experience_match * 0.15 +
                education_match * 0.05
            )
            
            # Step 6: Generate insights
            insights = self._generate_comprehensive_insights(
                user_profile, job, final_score, skill_match, experience_match
            )
            
            # Determine if should apply
            should_apply = (
                ai_result.get("decision") == "YES" and 
                final_score >= 60
            )
            
            return {
                "total_score": round(final_score, 1),
                "breakdown": {
                    "semantic_similarity": round(similarity_score, 1),
                    "ai_reasoning_score": round(ai_result.get("score", 50), 1),
                    "skill_match": round(skill_match, 1),
                    "experience_match": round(experience_match, 1),
                    "education_match": round(education_match, 1)
                },
                "ai_decision": ai_result.get("decision", "MAYBE"),
                "ai_reasoning": ai_result.get("reasoning", ""),
                "insights": insights,
                "match_level": self._get_match_level(final_score),
                "should_apply": should_apply,
                "confidence": ai_result.get("confidence", "medium")
            }
            
        except Exception as e:
            logger.error(f"❌ Job matching error: {e}")
            return self._get_fallback_match()
    
    def _prepare_resume_text(self, profile: Dict) -> str:
        """Convert user profile to searchable text for embedding"""
        parts = []
        
        # Name and title
        name = profile.get("full_name") or f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
        if name:
            parts.append(f"Candidate: {name}")
        
        # Role
        role = profile.get("role", "")
        if role:
            parts.append(f"Role: {role}")
        
        # Skills
        skills = profile.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",")]
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")
        
        # Experience
        experience = profile.get("experience", [])
        if experience and isinstance(experience, list):
            exp_parts = []
            for exp in experience[:3]:
                if isinstance(exp, dict):
                    title = exp.get("title", "")
                    company = exp.get("company", "")
                    desc = exp.get("description", "")
                    if title:
                        exp_parts.append(f"{title} at {company}: {desc[:100]}")
            if exp_parts:
                parts.append("Experience: " + "; ".join(exp_parts))
        
        # Years of experience
        years = profile.get("experience_years", 0)
        if years:
            parts.append(f"Total Experience: {years} years")
        
        # Education
        education = profile.get("education", [])
        if education and isinstance(education, list):
            edu_parts = []
            for edu in education[:2]:
                if isinstance(edu, dict):
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    if degree:
                        edu_parts.append(f"{degree} from {institution}")
            if edu_parts:
                parts.append("Education: " + "; ".join(edu_parts))
        
        # Summary
        summary = profile.get("summary", "")
        if summary:
            parts.append(f"Summary: {summary[:200]}")
        
        # Location
        location = profile.get("location", "")
        if location:
            parts.append(f"Location: {location}")
        
        return " | ".join(parts) if parts else "No profile data available"
    
    def _prepare_job_text(self, job: Dict) -> str:
        """Convert job posting to searchable text for embedding"""
        parts = []
        
        # Job title
        title = job.get("job_title") or job.get("title", "")
        if title:
            parts.append(f"Position: {title}")
        
        # Company
        company = job.get("companies", {})
        if isinstance(company, dict):
            company_name = company.get("companyname", "")
        else:
            company_name = job.get("company", "")
        if company_name:
            parts.append(f"Company: {company_name}")
        
        # Description
        description = job.get("job_description") or job.get("description", "")
        if description:
            parts.append(f"Description: {description[:500]}")
        
        # Requirements
        requirements = job.get("job_requirements") or job.get("requirements", "")
        if requirements:
            parts.append(f"Requirements: {requirements[:300]}")
        
        # Location
        location = job.get("job_location") or job.get("location", "")
        if location:
            parts.append(f"Location: {location}")
        
        # Employment type
        emp_type = job.get("employment_type") or job.get("job_type", "")
        if emp_type:
            parts.append(f"Type: {emp_type}")
        
        # Salary
        salary = job.get("salary_range") or job.get("salary", "")
        if salary:
            parts.append(f"Salary: {salary}")
        
        return " | ".join(parts) if parts else "No job details available"
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text"""
        cache_key = hash(text[:200])
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        try:
            if self.use_openai and text.strip():
                response = openai.Embedding.create(
                    model="text-embedding-ada-002",
                    input=text[:8000]  # Limit length for API
                )
                embedding = response['data'][0]['embedding']
                self.embedding_cache[cache_key] = embedding
                return embedding
        except Exception as e:
            logger.error(f"Embedding error: {e}")
        
        # Fallback to random embedding
        return np.random.randn(1536).tolist()
    
    def _calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        try:
            emb1_np = np.array(emb1).reshape(1, -1)
            emb2_np = np.array(emb2).reshape(1, -1)
            similarity = cosine_similarity(emb1_np, emb2_np)[0][0]
            return float(similarity * 100)
        except:
            return 50.0
    
    def _calculate_basic_match(self, user_profile: Dict, job: Dict) -> float:
        """Basic skill-based matching without AI"""
        user_skills = self._extract_skills(user_profile)
        job_skills = self._extract_job_skills(job)
        
        if not job_skills:
            return 50.0
        
        matches = 0
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            for user_skill in user_skills:
                if job_skill_lower in user_skill.lower() or user_skill.lower() in job_skill_lower:
                    matches += 1
                    break
        
        return (matches / len(job_skills)) * 100
    
    def _calculate_skill_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate skill match percentage"""
        user_skills = self._extract_skills(user_profile)
        job_skills = self._extract_job_skills(job)
        
        if not job_skills:
            return 50.0
        
        matched = 0
        partial_matched = 0
        
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            found_exact = False
            found_partial = False
            
            for user_skill in user_skills:
                user_skill_lower = user_skill.lower()
                
                # Exact match
                if job_skill_lower == user_skill_lower:
                    found_exact = True
                    break
                
                # Partial match
                if job_skill_lower in user_skill_lower or user_skill_lower in job_skill_lower:
                    found_partial = True
            
            if found_exact:
                matched += 1
            elif found_partial:
                partial_matched += 0.5
        
        total_match = matched + partial_matched
        return (total_match / len(job_skills)) * 100
    
    def _calculate_experience_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate experience level match"""
        user_years = user_profile.get("experience_years", 0)
        
        # Try to extract required experience from job
        job_years = self._extract_required_experience(job)
        
        if job_years == 0:
            return 75.0  # No experience requirement specified
        
        if user_years >= job_years:
            # Extra points for more experience (up to 100)
            return min(100, 80 + (user_years - job_years) * 5)
        else:
            # Penalty for less experience
            ratio = user_years / job_years
            return ratio * 60  # Max 60 if doesn't meet requirement
    
    def _calculate_education_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate education level match"""
        user_education = user_profile.get("education", [])
        if not user_education:
            return 50.0
        
        # Check if user has relevant education
        job_description = job.get("job_description", "").lower()
        
        education_keywords = ["bachelor", "master", "phd", "degree", "computer science", 
                             "engineering", "information technology"]
        
        has_relevant = False
        for edu in user_education:
            if isinstance(edu, dict):
                degree = edu.get("degree", "").lower()
                for keyword in education_keywords:
                    if keyword in degree or keyword in job_description:
                        has_relevant = True
                        break
        
        return 85.0 if has_relevant else 60.0
    
    def _get_ai_decision(self, user_profile: Dict, job: Dict, similarity: float) -> Dict:
        """Use GPT to make final decision with detailed reasoning"""
        try:
            if not self.use_openai:
                return self._get_fallback_decision(similarity)
            
            # Prepare data
            user_name = user_profile.get("full_name") or "Candidate"
            skills = self._extract_skills(user_profile)
            experience = user_profile.get("experience_years", 0)
            summary = user_profile.get("summary", "")[:200]
            
            job_title = job.get("job_title") or job.get("title", "Position")
            job_desc = job.get("job_description") or job.get("description", "")
            job_reqs = job.get("job_requirements") or ""
            
            prompt = f"""You are an expert recruitment AI. Analyze this candidate-job match and provide a detailed assessment.

CANDIDATE PROFILE:
- Name: {user_name}
- Skills: {', '.join(skills[:15])}
- Experience: {experience} years
- Summary: {summary}

JOB DETAILS:
- Title: {job_title}
- Description: {job_desc[:500]}
- Requirements: {job_reqs[:300]}

Semantic Similarity Score: {similarity:.1f}%

Please analyze and return ONLY a valid JSON object with these exact fields:
{{
    "skill_match": number (0-100),
    "experience_match": number (0-100),
    "overall_score": number (0-100),
    "decision": "YES" or "NO" or "MAYBE",
    "confidence": "high" or "medium" or "low",
    "reasoning": "Detailed 2-3 sentence explanation of your decision",
    "key_strengths": ["strength1", "strength2"],
    "key_gaps": ["gap1", "gap2"],
    "recommendation": "Specific advice for the candidate"
}}

JSON:"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert AI recruitment assistant. Be honest, accurate, and helpful."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=15
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                result = json.loads(result_text[json_start:json_end])
                
                return {
                    "skill_match": float(result.get("skill_match", 50)),
                    "experience_match": float(result.get("experience_match", 50)),
                    "score": float(result.get("overall_score", similarity)),
                    "decision": result.get("decision", "MAYBE"),
                    "confidence": result.get("confidence", "medium"),
                    "reasoning": result.get("reasoning", "Analysis based on AI evaluation"),
                    "key_strengths": result.get("key_strengths", []),
                    "key_gaps": result.get("key_gaps", []),
                    "recommendation": result.get("recommendation", "")
                }
            
        except Exception as e:
            logger.error(f"AI decision error: {e}")
        
        return self._get_fallback_decision(similarity)
    
    def _get_fallback_decision(self, similarity: float) -> Dict:
        """Fallback decision based on similarity score"""
        if similarity >= 75:
            decision = "YES"
            confidence = "high"
        elif similarity >= 60:
            decision = "YES"
            confidence = "medium"
        elif similarity >= 45:
            decision = "MAYBE"
            confidence = "low"
        else:
            decision = "NO"
            confidence = "high"
        
        return {
            "skill_match": similarity,
            "experience_match": similarity,
            "score": similarity,
            "decision": decision,
            "confidence": confidence,
            "reasoning": f"Based on {similarity:.0f}% semantic similarity",
            "key_strengths": [],
            "key_gaps": [],
            "recommendation": "Review job requirements carefully"
        }
    
    def _generate_comprehensive_insights(self, user_profile: Dict, job: Dict, 
                                        final_score: float, skill_match: float,
                                        experience_match: float) -> List[str]:
        """Generate actionable insights for the user"""
        insights = []
        
        job_title = job.get("job_title") or "this position"
        
        # Overall match insight
        if final_score >= 80:
            insights.append(f"🌟 Excellent match for {job_title}! Your profile aligns very well.")
        elif final_score >= 65:
            insights.append(f"👍 Good match for {job_title}. You're a strong candidate.")
        elif final_score >= 50:
            insights.append(f"📊 Moderate match for {job_title}. Consider highlighting relevant experience.")
        else:
            insights.append(f"⚠️ Below average match for {job_title}. Review requirements carefully.")
        
        # Skill insights
        if skill_match < 60:
            missing_skills = self._identify_missing_skills(user_profile, job)
            if missing_skills:
                insights.append(f"📚 Consider developing: {', '.join(missing_skills[:3])}")
        else:
            insights.append("✅ Your skills align well with the job requirements.")
        
        # Experience insights
        if experience_match < 60:
            insights.append("⏳ Experience level is below requirements. Highlight relevant projects.")
        else:
            insights.append("💼 Your experience level matches the position well.")
        
        return insights[:5]
    
    def _extract_skills(self, profile: Dict) -> List[str]:
        """Extract skills from user profile"""
        skills = []
        
        if profile.get("skills"):
            if isinstance(profile["skills"], list):
                skills = profile["skills"]
            elif isinstance(profile["skills"], str):
                skills = [s.strip() for s in profile["skills"].split(",")]
        
        if not skills:
            skills = ["Communication", "Problem Solving", "Teamwork"]
        
        return list(set(skills))
    
    def _extract_job_skills(self, job: Dict) -> List[str]:
        """Extract required skills from job posting"""
        skills = []
        
        # Check requirements field
        requirements = job.get("job_requirements") or job.get("requirements", "")
        if isinstance(requirements, str):
            # Extract skills from requirements text
            common_skills = [
                "Python", "Java", "JavaScript", "React", "Angular", "Vue", 
                "Node.js", "Flutter", "Dart", "Swift", "Kotlin", "SQL",
                "Docker", "Kubernetes", "AWS", "Azure", "Git", "REST API",
                "GraphQL", "Machine Learning", "AI", "Data Analysis"
            ]
            for skill in common_skills:
                if skill.lower() in requirements.lower():
                    skills.append(skill)
        
        # Also check description
        description = job.get("job_description") or job.get("description", "")
        if isinstance(description, str):
            for skill in common_skills:
                if skill.lower() in description.lower() and skill not in skills:
                    skills.append(skill)
        
        if not skills:
            skills = ["Relevant technical skills"]
        
        return list(set(skills))
    
    def _extract_required_experience(self, job: Dict) -> int:
        """Extract required years of experience from job posting"""
        import re
        
        text = f"{job.get('job_description', '')} {job.get('job_requirements', '')}"
        
        # Look for patterns like "X+ years", "X years experience"
        patterns = [
            r'(\d+)\+?\s*(?:years|yrs)(?:\s*of)?\s*experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*(?:years|yrs)',
            r'(\d+)\s*-\s*\d+\s*(?:years|yrs)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                return int(matches[0])
        
        return 0
    
    def _identify_missing_skills(self, user_profile: Dict, job: Dict) -> List[str]:
        """Identify skills missing from user profile"""
        user_skills = [s.lower() for s in self._extract_skills(user_profile)]
        job_skills = self._extract_job_skills(job)
        
        missing = []
        for skill in job_skills:
            skill_lower = skill.lower()
            if not any(skill_lower in us or us in skill_lower for us in user_skills):
                missing.append(skill)
        
        return missing[:5]
    
    def _get_match_level(self, score: float) -> str:
        """Get descriptive match level"""
        if score >= 85:
            return "Excellent Match"
        elif score >= 70:
            return "Strong Match"
        elif score >= 55:
            return "Good Match"
        elif score >= 40:
            return "Fair Match"
        else:
            return "Weak Match"
    
    def _get_fallback_match(self) -> Dict[str, Any]:
        """Ultimate fallback match result"""
        return {
            "total_score": 50.0,
            "breakdown": {
                "semantic_similarity": 50.0,
                "ai_reasoning_score": 50.0,
                "skill_match": 50.0,
                "experience_match": 50.0,
                "education_match": 50.0
            },
            "ai_decision": "MAYBE",
            "ai_reasoning": "Unable to perform detailed analysis. Using default score.",
            "insights": ["Complete your profile for better matching", "Add more skills to improve matches"],
            "match_level": "Unknown",
            "should_apply": False,
            "confidence": "low"
        }
import json
import re
from typing import Dict, List, Any
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class JobMatcher:
    def __init__(self):
        self.skill_weight = 0.4
        self.experience_weight = 0.3
        self.education_weight = 0.15
        self.location_weight = 0.1
        self.salary_weight = 0.05
        
        # Predefined skill categories
        self.skill_categories = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'swift', 'kotlin'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask'],
            'mobile': ['flutter', 'react native', 'android', 'ios', 'swift', 'kotlin', 'dart'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'firebase'],
            'devops': ['aws', 'azure', 'docker', 'kubernetes', 'jenkins', 'git', 'ci/cd'],
            'data': ['machine learning', 'ai', 'data analysis', 'pandas', 'numpy', 'tensorflow'],
            'soft_skills': ['communication', 'teamwork', 'leadership', 'problem solving', 'creativity']
        }
    
    def calculate_match_score(self, user_profile: Dict, job: Dict) -> Dict[str, Any]:
        """Calculate comprehensive match score between user and job"""
        try:
            # Calculate individual component scores
            skill_score = self._calculate_skill_match(user_profile, job)
            experience_score = self._calculate_experience_match(user_profile, job)
            education_score = self._calculate_education_match(user_profile, job)
            location_score = self._calculate_location_match(user_profile, job)
            salary_score = self._calculate_salary_match(user_profile, job)
            
            # Calculate weighted total score
            total_score = (
                skill_score * self.skill_weight +
                experience_score * self.experience_weight +
                education_score * self.education_weight +
                location_score * self.location_weight +
                salary_score * self.salary_weight
            )
            
            # Generate insights
            insights = self._generate_insights(
                user_profile, job,
                skill_score, experience_score, education_score,
                location_score, salary_score
            )
            
            return {
                "total_score": total_score,
                "breakdown": {
                    "skills": skill_score,
                    "experience": experience_score,
                    "education": education_score,
                    "location": location_score,
                    "salary": salary_score
                },
                "weights": {
                    "skills": self.skill_weight,
                    "experience": self.experience_weight,
                    "education": self.education_weight,
                    "location": self.location_weight,
                    "salary": self.salary_weight
                },
                "insights": insights,
                "match_level": self._get_match_level(total_score)
            }
            
        except Exception as e:
            print(f"Job matching error: {e}")
            return self._get_fallback_match()
    
    def _calculate_skill_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate skill matching score"""
        user_skills = self._extract_user_skills(user_profile)
        job_skills = self._extract_job_skills(job)
        
        if not job_skills:
            return 50.0
        
        # Calculate similarity
        matches = 0
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            
            # Check exact match
            if any(job_skill_lower == user_skill.lower() for user_skill in user_skills):
                matches += 1
            # Check partial match
            elif any(job_skill_lower in user_skill.lower() or 
                    user_skill.lower() in job_skill_lower 
                    for user_skill in user_skills):
                matches += 0.7
            # Check category match
            elif self._check_skill_category(job_skill_lower, user_skills):
                matches += 0.5
        
        score = (matches / len(job_skills)) * 100
        return min(max(score, 0), 100)
    
    def _extract_user_skills(self, user_profile: Dict) -> List[str]:
        """Extract skills from user profile"""
        skills = []
        
        if user_profile.get('skills'):
            if isinstance(user_profile['skills'], list):
                skills.extend(user_profile['skills'])
            elif isinstance(user_profile['skills'], str):
                skills.extend([s.strip() for s in user_profile['skills'].split(',')])
        
        # Extract from experience
        if user_profile.get('experience'):
            for exp in user_profile['experience']:
                if isinstance(exp, dict) and exp.get('description'):
                    desc = exp['description'].lower()
                    # Look for common skills in description
                    for category, cat_skills in self.skill_categories.items():
                        for skill in cat_skills:
                            if skill in desc and skill not in skills:
                                skills.append(skill)
        
        # Add default skills if none
        if not skills:
            skills = ['problem solving', 'communication', 'teamwork']
        
        return [s.lower() for s in skills]
    
    def _extract_job_skills(self, job: Dict) -> List[str]:
        """Extract required skills from job"""
        skills = []
        
        # From description
        if job.get('description'):
            desc = job['description'].lower()
            
            # Look for skills in common categories
            for category, cat_skills in self.skill_categories.items():
                for skill in cat_skills:
                    if skill in desc and skill not in skills:
                        skills.append(skill)
            
            # Extract from requirements section
            requirement_sections = ['requirements:', 'qualifications:', 'must have:']
            for section in requirement_sections:
                if section in desc:
                    start = desc.find(section) + len(section)
                    end = desc.find('\n', start)
                    if end == -1:
                        end = start + 200
                    
                    req_text = desc[start:end]
                    # Simple extraction of capitalized words (potential skills)
                    words = re.findall(r'\b[A-Z][a-z]+\b', job['description'])
                    for word in words:
                        if len(word) > 3 and word.lower() not in skills:
                            for cat_skills in self.skill_categories.values():
                                if word.lower() in cat_skills:
                                    skills.append(word.lower())
                                    break
        
        # From title
        if job.get('title'):
            title = job['title'].lower()
            for cat_skills in self.skill_categories.values():
                for skill in cat_skills:
                    if skill in title and skill not in skills:
                        skills.append(skill)
        
        return list(set(skills))[:15]
    
    def _check_skill_category(self, job_skill: str, user_skills: List[str]) -> bool:
        """Check if user has skills in same category"""
        # Find category of job skill
        job_category = None
        for category, skills in self.skill_categories.items():
            if job_skill in skills:
                job_category = category
                break
        
        if not job_category:
            return False
        
        # Check if user has any skill in same category
        for user_skill in user_skills:
            if user_skill in self.skill_categories.get(job_category, []):
                return True
        
        return False
    
    def _calculate_experience_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate experience matching score"""
        user_exp = user_profile.get('experience_years', 0)
        
        # Try to extract required experience from job
        job_exp_required = 0
        if job.get('description'):
            desc = job['description'].lower()
            
            # Look for experience patterns
            exp_patterns = [
                r'(\d+)\+?\s*years?',
                r'(\d+)\+?\s*yrs?',
                r'experience.*?(\d+).*?years?',
                r'(\d+).*?years?.*?experience'
            ]
            
            for pattern in exp_patterns:
                match = re.search(pattern, desc)
                if match:
                    try:
                        job_exp_required = int(match.group(1))
                        break
                    except:
                        continue
        
        if job_exp_required == 0:
            return 75.0  # Default score if no experience requirement
        
        if user_exp >= job_exp_required:
            return 100.0
        elif user_exp > 0:
            # Proportional score
            score = (user_exp / job_exp_required) * 100
            return min(score, 100)
        else:
            return 30.0
    
    def _calculate_education_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate education matching score"""
        user_education = user_profile.get('education', [])
        
        if not user_education:
            return 50.0
        
        # Check for degree requirements
        if job.get('description'):
            desc = job['description'].lower()
            
            degree_keywords = [
                'bachelor', "bachelor's", 'bs', 'bsc', 'ba',
                'master', "master's", 'ms', 'msc', 'ma',
                'phd', 'doctorate', 'mba'
            ]
            
            # Check if any degree is mentioned in job description
            for keyword in degree_keywords:
                if keyword in desc:
                    # Check if user has similar education
                    for edu in user_education:
                        if isinstance(edu, dict):
                            degree = edu.get('degree', '').lower()
                            if keyword in degree:
                                return 100.0
            
            # No specific degree requirement found
            return 80.0
        
        return 70.0
    
    def _calculate_location_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate location matching score"""
        user_location = user_profile.get('location', '').lower()
        job_location = job.get('location', '').lower()
        
        if not user_location or not job_location:
            return 50.0
        
        # Check for remote work
        if 'remote' in job_location or 'anywhere' in job_location:
            return 100.0
        
        # Check exact match
        if user_location == job_location:
            return 100.0
        
        # Check partial match (city, country)
        user_parts = set(user_location.split())
        job_parts = set(job_location.split())
        
        if user_parts.intersection(job_parts):
            return 80.0
        
        return 30.0
    
    def _calculate_salary_match(self, user_profile: Dict, job: Dict) -> float:
        """Calculate salary matching score"""
        user_expected = user_profile.get('expected_salary', 0)
        job_min = job.get('salary_min', 0)
        job_max = job.get('salary_max', 0)
        
        if user_expected <= 0 or job_max <= 0:
            return 50.0
        
        if job_min <= user_expected <= job_max:
            return 100.0
        elif user_expected < job_min:
            # User expects less than minimum - good for employer
            return 90.0
        else:
            # User expects more than maximum
            ratio = job_max / user_expected
            return max(30.0, ratio * 100)
    
    def _generate_insights(self, user_profile: Dict, job: Dict,
                          skill_score: float, exp_score: float,
                          edu_score: float, loc_score: float,
                          salary_score: float) -> List[str]:
        """Generate insights based on match scores"""
        insights = []
        
        job_title = job.get('title', 'this position')
        
        # Overall match insight
        total_score = (
            skill_score * self.skill_weight +
            exp_score * self.experience_weight +
            edu_score * self.education_weight +
            loc_score * self.location_weight +
            salary_score * self.salary_weight
        )
        
        if total_score >= 80:
            insights.append(f"Excellent match for {job_title}! You meet most requirements.")
        elif total_score >= 60:
            insights.append(f"Good match for {job_title}. Consider applying.")
        else:
            insights.append(f"Limited match for {job_title}. Consider other opportunities.")
        
        # Skill insights
        if skill_score < 60:
            job_skills = self._extract_job_skills(job)
            insights.append(f"Add these skills to improve match: {', '.join(job_skills[:3])}")
        
        # Experience insights
        user_exp = user_profile.get('experience_years', 0)
        if exp_score < 70 and user_exp < 2:
            insights.append("Highlight projects and achievements to compensate for experience.")
        
        # Location insights
        if loc_score < 50:
            insights.append("Consider remote opportunities or relocation.")
        
        # Salary insights
        user_expected = user_profile.get('expected_salary', 0)
        job_max = job.get('salary_max', 0)
        if salary_score < 50 and user_expected > job_max > 0:
            insights.append(f"Expected salary (${user_expected:,}) exceeds range (up to ${job_max:,})")
        
        return insights[:5]
    
    def _get_match_level(self, score: float) -> str:
        """Get match level description"""
        if score >= 90:
            return "Perfect Match"
        elif score >= 75:
            return "Strong Match"
        elif score >= 60:
            return "Good Match"
        elif score >= 40:
            return "Fair Match"
        else:
            return "Weak Match"
    
    def get_recommended_jobs(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get AI-recommended jobs for user"""
        # This would typically query database
        # For now, return sample structure
        return [
            {
                "job_id": "1",
                "title": "Senior Flutter Developer",
                "company": "Tech Corp",
                "match_score": 92,
                "reason": "Matches your Flutter and mobile development skills",
                "salary_range": "$80,000 - $120,000",
                "location": "Remote"
            },
            {
                "job_id": "2",
                "title": "Mobile App Developer",
                "company": "Startup XYZ",
                "match_score": 85,
                "reason": "Strong alignment with your experience",
                "salary_range": "$70,000 - $100,000",
                "location": "New York"
            }
        ]
    
    def _get_fallback_match(self) -> Dict[str, Any]:
        """Fallback match result"""
        return {
            "total_score": 50,
            "breakdown": {
                "skills": 50,
                "experience": 50,
                "education": 50,
                "location": 50,
                "salary": 50
            },
            "weights": self.__dict__.get('weights', {}),
            "insights": ["Unable to calculate detailed match score"],
            "match_level": "Unknown"
        }
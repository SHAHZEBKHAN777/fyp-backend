import re
from typing import Dict, List, Any
from difflib import SequenceMatcher

class ResumeOptimizer:
    def __init__(self):
        self.common_skills = [
            "Python", "Java", "JavaScript", "C++", "C#", "PHP", "SQL", "NoSQL",
            "React", "Angular", "Vue", "Node.js", "Express", "Django", "Flask",
            "AWS", "Azure", "Docker", "Kubernetes", "Git", "REST API", "GraphQL",
            "Machine Learning", "AI", "Data Analysis", "Agile", "Scrum"
        ]
        
        self.action_verbs = [
            "developed", "created", "implemented", "designed", "built",
            "managed", "led", "improved", "optimized", "increased",
            "reduced", "solved", "automated", "launched", "coordinated"
        ]
        
        self.quantifiable_words = [
            "increased", "decreased", "reduced", "improved", "saved",
            "achieved", "delivered", "completed", "managed", "led"
        ]
    
    def optimize_resume(self, user_data: Dict, target_job: Dict) -> Dict[str, Any]:
        """Optimize resume for specific job"""
        try:
            # Extract job requirements
            job_requirements = self._extract_requirements(target_job)
            
            # Analyze current resume/skills
            current_skills = self._extract_user_skills(user_data)
            
            # Calculate match score
            match_score = self._calculate_match_score(current_skills, job_requirements)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(
                user_data, 
                current_skills, 
                job_requirements, 
                match_score
            )
            
            # Generate optimized resume text
            optimized_text = self._generate_optimized_text(user_data, job_requirements)
            
            # Identify missing keywords
            missing_keywords = self._identify_missing_keywords(
                current_skills, 
                job_requirements
            )
            
            return {
                "success": True,
                "match_score": match_score,
                "suggestions": suggestions,
                "missing_keywords": missing_keywords,
                "optimized_text": optimized_text,
                "analysis": self._generate_analysis(user_data, target_job, match_score)
            }
            
        except Exception as e:
            print(f"Resume optimization error: {e}")
            return self._get_fallback_optimization(user_data, target_job)
    
    def _extract_requirements(self, job: Dict) -> List[str]:
        """Extract requirements from job description"""
        requirements = []
        
        # Extract from job description
        if job.get('description'):
            desc = job['description'].lower()
            
            # Look for common requirements
            requirement_phrases = [
                "requirements:", "qualifications:", "must have:", 
                "should have:", "required:", "looking for:"
            ]
            
            for phrase in requirement_phrases:
                if phrase in desc:
                    start_idx = desc.find(phrase) + len(phrase)
                    # Extract next 500 characters
                    req_text = desc[start_idx:start_idx + 500]
                    # Split into requirements
                    lines = req_text.split('\n')
                    for line in lines[:10]:  # Take first 10 lines
                        line = line.strip()
                        if line and len(line.split()) > 1:
                            requirements.append(line)
            
            # If no specific requirements section, extract keywords
            if not requirements:
                for skill in self.common_skills:
                    if skill.lower() in desc:
                        requirements.append(skill)
        
        # Add job title and type
        if job.get('title'):
            requirements.append(job['title'])
        if job.get('job_type'):
            requirements.append(job['job_type'])
        
        return list(set(requirements))[:20]  # Remove duplicates, limit to 20
    
    def _extract_user_skills(self, user_data: Dict) -> List[str]:
        """Extract skills from user data"""
        skills = []
        
        # Extract from skills field
        if user_data.get('skills'):
            if isinstance(user_data['skills'], list):
                skills.extend(user_data['skills'])
            elif isinstance(user_data['skills'], str):
                skills.extend([s.strip() for s in user_data['skills'].split(',')])
        
        # Extract from experience
        if user_data.get('experience'):
            for exp in user_data['experience']:
                if isinstance(exp, dict) and exp.get('description'):
                    desc = exp['description'].lower()
                    for skill in self.common_skills:
                        if skill.lower() in desc and skill not in skills:
                            skills.append(skill)
        
        # Add default skills if none found
        if not skills:
            skills = ["Problem Solving", "Communication", "Teamwork"]
        
        return list(set(skills))[:15]
    
    def _calculate_match_score(self, user_skills: List[str], job_requirements: List[str]) -> int:
        """Calculate match score between user skills and job requirements"""
        if not job_requirements:
            return 50
        
        user_skills_lower = [s.lower() for s in user_skills]
        job_reqs_lower = [r.lower() for r in job_requirements]
        
        matches = 0
        for req in job_reqs_lower:
            # Check direct match
            if any(req in skill or skill in req for skill in user_skills_lower):
                matches += 1
            # Check partial match
            elif any(self._similarity(req, skill) > 0.6 for skill in user_skills_lower):
                matches += 0.5
        
        score = int((matches / len(job_reqs_lower)) * 100)
        return min(max(score, 0), 100)
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity"""
        return SequenceMatcher(None, a, b).ratio()
    
    def _generate_suggestions(self, user_data: Dict, user_skills: List[str], 
                            job_requirements: List[str], match_score: int) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        
        # Add general suggestions based on match score
        if match_score < 60:
            suggestions.append("Your resume needs significant optimization for this role.")
            suggestions.append("Consider adding more relevant skills and experience.")
        
        # Check for quantifiable achievements
        has_quantifiable = False
        if user_data.get('experience'):
            for exp in user_data['experience']:
                if isinstance(exp, dict) and exp.get('description'):
                    desc = exp['description'].lower()
                    for verb in self.quantifiable_words:
                        if verb in desc:
                            has_quantifiable = True
                            break
        
        if not has_quantifiable:
            suggestions.append("Add quantifiable achievements (e.g., 'Increased efficiency by 30%')")
        
        # Check skill alignment
        missing_skills = self._identify_missing_keywords(user_skills, job_requirements)
        if missing_skills:
            suggestions.append(f"Add these keywords: {', '.join(missing_skills[:3])}")
        
        # Formatting suggestions
        suggestions.append("Use bullet points for experience descriptions")
        suggestions.append("Keep resume to 1-2 pages maximum")
        suggestions.append("Include relevant certifications if any")
        
        return suggestions[:5]
    
    def _identify_missing_keywords(self, user_skills: List[str], job_requirements: List[str]) -> List[str]:
        """Identify missing keywords from job requirements"""
        missing = []
        user_skills_lower = [s.lower() for s in user_skills]
        
        for req in job_requirements:
            req_lower = req.lower()
            # Check if requirement is in user skills
            if not any(req_lower in skill or skill in req_lower or 
                      self._similarity(req_lower, skill) > 0.7 
                      for skill in user_skills_lower):
                missing.append(req)
        
        return missing[:10]
    
    def _generate_optimized_text(self, user_data: Dict, job_requirements: List[str]) -> str:
        """Generate optimized resume text"""
        optimized = []
        
        # Summary/Objective
        if user_data.get('summary'):
            optimized.append(f"SUMMARY\n{user_data['summary']}")
        else:
            optimized.append("SUMMARY\nResults-driven professional seeking new opportunities.")
        
        optimized.append("")
        
        # Skills section
        optimized.append("SKILLS")
        skills_text = ""
        if user_data.get('skills'):
            if isinstance(user_data['skills'], list):
                skills_text = ', '.join(user_data['skills'][:10])
            else:
                skills_text = str(user_data['skills'])
        
        # Add missing keywords from job requirements
        user_skills = self._extract_user_skills(user_data)
        missing = self._identify_missing_keywords(user_skills, job_requirements)
        
        if missing:
            skills_text += f" | {', '.join(missing[:5])}"
        
        optimized.append(skills_text)
        optimized.append("")
        
        # Experience section
        optimized.append("EXPERIENCE")
        if user_data.get('experience'):
            for exp in user_data['experience'][:3]:
                if isinstance(exp, dict):
                    title = exp.get('title', 'Position')
                    company = exp.get('company', 'Company')
                    desc = exp.get('description', 'Responsibilities')
                    
                    # Optimize description with action verbs
                    optimized_desc = self._optimize_description(desc, job_requirements)
                    
                    optimized.append(f"{title} at {company}")
                    optimized.append(f"  • {optimized_desc}")
        
        # Education
        optimized.append("")
        optimized.append("EDUCATION")
        if user_data.get('education'):
            for edu in user_data['education'][:2]:
                if isinstance(edu, dict):
                    degree = edu.get('degree', 'Degree')
                    institution = edu.get('institution', 'Institution')
                    year = edu.get('year', 'Year')
                    optimized.append(f"{degree} - {institution} ({year})")
        
        return '\n'.join(optimized)
    
    def _optimize_description(self, description: str, job_requirements: List[str]) -> str:
        """Optimize experience description"""
        desc_lower = description.lower()
        
        # Start with action verb if not already
        if not any(desc_lower.startswith(verb) for verb in self.action_verbs):
            for verb in self.action_verbs:
                if verb in desc_lower:
                    # Move verb to beginning
                    words = desc_lower.split()
                    if verb in words:
                        idx = words.index(verb)
                        words = [verb.capitalize()] + words[idx+1:] + words[:idx]
                        return ' '.join(words)
        
        # Ensure first word is capitalized
        if description:
            return description[0].upper() + description[1:]
        
        return description
    
    def _generate_analysis(self, user_data: Dict, job: Dict, match_score: int) -> str:
        """Generate analysis text"""
        analysis = []
        
        job_title = job.get('title', 'this position')
        company = job.get('company', 'the company')
        
        analysis.append(f"Analysis for {job_title} at {company}:")
        analysis.append(f"Current Match Score: {match_score}%")
        
        if match_score >= 80:
            analysis.append("Your resume is well-aligned with this position.")
            analysis.append("Focus on highlighting your most relevant achievements.")
        elif match_score >= 60:
            analysis.append("Good alignment, but room for improvement.")
            analysis.append("Consider adding more specific keywords from the job description.")
        else:
            analysis.append("Significant optimization needed.")
            analysis.append("Tailor your resume specifically for this role.")
        
        # Years of experience analysis
        exp_years = user_data.get('experience_years', 0)
        if exp_years >= 5:
            analysis.append(f"Your {exp_years} years of experience is a strong asset.")
        elif exp_years >= 2:
            analysis.append(f"Your {exp_years} years of experience is adequate.")
        else:
            analysis.append("Consider highlighting projects and skills over experience.")
        
        return '\n'.join(analysis)
    
    def _get_fallback_optimization(self, user_data: Dict, target_job: Dict) -> Dict[str, Any]:
        """Fallback optimization result"""
        return {
            "success": True,
            "match_score": 50,
            "suggestions": [
                "Customize your resume for the specific job",
                "Add quantifiable achievements",
                "Include relevant keywords from job description"
            ],
            "missing_keywords": ["Relevant skills"],
            "optimized_text": "Optimized resume text will appear here",
            "analysis": "AI analysis will be generated here"
        }
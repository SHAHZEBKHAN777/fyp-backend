import os
import json
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv

load_dotenv()

class CoverLetterAI:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai = bool(self.api_key)
        
        if self.use_openai:
            openai.api_key = self.api_key
            print("✅ OpenAI configured for cover letters")
        else:
            print("⚠️  OPENAI_API_KEY not found, using template cover letters")
    
    def generate_cover_letter(self, user_profile: Dict[str, Any], 
                             job_details: Dict[str, Any]) -> str:
        """
        Generate cover letter using AI
        """
        try:
            # Try AI generation first
            if self.use_openai:
                ai_letter = self._generate_with_openai(user_profile, job_details)
                if ai_letter and len(ai_letter) > 150:
                    return ai_letter
            
            # Fallback to template
            return self._generate_with_template(user_profile, job_details)
            
        except Exception as e:
            print(f"❌ Cover letter error: {e}")
            return self._generate_ultimate_fallback(user_profile, job_details)
    
    def _generate_with_openai(self, user_profile: Dict, job: Dict) -> Optional[str]:
        """Generate with OpenAI"""
        try:
            # Prepare data
            name = user_profile.get("name") or user_profile.get("full_name") or "Applicant"
            skills = user_profile.get("skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",")]
            
            experience = user_profile.get("experience_years", 0)
            job_title = job.get("title") or job.get("job_title") or "the position"
            company = job.get("company") or "your company"
            job_desc = job.get("description") or job.get("job_description") or ""
            
            prompt = f"""Write a professional, compelling cover letter for this job application.

CANDIDATE:
- Name: {name}
- Key Skills: {', '.join(skills[:8])}
- Experience: {experience} years

JOB:
- Title: {job_title}
- Company: {company}
- Description: {job_desc[:400]}

REQUIREMENTS:
1. Address to "Hiring Manager"
2. Show genuine enthusiasm for {company}
3. Highlight relevant skills: {', '.join(skills[:5])}
4. Include 2-3 specific contributions
5. Professional but warm tone
6. 250-350 words
7. End with professional closing and signature

COVER LETTER:"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert cover letter writer. Create personalized, effective letters."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                timeout=15
            )
            
            letter = response.choices[0].message.content.strip()
            
            # Ensure proper format
            if not letter.startswith(('Dear', 'Hello')):
                letter = f"Dear Hiring Manager,\n\n{letter}"
            
            if not letter.strip().endswith(name):
                letter = f"{letter}\n\nSincerely,\n{name}"
            
            return letter
            
        except Exception as e:
            print(f"⚠️ OpenAI generation failed: {e}")
            return None
    
    def _generate_with_template(self, user_profile: Dict, job: Dict) -> str:
        """Generate with smart template"""
        name = user_profile.get("name") or user_profile.get("full_name") or "Applicant"
        skills = user_profile.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",")]
        
        experience = user_profile.get("experience_years", 0)
        job_title = job.get("title") or job.get("job_title") or "the position"
        company = job.get("company") or "your company"
        
        # Select template based on experience
        if experience >= 5:
            template = self._get_senior_template()
        elif experience >= 2:
            template = self._get_mid_template()
        else:
            template = self._get_junior_template()
        
        # Fill template
        letter = template.format(
            name=name,
            job_title=job_title,
            company=company,
            skills=", ".join(skills[:5]),
            experience=experience
        )
        
        return letter
    
    def _get_senior_template(self) -> str:
        return """Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}. With {experience} years of comprehensive experience and expertise in {skills}, I am confident in my ability to make immediate and significant contributions to your team.

Throughout my career, I have consistently delivered high-impact results:
• Led complex projects from conception to successful delivery
• Mentored junior team members and improved overall team productivity
• Implemented solutions that increased efficiency and reduced costs

My technical expertise includes {skills}, and I stay current with industry trends and best practices. I am particularly drawn to {company} because of your reputation for innovation and excellence in the field.

I am excited about the opportunity to bring my leadership experience and technical skills to {company}. Thank you for considering my application.

Sincerely,
{name}"""
    
    def _get_mid_template(self) -> str:
        return """Dear Hiring Manager,

I am excited to apply for the {job_title} position at {company}. With {experience} years of hands-on experience and strong skills in {skills}, I believe I can contribute effectively to your team.

Key highlights of my experience:
• Successfully delivered multiple projects using cutting-edge technologies
• Collaborated with cross-functional teams to achieve business goals
• Continuously improved processes and adopted best practices

I am proficient in {skills} and always eager to learn and grow. I have followed {company}'s work and am impressed by your innovative approach.

I would welcome the opportunity to discuss how my skills align with your needs. Thank you for your consideration.

Best regards,
{name}"""
    
    def _get_junior_template(self) -> str:
        return """Dear Hiring Manager,

I am writing to apply for the {job_title} position at {company}. As an enthusiastic professional with training in {skills}, I am eager to launch my career with an innovative company like yours.

During my academic and project work, I have:
• Developed strong foundations in {skills}
• Completed projects demonstrating my ability to learn quickly
• Collaborated effectively in team environments

I am particularly drawn to {company} because of your reputation for excellence. I am a quick learner, highly motivated, and ready to contribute from day one.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team.

Sincerely,
{name}"""
    
    def _generate_ultimate_fallback(self, user_profile: Dict, job: Dict) -> str:
        """Ultimate fallback"""
        name = user_profile.get("name") or user_profile.get("full_name") or "Applicant"
        job_title = job.get("title") or job.get("job_title") or "the position"
        company = job.get("company") or "your company"
        
        return f"""Dear Hiring Manager,

I am writing to apply for the {job_title} position at {company}. With my skills and experience, I believe I would be a valuable addition to your team.

I am enthusiastic about this opportunity and eager to contribute to {company}'s success.

Thank you for considering my application.

Sincerely,
{name}"""
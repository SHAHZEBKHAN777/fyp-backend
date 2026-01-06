import os
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv
import random

# Try to import OpenAI, but provide fallback
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

load_dotenv()

class CoverLetterAI:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai = OPENAI_AVAILABLE and self.api_key
        
        if self.use_openai:
            openai.api_key = self.api_key
            print("✅ OpenAI configured for cover letters")
        else:
            print("⚠️  Using template-based cover letters (add OPENAI_API_KEY for AI)")
        
        # Enhanced templates database
        self.templates = {
            "technical_developer": {
                "senior": """Dear Hiring Manager,

I am writing to express my keen interest in the {job_title} position at {company}. With {experience_years} years of professional experience in {primary_technology} development, I have successfully delivered {project_count} projects that demonstrate my expertise in {key_skills}.

My technical accomplishments include:
• Developed and maintained scalable {app_type} applications serving {user_count}+ users
• Implemented {feature_improvement} that improved performance by {performance_improvement}%
• Collaborated with cross-functional teams to deliver features ahead of schedule
• Reduced production bugs by {bug_reduction}% through improved testing strategies

My skill set includes: {technical_skills_list}

I have been following {company}'s work in the {industry} sector and am particularly impressed by {company_achievement}. I am confident that my experience with {relevant_technology} aligns perfectly with your requirements for this role.

I am eager to contribute to your team's success and help {company} achieve its goals in {company_focus_area}.

Thank you for considering my application. I look forward to discussing how I can add value to your organization.

Sincerely,
{applicant_name}""",

                "mid_level": """Hello {company} Team,

I was excited to see the {job_title} position opening at {company}. With {experience_years} years of hands-on experience in {primary_technology} and a strong foundation in {secondary_skills}, I believe I can make immediate contributions to your development team.

Key highlights of my experience:
✓ Built {app_count} production applications using {primary_technology}
✓ Improved application load time by {performance_gain}% through optimization
✓ Implemented {feature_count} new features that increased user engagement
✓ Collaborated with designers to create intuitive user interfaces

Technical Proficiencies: {technical_skills_list}

What excites me about {company} is your focus on {company_value}. I've been following your work on {company_project} and believe my skills in {relevant_skill} would complement your team's efforts.

I am enthusiastic about the opportunity to grow with {company} and contribute to your success in the {industry} space.

Best regards,
{applicant_name}""",

                "junior": """Dear Hiring Manager,

I am writing to apply for the {job_title} position at {company}. As a recent graduate/new professional with training in {primary_technology}, I am eager to begin my career with an innovative company like {company}.

During my academic/professional journey, I have:
• Completed {project_count} projects using {primary_technology} and related technologies
• Developed proficiency in {technical_skills_list}
• Gained hands-on experience with {tools_experience}
• Demonstrated ability to quickly learn and apply new technologies

I am particularly drawn to {company} because of your reputation for {company_strength}. I am impressed by your work in {company_area} and would be thrilled to contribute to your mission.

I am a fast learner, highly motivated, and excited about the opportunity to grow my skills while contributing to {company}'s success.

Thank you for considering my application.

Sincerely,
{applicant_name}"""
            },
            
            "business_professional": {
                "manager": """Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company}. With {experience_years} years of experience in {industry} and a proven track record of {key_achievement}, I am confident in my ability to contribute significantly to your team.

My professional accomplishments include:
• Led a team of {team_size} to achieve {business_goal}, resulting in {positive_outcome}
• Developed and implemented strategies that increased {metric} by {improvement_percentage}%
• Managed {budget_amount} budgets while delivering projects on time
• Built strong relationships with {stakeholder_type}, improving collaboration

I have followed {company}'s growth in the {market_segment} market and am impressed by your approach to {company_approach}. My experience with {relevant_experience} aligns well with your needs for this role.

I am excited about the opportunity to bring my expertise to {company} and help drive success in {company_initiative}.

Thank you for your consideration.

Best regards,
{applicant_name}""",

                "analyst": """Dear {company} Team,

I am writing to apply for the {job_title} position at {company}. With {experience_years} years of experience in data analysis and a strong background in {analysis_tools}, I am eager to contribute to your analytical initiatives.

My analytical capabilities include:
• Analyzed {data_volume} of data to derive actionable insights
• Created dashboards and reports that improved decision-making by {improvement_percentage}%
• Identified trends that led to {cost_saving} in operational expenses
• Collaborated with {department_type} teams to implement data-driven solutions

Technical Skills: {technical_skills_list}

I am particularly interested in {company} because of your focus on {data_initiative}. I have been following your work in {industry_application} and believe my skills in {relevant_skill} would be valuable to your team.

I look forward to the possibility of discussing how I can contribute to {company}'s data-driven success.

Sincerely,
{applicant_name}"""
            }
        }
        
        # Industry-specific phrases
        self.industry_data = {
            "tech": {
                "achievements": [
                    "Developed applications serving {user_count}+ active users",
                    "Reduced application loading time by {percentage}% through optimization",
                    "Implemented features increasing user retention by {percentage}%",
                    "Improved API response time from {old_time}ms to {new_time}ms",
                    "Led migration from {old_tech} to {new_tech} with zero downtime"
                ],
                "skills": ["Flutter", "Dart", "React", "Python", "JavaScript", "TypeScript", 
                          "Node.js", "Firebase", "AWS", "Docker", "Kubernetes", "Git", 
                          "REST APIs", "GraphQL", "MongoDB", "PostgreSQL", "CI/CD"]
            },
            "finance": {
                "achievements": [
                    "Managed portfolios worth ${amount}",
                    "Reduced operational costs by {percentage}%",
                    "Increased investment returns by {percentage}%",
                    "Developed risk models with {accuracy}% accuracy",
                    "Automated processes saving {hours} hours monthly"
                ],
                "skills": ["Financial Analysis", "Risk Management", "Excel", "SQL", 
                          "Python", "Data Visualization", "Budgeting", "Forecasting"]
            },
            "healthcare": {
                "achievements": [
                    "Improved patient satisfaction scores by {percentage}%",
                    "Reduced processing time for {process} by {percentage}%",
                    "Implemented system serving {patient_count}+ patients",
                    "Achieved {compliance}% compliance rate",
                    "Trained {staff_count}+ staff on new systems"
                ],
                "skills": ["Healthcare IT", "EMR Systems", "Data Privacy", "Process Improvement", 
                          "Patient Care", "Regulatory Compliance", "Medical Terminology"]
            }
        }

    def generate_cover_letter(self, user_profile: Dict[str, Any], 
                             job_details: Dict[str, Any]) -> str:
        """
        Generate cover letter - automatically uses template if OpenAI fails
        """
        try:
            # Try OpenAI with timeout
            if self.use_openai:
                try:
                    ai_letter = self._generate_with_openai(user_profile, job_details)
                    if ai_letter and len(ai_letter) > 100:
                        return ai_letter
                except Exception as ai_error:
                    print(f"⚠️ OpenAI failed: {ai_error}")
            
            # Always use template (more reliable)
            return self._generate_with_template(user_profile, job_details)
            
        except Exception as e:
            print(f"❌ Cover letter generation error: {e}")
            # Ultimate fallback
            return self._generate_ultimate_fallback(user_profile, job_details)

    def _generate_with_openai(self, user_profile: Dict[str, Any], 
                             job_details: Dict[str, Any]) -> Optional[str]:
        """
        Generate cover letter using OpenAI GPT (with better error handling)
        """
        try:
            prompt = self._create_openai_prompt(user_profile, job_details)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional career coach writing compelling, authentic cover letters."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                timeout=10  # 10 second timeout
            )
            
            letter = response.choices[0].message.content.strip()
            
            # Validate response
            if len(letter) < 150:
                raise ValueError("OpenAI response too short")
                
            letter = self._post_process_letter(letter, user_profile, job_details)
            
            print("✅ AI-generated cover letter created")
            return letter
            
        except Exception as e:
            print(f"⚠️ OpenAI generation failed: {e}")
            return None

    def _create_openai_prompt(self, user_profile: Dict[str, Any], 
                             job_details: Dict[str, Any]) -> str:
        """
        Create prompt for OpenAI
        """
        user_name = user_profile.get("name", user_profile.get("full_name", "Applicant"))
        user_skills = user_profile.get("skills", [])
        if isinstance(user_skills, str):
            user_skills = [s.strip() for s in user_skills.split(",")]
        user_experience = user_profile.get("experience_years", user_profile.get("experience", 1))
        
        job_title = job_details.get("title", job_details.get("job_title", "the position"))
        company = job_details.get("company", "your company")
        job_desc = job_details.get("description", job_details.get("job_description", ""))[:500]
        
        prompt = f"""Write a professional, tailored cover letter with these specifics:

APPLICANT PROFILE:
- Name: {user_name}
- Key Skills: {', '.join(user_skills[:8])}
- Experience: {user_experience} years
- Current/Previous Role: {user_profile.get('current_role', user_profile.get('role', 'Professional'))}

JOB DETAILS:
- Position: {job_title}
- Company: {company}
- Key Requirements: {job_desc[:300]}

INSTRUCTIONS:
1. Address to "Hiring Manager"
2. Show enthusiasm for {company} specifically
3. Highlight relevant skills: {', '.join(user_skills[:5])}
4. Include 2-3 specific achievements/contributions
5. Keep tone professional but not overly formal
6. Length: 250-350 words
7. End with professional closing and signature

COVER LETTER:"""
        
        return prompt

    def _generate_with_template(self, user_profile: Dict[str, Any], 
                               job_details: Dict[str, Any]) -> str:
        """
        Generate cover letter using smart templates (PRIMARY METHOD)
        """
        try:
            # Determine template based on job type and experience
            job_title = (job_details.get("title") or job_details.get("job_title") or "").lower()
            
            # 🔥 CRITICAL FIX: Safely convert experience to integer
            experience_value = user_profile.get("experience_years") or user_profile.get("experience", 1)
            
            # Ensure experience is integer
            try:
                if isinstance(experience_value, str):
                    experience = int(experience_value)
                elif isinstance(experience_value, (int, float)):
                    experience = int(experience_value)
                else:
                    experience = 1  # Default
            except (ValueError, TypeError):
                experience = 1  # Default on error
            
            print(f"📊 Experience value: {experience_value} -> Converted to: {experience}")
            
            # Select template category
            if any(word in job_title for word in ["developer", "engineer", "programmer", "software", "technical"]):
                category = "technical_developer"
                if experience >= 5:
                    template_type = "senior"
                elif experience >= 2:
                    template_type = "mid_level"
                else:
                    template_type = "junior"
            else:
                category = "business_professional"
                if any(word in job_title for word in ["manager", "director", "lead", "head"]):
                    template_type = "manager"
                else:
                    template_type = "analyst"
            
            # Get template
            template = self.templates.get(category, {}).get(template_type)
            if not template:
                template = self.templates["technical_developer"]["mid_level"]
            
            # Prepare dynamic data with safe experience
            template_data = self._prepare_dynamic_data(user_profile, job_details)
            
            # 🔥 Ensure experience_years is numeric in template data
            template_data["experience_years"] = experience
            
            # Fill template
            letter = template.format(**template_data)
            
            # Post-process
            letter = self._post_process_letter(letter, user_profile, job_details)
            
            print(f"✅ Template cover letter generated ({category}/{template_type})")
            return letter
            
        except Exception as e:
            print(f"❌ Template generation error: {e}")
            # Fallback to ultimate fallback
            return self._generate_ultimate_fallback(user_profile, job_details)

    def _prepare_dynamic_data(self, user_profile: Dict[str, Any], 
                             job_details: Dict[str, Any]) -> Dict[str, str]:
        """
        Prepare dynamic data for templates with realistic values
        """
        # Basic information
        applicant_name = user_profile.get("name", user_profile.get("full_name", "Applicant"))
        
        # 🔥 SAFE EXPERIENCE EXTRACTION
        experience_years = 1  # Default
        try:
            exp_value = user_profile.get("experience_years") or user_profile.get("experience", 1)
            if isinstance(exp_value, str):
                experience_years = int(exp_value)
            elif isinstance(exp_value, (int, float)):
                experience_years = int(exp_value)
        except (ValueError, TypeError):
            experience_years = 1
        
        print(f"📊 Dynamic data - Experience: {experience_years}")
        
        # Job information
        job_title = job_details.get("title", job_details.get("job_title", "the position"))
        company = job_details.get("company", "your company")
        
        # Skills processing
        skills = user_profile.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        if not skills:
            skills = ["Problem Solving", "Communication", "Team Collaboration"]
        
        # Generate realistic metrics based on experience
        if experience_years >= 5:
            user_count = random.randint(5000, 50000)
            project_count = random.randint(8, 20)
            performance_improvement = random.randint(25, 60)
            bug_reduction = random.randint(30, 70)
            app_count = random.randint(5, 15)
        elif experience_years >= 2:
            user_count = random.randint(1000, 10000)
            project_count = random.randint(3, 8)
            performance_improvement = random.randint(15, 40)
            bug_reduction = random.randint(20, 50)
            app_count = random.randint(2, 6)
        else:
            user_count = random.randint(100, 1000)
            project_count = random.randint(1, 3)
            performance_improvement = random.randint(10, 30)
            bug_reduction = random.randint(10, 30)
            app_count = random.randint(1, 3)
        
        # Company data
        industries = ["technology", "software development", "digital solutions", 
                     "IT services", "mobile applications", "web platforms"]
        company_values = ["innovation", "quality", "customer satisfaction", 
                         "excellence", "collaboration", "growth"]
        
        return {
            # Basic info
            "applicant_name": applicant_name,
            "job_title": job_title,
            "company": company,
            "experience_years": experience_years,
            
            # Technical metrics
            "user_count": f"{user_count:,}",
            "project_count": project_count,
            "app_count": app_count,
            "performance_improvement": performance_improvement,
            "performance_gain": performance_improvement,
            "bug_reduction": bug_reduction,
            "feature_count": random.randint(10, 50),
            
            # Skills
            "primary_technology": skills[0] if skills else "software development",
            "secondary_skills": ", ".join(skills[1:4]) if len(skills) > 1 else "related technologies",
            "technical_skills_list": ", ".join(skills[:8]),
            "key_skills": ", ".join(skills[:5]),
            "relevant_technology": skills[0] if skills else "relevant technologies",
            "relevant_skill": skills[0] if skills else "key skills",
            
            # Company specifics
            "industry": random.choice(industries),
            "company_achievement": f"your work in {random.choice(industries)}",
            "company_focus_area": random.choice(industries),
            "company_value": random.choice(company_values),
            "company_project": f"your {random.choice(['latest', 'upcoming', 'flagship'])} project",
            "company_strength": random.choice(["innovation", "technical excellence", "team culture"]),
            "company_area": random.choice(industries),
            "company_approach": random.choice(["customer-centric solutions", "innovative approaches", "quality delivery"]),
            "company_initiative": random.choice(["digital transformation", "product development", "market expansion"]),
            
            # Business metrics
            "team_size": random.randint(3, 15),
            "business_goal": random.choice(["project completion", "revenue targets", "client satisfaction"]),
            "positive_outcome": random.choice(["increased efficiency", "cost savings", "improved performance"]),
            "metric": random.choice(["productivity", "revenue", "customer satisfaction"]),
            "improvement_percentage": random.randint(15, 45),
            "budget_amount": f"{random.randint(50, 500):,}K",
            "stakeholder_type": random.choice(["clients", "partners", "cross-functional teams"]),
            "market_segment": random.choice(industries),
            "relevant_experience": ", ".join(skills[:3]),
            
            # Analysis metrics
            "data_volume": random.choice(["large datasets", "complex data structures", "diverse data sources"]),
            "cost_saving": f"${random.randint(10, 100):,}K",
            "department_type": random.choice(["business", "technical", "operational"]),
            "data_initiative": random.choice(["data-driven decision making", "analytics excellence", "insight generation"]),
            "industry_application": random.choice(["business intelligence", "performance analytics", "predictive modeling"]),
            
            # Application type
            "app_type": random.choice(["web", "mobile", "enterprise"]),
            "feature_improvement": random.choice(["caching mechanisms", "database optimization", "code refactoring"]),
            "tools_experience": ", ".join(skills[:4] if skills else ["modern development tools"]),
            "analysis_tools": ", ".join(skills[:4] if skills else ["analytical tools"])
        }

    def _post_process_letter(self, letter: str, user_profile: Dict[str, Any], 
                            job_details: Dict[str, Any]) -> str:
        """
        Post-process the generated letter for consistency
        """
        try:
            # Ensure proper formatting
            letter = letter.strip()
            letter = letter.replace('\r\n', '\n').replace('\r', '\n')
            
            # Ensure it starts with proper greeting
            if not letter.startswith(('Dear', 'Hello', 'To whom it may concern')):
                letter = f"Dear Hiring Manager,\n\n{letter}"
            
            # Ensure it ends with proper signature
            applicant_name = user_profile.get("name", user_profile.get("full_name", "Applicant"))
            if not letter.strip().endswith(applicant_name):
                letter = f"{letter}\n\nSincerely,\n{applicant_name}"
            
            # Add generation note (optional)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            letter = f"{letter}\n\n---\nGenerated by AutoCareer AI | {timestamp}"
            
            return letter
        except Exception as e:
            print(f"❌ Post-process error: {e}")
            # Return original letter if post-processing fails
            return letter

    def _generate_ultimate_fallback(self, user_profile: Dict[str, Any], 
                                   job_details: Dict[str, Any]) -> str:
        """
        Ultimate fallback - always works
        """
        try:
            applicant_name = user_profile.get("name", user_profile.get("full_name", "Applicant"))
            job_title = job_details.get("title", job_details.get("job_title", "the position"))
            company = job_details.get("company", "your company")
            
            skills = user_profile.get("skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            if not skills:
                skills = ["relevant skills"]
            
            # Safe experience extraction
            experience = 1
            try:
                exp_val = user_profile.get("experience_years") or user_profile.get("experience", 1)
                if isinstance(exp_val, str):
                    experience = int(exp_val)
                elif isinstance(exp_val, (int, float)):
                    experience = int(exp_val)
            except:
                experience = 1
            
            letter = f"""Dear Hiring Manager,

I am writing to apply for the {job_title} position at {company}.

With {experience} years of professional experience and expertise in {', '.join(skills[:3])}, I am confident that I possess the qualifications needed to excel in this role.

I have successfully contributed to various projects throughout my career, demonstrating strong problem-solving abilities and a commitment to delivering quality results.

I am particularly interested in this opportunity at {company} because of your reputation for excellence in the field. I believe my background aligns well with your requirements, and I am eager to contribute to your team's success.

Thank you for considering my application. I look forward to the possibility of discussing how I can add value to {company}.

Sincerely,
{applicant_name}

---
Generated by AutoCareer AI | {datetime.now().strftime("%Y-%m-%d")}"""
            
            print("✅ Ultimate fallback cover letter generated")
            return letter
            
        except Exception as e:
            print(f"❌ Ultimate fallback error: {e}")
            # Absolute last resort
            return f"""Dear Hiring Manager,

I am applying for the position at your company.

I believe my skills and experience make me a suitable candidate for this role.

Thank you for considering my application.

Sincerely,
Applicant

---
Generated by AutoCareer AI"""

    def analyze_job_fit(self, user_profile: Dict[str, Any], 
                       job_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze job fit for cover letter optimization
        """
        try:
            user_skills = user_profile.get("skills", [])
            if isinstance(user_skills, str):
                user_skills = [s.strip().lower() for s in user_skills.split(",")]
            else:
                user_skills = [str(s).lower() for s in user_skills]
            
            job_desc = (job_details.get("description") or job_details.get("job_description") or "").lower()
            
            # Extract keywords
            words = re.findall(r'\b[a-zA-Z]{4,}\b', job_desc)
            job_keywords = set(word.lower() for word in words)
            
            # Calculate matches
            matching_skills = [skill for skill in user_skills if any(keyword in skill or skill in keyword for keyword in job_keywords)]
            
            match_percentage = (len(matching_skills) / len(job_keywords) * 100) if job_keywords else 0
            
            return {
                "match_score": round(match_percentage, 1),
                "matched_skills": matching_skills[:10],
                "total_keywords": len(job_keywords),
                "top_keywords": list(job_keywords)[:10]
            }
        except Exception as e:
            print(f"❌ Job fit analysis error: {e}")
            return {
                "match_score": 0,
                "matched_skills": [],
                "total_keywords": 0,
                "top_keywords": []
            }


# Quick test function
if __name__ == "__main__":
    # Test the cover letter generator
    ai = CoverLetterAI()
    
    test_profile = {
        "name": "John Doe",
        "full_name": "John Doe",
        "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "Git"],
        "experience_years": "3",  # Test with string
        "current_role": "Flutter Developer"
    }
    
    test_job = {
        "title": "Senior Flutter Developer",
        "company": "Tech Innovations Inc.",
        "description": "Looking for Flutter developer with 3+ years experience. Must know Dart, Firebase, and REST APIs. Mobile app development experience required."
    }
    
    print("🔧 Testing Cover Letter Generator...")
    letter = ai.generate_cover_letter(test_profile, test_job)
    print("\n" + "="*60)
    print("GENERATED COVER LETTER:")
    print("="*60)
    print(letter)
    print("="*60)
    
    # Test job fit analysis
    fit_analysis = ai.analyze_job_fit(test_profile, test_job)
    print(f"\n📊 Job Fit Analysis: {fit_analysis['match_score']}% match")
    print(f"Matched Skills: {fit_analysis['matched_skills']}")
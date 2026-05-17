import os
import base64
import json
from typing import Dict, List, Any
import PyPDF2
import openai
from dotenv import load_dotenv

load_dotenv()

class CVParserNLP:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai = bool(self.api_key)
        
        if self.use_openai:
            openai.api_key = self.api_key
            print("✅ OpenAI configured for CV parsing")
        else:
            print("⚠️  OPENAI_API_KEY not found, using fallback parser")
    
    def parse_cv(self, file_path: str) -> Dict[str, Any]:
        """Parse CV using AI for accurate skill extraction"""
        try:
            # Step 1: Extract text from file
            text = self._extract_text(file_path)
            
            # Step 2: Use AI to parse if available
            if self.use_openai and len(text) > 100:
                ai_parsed = self._parse_with_ai(text)
                if ai_parsed and ai_parsed.get("success"):
                    return ai_parsed
            
            # Step 3: Fallback to traditional parsing
            return self._parse_with_fallback(text)
            
        except Exception as e:
            print(f"❌ CV parsing error: {e}")
            return self._get_fallback_data()
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF or text file"""
        if file_path.lower().endswith('.pdf'):
            return self._extract_pdf_text(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"❌ PDF extraction error: {e}")
        return text
    
    def _parse_with_ai(self, text: str) -> Dict[str, Any]:
        """Use GPT to extract structured information from CV"""
        try:
            # Truncate if too long
            if len(text) > 6000:
                text = text[:6000]
            
            prompt = f"""Extract the following information from this resume/CV. Return ONLY a valid JSON object with these fields:

1. personal_info: {{"name": "Full Name", "email": "email", "phone": "phone", "location": "city/country"}}
2. skills: List of ALL technical skills (programming languages, frameworks, tools, soft skills)
3. experience: List of jobs with {{"title": "Job Title", "company": "Company", "duration": "X years", "description": "brief description"}}
4. education: List of degrees with {{"degree": "Degree Name", "institution": "University", "year": "Year"}}
5. experience_years: Total years of professional experience (number)
6. summary: 2-3 sentence professional summary

Resume Text:
{text}

JSON Output:"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert CV parser. Extract structured information accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500,
                timeout=15
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Ensure required fields
                if "personal_info" not in parsed_data:
                    parsed_data["personal_info"] = {}
                if "skills" not in parsed_data:
                    parsed_data["skills"] = []
                if "experience" not in parsed_data:
                    parsed_data["experience"] = []
                if "education" not in parsed_data:
                    parsed_data["education"] = []
                if "experience_years" not in parsed_data:
                    parsed_data["experience_years"] = self._estimate_experience(parsed_data.get("experience", []))
                
                parsed_data["raw_text"] = text[:500]
                parsed_data["success"] = True
                parsed_data["parsed_by"] = "ai"
                
                print(f"✅ AI CV parsing successful: {len(parsed_data.get('skills', []))} skills found")
                return parsed_data
            
            return self._parse_with_fallback(text)
            
        except Exception as e:
            print(f"❌ AI parsing error: {e}")
            return self._parse_with_fallback(text)
    
    def _parse_with_fallback(self, text: str) -> Dict[str, Any]:
        """Traditional parsing as fallback"""
        skills = self._extract_skills_fallback(text)
        
        return {
            "personal_info": self._extract_personal_info(text),
            "skills": skills,
            "experience": self._extract_experience_fallback(text),
            "education": self._extract_education_fallback(text),
            "summary": self._extract_summary(text),
            "experience_years": self._calculate_experience_years_fallback(text),
            "raw_text": text[:500],
            "success": True,
            "parsed_by": "fallback"
        }
    
    def _extract_skills_fallback(self, text: str) -> List[str]:
        """Traditional skill extraction"""
        common_skills = [
            'Python', 'Java', 'JavaScript', 'C++', 'C#', 'PHP', 'Ruby', 'Go',
            'Swift', 'Kotlin', 'Dart', 'Flutter', 'React', 'Angular', 'Vue',
            'Node.js', 'Express', 'Django', 'Flask', 'Spring', 'Laravel',
            'HTML', 'CSS', 'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL', 'MySQL',
            'Firebase', 'AWS', 'Azure', 'Docker', 'Kubernetes', 'Git',
            'REST API', 'GraphQL', 'Microservices', 'CI/CD', 'Agile', 'Scrum'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills[:20]
    
    def _extract_personal_info(self, text: str) -> Dict[str, str]:
        """Extract personal info"""
        info = {}
        
        # Email pattern
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            info['email'] = emails[0]
        
        # Phone pattern
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            info['phone'] = phones[0][0] if isinstance(phones[0], tuple) else phones[0]
        
        # Try to get name from first few lines
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line.split()) >= 2 and len(line.split()) <= 4:
                if not line.isupper() and len(line) < 50:
                    info['name'] = line
                    break
        
        return info
    
    def _extract_experience_fallback(self, text: str) -> List[Dict[str, str]]:
        """Extract experience (simplified)"""
        experiences = []
        
        lines = text.split('\n')
        current_exp = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for job titles
            if any(role in line.lower() for role in ['developer', 'engineer', 'manager', 'analyst']):
                if current_exp:
                    experiences.append(current_exp)
                current_exp = {'title': line, 'company': 'Unknown', 'description': ''}
            elif current_exp and len(line.split()) > 5:
                if current_exp.get('description'):
                    current_exp['description'] += ' ' + line
                else:
                    current_exp['description'] = line
        
        if current_exp:
            experiences.append(current_exp)
        
        return experiences[:5]
    
    def _extract_education_fallback(self, text: str) -> List[Dict[str, str]]:
        """Extract education (simplified)"""
        education = []
        
        lines = text.split('\n')
        for line in lines:
            if any(word in line.lower() for word in ['university', 'college', 'bachelor', 'master', 'phd']):
                education.append({
                    'degree': line,
                    'institution': 'Extracted from CV',
                    'year': 'N/A'
                })
                if len(education) >= 2:
                    break
        
        return education
    
    def _extract_summary(self, text: str) -> str:
        """Extract summary"""
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if len(para.split()) > 20 and len(para.split()) < 100:
                return para[:500]
        return "Experienced professional"
    
    def _calculate_experience_years_fallback(self, text: str) -> int:
        """Estimate experience years"""
        import re
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        
        if len(years) >= 2:
            try:
                years_int = [int(y) for y in years]
                return min(max(max(years_int) - min(years_int), 1), 30)
            except:
                pass
        
        return 2
    
    def _estimate_experience(self, experiences: List) -> int:
        """Estimate from experience list"""
        return min(len(experiences) * 2, 20)
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """Ultimate fallback"""
        return {
            "personal_info": {"name": "Applicant", "email": "applicant@example.com"},
            "skills": ["Communication", "Problem Solving", "Teamwork"],
            "experience": [],
            "education": [],
            "summary": "Experienced professional",
            "experience_years": 2,
            "raw_text": "",
            "success": True,
            "parsed_by": "fallback"
        }
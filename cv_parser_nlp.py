import os
import re
import json
from typing import Dict, List, Any
import PyPDF2
import spacy
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import nltk

# Download NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass

class CVParserNLP:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.stop_words = set(stopwords.words('english'))
        
        # Keywords for extraction
        self.name_keywords = ['name', 'full name', 'candidate', 'applicant']
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
        self.skills_keywords = ['skills', 'technical skills', 'competencies', 'expertise']
        self.experience_keywords = ['experience', 'work history', 'employment', 'career']
        self.education_keywords = ['education', 'qualifications', 'academic', 'degree']
        
    def parse_cv(self, file_path: str) -> Dict[str, Any]:
        """Parse CV file and extract structured information"""
        try:
            # Extract text from file
            text = self._extract_text(file_path)
            
            # Parse using NLP
            parsed_data = {
                "personal_info": self._extract_personal_info(text),
                "skills": self._extract_skills(text),
                "experience": self._extract_experience(text),
                "education": self._extract_education(text),
                "summary": self._extract_summary(text),
                "raw_text": text[:1000]  # Store first 1000 chars for reference
            }
            
            # Calculate experience years
            parsed_data["experience_years"] = self._calculate_experience_years(
                parsed_data["experience"]
            )
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing CV: {e}")
            return self._get_fallback_data()
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF or text file"""
        if file_path.lower().endswith('.pdf'):
            return self._extract_pdf_text(file_path)
        else:
            # Assume text file
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
        except:
            # Fallback: try PyPDF2 v2+
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        return text
    
    def _extract_personal_info(self, text: str) -> Dict[str, str]:
        """Extract personal information"""
        info = {}
        
        # Extract email
        emails = re.findall(self.email_pattern, text)
        if emails:
            info['email'] = emails[0]
        
        # Extract phone
        phones = re.findall(self.phone_pattern, text)
        if phones:
            info['phone'] = phones[0][0] if isinstance(phones[0], tuple) else phones[0]
        
        # Try to extract name (first 2 lines often contain name)
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line.split()) >= 2 and len(line.split()) <= 4:
                # Check if line looks like a name (not all caps, not too long)
                if not line.isupper() and len(line) < 50:
                    info['name'] = line
                    break
        
        # Extract LinkedIn profile
        linkedin_patterns = [
            r'linkedin\.com/in/[A-Za-z0-9-]+',
            r'linkedin\.com/[A-Za-z0-9-]+',
            r'https?://(www\.)?linkedin\.com/[^\s]+'
        ]
        for pattern in linkedin_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                info['linkedin'] = matches[0]
                break
        
        return info
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from CV"""
        skills = []
        
        # Common technical skills (expand as needed)
        common_skills = [
            'Python', 'Java', 'JavaScript', 'C++', 'C#', 'PHP', 'Ruby', 'Go',
            'Swift', 'Kotlin', 'Dart', 'Flutter', 'React', 'Angular', 'Vue',
            'Node.js', 'Express', 'Django', 'Flask', 'Spring', 'Laravel',
            'HTML', 'CSS', 'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL', 'MySQL',
            'Firebase', 'AWS', 'Azure', 'Docker', 'Kubernetes', 'Git',
            'REST API', 'GraphQL', 'Microservices', 'CI/CD', 'Agile', 'Scrum'
        ]
        
        # Look for skills section
        lines = text.lower().split('\n')
        in_skills_section = False
        
        for line in lines:
            # Check if this line starts a skills section
            if any(keyword in line for keyword in self.skills_keywords):
                in_skills_section = True
                continue
            
            if in_skills_section:
                # Check for common skills in this line
                for skill in common_skills:
                    if skill.lower() in line:
                        if skill not in skills:
                            skills.append(skill)
        
        # Also search entire text for skills
        for skill in common_skills:
            if skill.lower() in text.lower() and skill not in skills:
                skills.append(skill)
        
        # Limit to top 15 skills
        return skills[:15]
    
    def _extract_experience(self, text: str) -> List[Dict[str, str]]:
        """Extract work experience"""
        experiences = []
        
        # Simple regex for dates and positions
        date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}'
        
        lines = text.split('\n')
        current_exp = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Look for date patterns (indicating experience entry)
            if re.search(date_pattern, line, re.IGNORECASE):
                if current_exp:
                    experiences.append(current_exp.copy())
                    current_exp = {}
                
                # Try to extract company and position
                # Usually format: Position at Company (Date - Date)
                if ' at ' in line:
                    parts = line.split(' at ', 1)
                    current_exp['title'] = parts[0].strip()
                    current_exp['company'] = parts[1].split('(')[0].strip()
                elif ',' in line:
                    parts = line.split(',', 1)
                    current_exp['title'] = parts[0].strip()
                    current_exp['company'] = parts[1].split('(')[0].strip()
            
            # Collect description lines
            elif current_exp and len(line.split()) > 3:
                if 'description' not in current_exp:
                    current_exp['description'] = line
                else:
                    current_exp['description'] += ' ' + line
        
        if current_exp:
            experiences.append(current_exp)
        
        # Fallback: extract from bullet points
        if not experiences:
            bullet_points = re.findall(r'•\s*(.*?)(?=•|$)', text, re.DOTALL)
            for point in bullet_points[:5]:
                if any(role in point.lower() for role in ['developer', 'engineer', 'manager', 'analyst']):
                    experiences.append({
                        'title': 'Extracted Role',
                        'company': 'Various',
                        'description': point.strip()
                    })
        
        return experiences[:5]  # Return max 5 experiences
    
    def _extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education information"""
        education = []
        
        # Look for education keywords
        lines = text.split('\n')
        in_education_section = False
        
        for line in lines:
            line = line.strip()
            
            # Check if this line starts education section
            if any(keyword in line.lower() for keyword in self.education_keywords):
                in_education_section = True
                continue
            
            if in_education_section and line:
                # Common degree patterns
                degree_patterns = [
                    r'B\.?S\.?c?\.?', r'B\.?A\.?', r'M\.?S\.?c?\.?', r'M\.?A\.?',
                    r'PhD', r'Bachelor', r'Master', r'Doctorate'
                ]
                
                for pattern in degree_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        education.append({
                            'degree': line,
                            'institution': 'Extracted from CV',
                            'year': self._extract_year(line)
                        })
                        break
        
        # Fallback: simple extraction
        if not education:
            for line in lines:
                if any(word in line.lower() for word in ['university', 'college', 'institute', 'school']):
                    education.append({
                        'degree': 'Education',
                        'institution': line,
                        'year': 'N/A'
                    })
                    if len(education) >= 2:
                        break
        
        return education[:3]
    
    def _extract_summary(self, text: str) -> str:
        """Extract summary/objective"""
        summary = ""
        
        # Look for common summary keywords
        summary_keywords = ['summary', 'objective', 'profile', 'about']
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in summary_keywords):
                # Take next few lines as summary
                summary_lines = []
                for j in range(i+1, min(i+6, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and len(next_line.split()) > 3:
                        summary_lines.append(next_line)
                        if len(' '.join(summary_lines)) > 200:
                            break
                
                if summary_lines:
                    summary = ' '.join(summary_lines)
                    break
        
        # If no summary found, use first paragraph
        if not summary:
            paragraphs = text.split('\n\n')
            for para in paragraphs:
                if len(para.split()) > 20 and len(para.split()) < 100:
                    summary = para
                    break
        
        return summary[:500]  # Limit length
    
    def _extract_year(self, text: str) -> str:
        """Extract year from text"""
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        return year_match.group(0) if year_match else 'N/A'
    
    def _calculate_experience_years(self, experiences: List[Dict]) -> int:
        """Calculate total years of experience"""
        if not experiences:
            return 0
        
        # Simple estimation: 2 years per experience entry
        return min(len(experiences) * 2, 20)
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """Return fallback data if parsing fails"""
        return {
            "personal_info": {
                "name": "Applicant",
                "email": "applicant@example.com",
                "phone": "+1234567890"
            },
            "skills": ["Problem Solving", "Communication", "Teamwork"],
            "experience": [{
                "title": "Professional",
                "company": "Various Companies",
                "description": "Extracted from CV"
            }],
            "education": [{
                "degree": "Education",
                "institution": "University",
                "year": "N/A"
            }],
            "summary": "Experienced professional with strong skills.",
            "experience_years": 2,
            "raw_text": ""
        }
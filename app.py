import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
import docx
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# try:
#     from jobspy import scrape_jobs
# except ImportError:
#     print("Warning: 'python-jobspy' library not found. Job search will use sample data.")
scrape_jobs = None

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

JOB_ROLES = {
    "Software Engineer": ["python", "java", "c++", "sql", "git", "algorithms", "data structures", "flask", "react"],
    "Data Scientist": ["python", "r", "sql", "machine learning", "pandas", "numpy", "statistics", "deep learning"],
    "Product Manager": ["agile", "scrum", "product roadmap", "metrics", "user stories", "communication", "market research"],
    "Web Developer": ["html", "css", "javascript", "react", "node.js", "bootstrap", "responsive design"],
    "DevOps Engineer": ["aws", "docker", "kubernetes", "jenkins", "linux", "ci/cd", "terraform"],
    "Full Stack Developer": ["javascript", "react", "node.js", "mongodb", "sql", "html", "css", "git", "rest api"],
    "Machine Learning Engineer": ["python", "tensorflow", "pytorch", "scikit-learn", "deep learning", "nlp", "cloud", "docker"],
    "Cybersecurity Analyst": ["network security", "linux", "python", "siem", "firewalls", "cryptography", "penetration testing"],
    "Cloud Architect": ["aws", "azure", "google cloud", "docker", "kubernetes", "terraform", "networking", "security"],
    "Business Analyst": ["sql", "excel", "tableau", "power bi", "communication", "requirements gathering", "agile"]
}

SKILL_RESOURCES = {
    "python": "https://www.youtube.com/playlist?list=PL-osiE80TeTt2d9bfVyTiXJA-UTHn6WwU",
    "java": "https://www.udemy.com/topic/java/",
    "sql": "https://www.w3schools.com/sql/",
    "react": "https://react.dev/learn",
    "node.js": "https://nodejs.org/en/learn",
    "aws": "https://aws.amazon.com/getting-started/",
    "docker": "https://docs.docker.com/get-started/",
    "kubernetes": "https://kubernetes.io/docs/tutorials/",
    "machine learning": "https://www.coursera.org/learn/machine-learning",
    "git": "https://git-scm.com/doc",
    "html": "https://developer.mozilla.org/en-US/docs/Web/HTML",
    "css": "https://developer.mozilla.org/en-US/docs/Web/CSS",
    "javascript": "https://javascript.info/",
    "pandas": "https://pandas.pydata.org/docs/user_guide/10min.html",
    "tensorflow": "https://www.tensorflow.org/learn",
    "linux": "https://ubuntu.com/tutorials/command-line-for-beginners",
    "agile": "https://www.atlassian.com/agile"
}

def extract_text_from_pdf(file_path):
    try:
        return extract_text(file_path)
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""

def calculate_match_score(resume_text, job_description):
    """
    Calculates the cosine similarity between the resume and job description using TF-IDF.
    """
    if not resume_text or not job_description:
        return 0.0
    
    # Clean texts slightly
    resume_text = re.sub(r'\s+', ' ', resume_text).strip()
    job_description = re.sub(r'\s+', ' ', job_description).strip()
    
    documents = [resume_text, job_description]
    tfidf = TfidfVectorizer(stop_words='english')
    
    try:
        tfidf_matrix = tfidf.fit_transform(documents)
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(similarity * 100, 2)
    except Exception as e:
        print(f"Error in match calculation: {e}")
        return 0.0

def analyze_resume(text, job_role):
    if not text:
        return {"error": "Could not extract text from resume."}
    
    required_skills = set(JOB_ROLES.get(job_role, []))
    if not required_skills:
        return {"error": "Invalid job role."}
    
    # Simple normalization and tokenization
    text_lower = text.lower()
    # Replace non-alphanumeric with space
    text_clean = re.sub(r'[^a-z0-9\s]', ' ', text_lower)
    resume_tokens = set(text_clean.split())
    
    # Calculate match (Keyword based for initial analysis)
    matched_skills = required_skills.intersection(resume_tokens)
    missing_skills = required_skills - matched_skills
    
    match_percentage = (len(matched_skills) / len(required_skills)) * 100 if required_skills else 0
    
    # Get basic recommendations (Keyword based)
    recommendations = []
    for role, skills in JOB_ROLES.items():
        role_skills = set(skills)
        if not role_skills: 
            continue
        role_match = role_skills.intersection(resume_tokens)
        role_pct = (len(role_match) / len(role_skills)) * 100
        recommendations.append({
            "role": role,
            "percentage": round(role_pct, 1)
        })
    
    # Sort by percentage desc
    recommendations.sort(key=lambda x: x['percentage'], reverse=True)
    
    # Map missing skills to resources
    missing_skills_data = []
    for skill in missing_skills:
        missing_skills_data.append({
            "skill": skill,
            "link": SKILL_RESOURCES.get(skill, f"https://www.google.com/search?q=learn+{skill}+tutorial")
        })
    
    # Extract Contact Info (Simple Regex)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
    
    email = re.search(email_pattern, text)
    phone = re.search(phone_pattern, text)
    
    candidate_info = {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found"
    }
    
    # Generate Smart Tips
    tips = []
    if len(resume_tokens) < 150:
        tips.append("Your resume seems short. Consider adding more details about your projects and responsibilities.")
    if "education" not in resume_tokens and "university" not in resume_tokens:
        tips.append("We couldn't find an 'Education' section. Ensure you list your degrees and certifications.")
    if "experience" not in resume_tokens and "work" not in resume_tokens:
        tips.append("Work experience is key! Make sure to label your work history clearly (e.g., 'Work Experience').")
    if not email:
        tips.append("No email address detected. Recruiters need a way to contact you!")
    if len(missing_skills) > len(required_skills) / 2:
        tips.append("You are missing more than 50% of the required skills. Consider learning the basics of this role first.")
    
    if not tips:
        tips.append("Great job! Your resume covers the basics well.")

    return {
        "match_percentage": round(match_percentage, 2),
        "matched_skills": list(matched_skills),
        "missing_skills": missing_skills_data,
        "job_role": job_role,
        "recommendations": recommendations[:3],
        "candidate_info": candidate_info,
        "tips": tips,
        "resume_text": text  # Send back the raw text for later use
    }

@app.route('/')
def index():
    return render_template('index.html', job_roles=list(JOB_ROLES.keys()))

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['resume']
    job_role = request.form.get('job_role')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and job_role:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        text = ""
        if filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif filename.lower().endswith('.docx'):
            text = extract_text_from_docx(file_path)
        else:
            return jsonify({"error": "Unsupported file format. Please upload PDF or DOCX."}), 400
            
        try:
            os.remove(file_path)
        except:
            pass
            
        result = analyze_resume(text, job_role)
        return jsonify(result)
        
    return jsonify({"error": "Invalid request"}), 400

@app.route('/search_jobs', methods=['POST'])
def search_jobs_route():
    data = request.json
    job_role = data.get('job_role')
    location = data.get('location', '')
    resume_text = data.get('resume_text', '')
    
    if not job_role:
        return jsonify({"error": "Job role is required"}), 400

    print(f"Searching jobs for: {job_role} in {location}")

    try:
        jobs_df = pd.DataFrame()
        
        # Use scraper if available
        if scrape_jobs:
            try:
                jobs_df = scrape_jobs(
                    site_name=["indeed", "glassdoor"], 
                    search_term=job_role,
                    location=location,
                    results_wanted=5,
                    hours_old=72,
                    country_indeed='USA'
                )
            except Exception as scrape_err:
                print(f"Scraping failed: {scrape_err}, falling back to simulation.")
        
        # Use sumulated data if scraper unavailable or failed/empty
        if jobs_df.empty:
            print("Using simulated job data.")
            simulated_jobs = [
                {
                    "title": f"Senior {job_role}",
                    "company": "Tech Innovations Inc.",
                    "location": location if location else "Remote",
                    "job_url": "#",
                    "description": f"We are looking for a skilled {job_role} with experience in Python, Flask, and React. Join our dynamic team to build cutting-edge solutions."
                },
                {
                    "title": f"Junior {job_role}",
                    "company": "StartUp Hero",
                    "location": location if location else "San Francisco, CA",
                    "job_url": "#",
                    "description": f"Entry level {job_role} position. Great opportunity to learn. Requirements: Basic knowledge of coding and enthusiastic attitude."
                },
                {
                    "title": f"{job_role} Lead",
                    "company": "Global Corp",
                    "location": location if location else "New York, NY",
                    "job_url": "#",
                    "description": f"Lead our {job_role} team. 5+ years experience required. Strong leadership skills and deep technical expertise needed."
                }
            ]
            jobs_df = pd.DataFrame(simulated_jobs)

        # Format jobs
        jobs_list = []
        for index, row in jobs_df.iterrows():
            description = str(row.get('description', ''))
            title = str(row.get('title', 'Unknown Role'))
            company = str(row.get('company', 'Unknown Company'))
            loc = str(row.get('location', 'Unknown Location'))
            url = str(row.get('job_url', '#'))
            
            # Calculate ML Match Score
            match_score = calculate_match_score(resume_text, description + " " + title)
            
            jobs_list.append({
                "title": title,
                "company": company,
                "location": loc,
                "job_url": url,
                "description_snippet": description[:200] + "..." if len(description) > 200 else description,
                "match_score": match_score
            })
            
        # Sort by match score
        jobs_list.sort(key=lambda x: x['match_score'], reverse=True)
        
        return jsonify({"jobs": jobs_list})
        
    except Exception as e:
        print(f"Job search error: {e}")
        return jsonify({"error": f"Failed to fetch jobs: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

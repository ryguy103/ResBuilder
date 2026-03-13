"""
web/app.py - FastAPI web interface for resbuilder
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import asyncio

from core import (
    list_applications,
    scrape_job_posting,
    generate_application,
    get_companies_dir,
    get_company_slug,
    read_master_resume,
    load_profile,
    save_profile,
    HAS_SCRAPING,
    BASE_PATH,
)

app = FastAPI(title="ResBuilder", description="Resume & Cover Letter Generator")

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Store for generation progress
generation_status = {}


class ScrapeRequest(BaseModel):
    url: str


class GenerateRequest(BaseModel):
    company: str
    role: str
    job_description: str
    url: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard showing all past applications"""
    applications = list_applications()
    
    # Check for API key
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "applications": applications,
        "has_api_key": has_api_key,
        "has_scraping": HAS_SCRAPING,
    })


@app.get("/new", response_class=HTMLResponse)
async def new_application(request: Request):
    """New application form"""
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    
    return templates.TemplateResponse("new.html", {
        "request": request,
        "has_api_key": has_api_key,
        "has_scraping": HAS_SCRAPING,
    })


@app.post("/scrape", response_class=HTMLResponse)
async def scrape_url(request: Request, url: str = Form(default="")):
    """Scrape a job posting URL and return the form partial"""
    # Validate URL
    url = url.strip() if url else ""
    if not url:
        return templates.TemplateResponse("partials/scrape_error.html", {
            "request": request,
            "error": "Please enter a URL"
        })
    
    if not url.startswith(("http://", "https://")):
        return templates.TemplateResponse("partials/scrape_error.html", {
            "request": request,
            "error": "URL must start with http:// or https://"
        })
    
    if not HAS_SCRAPING:
        return templates.TemplateResponse("partials/scrape_error.html", {
            "request": request,
            "error": "Scraping dependencies not installed. Run: pip install requests beautifulsoup4"
        })
    
    try:
        # Run scraping in thread pool to not block
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, scrape_job_posting, url)
    except Exception as e:
        return templates.TemplateResponse("partials/scrape_error.html", {
            "request": request,
            "error": f"Scraping failed: {str(e)}"
        })
    
    if not result:
        return templates.TemplateResponse("partials/scrape_error.html", {
            "request": request,
            "error": "Failed to fetch URL - no content returned"
        })
    
    if "error" in result:
        return templates.TemplateResponse("partials/scrape_error.html", {
            "request": request,
            "error": result["error"]
        })
    
    # Truncate very long job descriptions to prevent browser issues
    content = result.get("content", "")
    if len(content) > 50000:
        content = content[:50000] + "\n\n[Content truncated - original was too long]"
    
    return templates.TemplateResponse("partials/scrape_result.html", {
        "request": request,
        "company": result.get("company", ""),
        "role": result.get("role", ""),
        "job_description": content,
        "url": url,
        "char_count": len(content)
    })


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    background_tasks: BackgroundTasks,
    company: str = Form(...),
    role: str = Form(...),
    job_description: str = Form(...),
    url: str = Form(None)
):
    """Start generating application materials"""
    if not company or not role or not job_description:
        return templates.TemplateResponse("partials/generate_error.html", {
            "request": request,
            "error": "Company, role, and job description are required"
        })
    
    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return templates.TemplateResponse("partials/generate_error.html", {
            "request": request,
            "error": "ANTHROPIC_API_KEY not set. Please set it in your environment."
        })
    
    # Generate a task ID
    task_id = get_company_slug(company) + "-" + str(hash(company + role))[-6:]
    generation_status[task_id] = {"status": "starting", "progress": 0}
    
    # Run generation in background
    background_tasks.add_task(run_generation, task_id, company, role, job_description, url)
    
    return templates.TemplateResponse("partials/generating.html", {
        "request": request,
        "task_id": task_id,
        "company": company,
        "role": role
    })


async def run_generation(task_id: str, company: str, role: str, job_description: str, url: str):
    """Background task to run generation"""
    try:
        generation_status[task_id] = {"status": "generating", "progress": 30, "message": "Tailoring resume..."}
        
        # Run the synchronous generation in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            generate_application,
            company, role, job_description, url
        )
        
        generation_status[task_id] = {
            "status": "complete",
            "progress": 100,
            "result": result
        }
    except Exception as e:
        generation_status[task_id] = {
            "status": "error",
            "progress": 0,
            "error": str(e)
        }


@app.get("/status/{task_id}", response_class=HTMLResponse)
async def get_status(request: Request, task_id: str):
    """Get generation status as HTML partial"""
    status = generation_status.get(task_id, {"status": "unknown"})
    
    if status["status"] == "complete":
        return templates.TemplateResponse("partials/complete.html", {
            "request": request,
            "result": status["result"]
        })
    elif status["status"] == "error":
        return templates.TemplateResponse("partials/generate_error.html", {
            "request": request,
            "error": status.get("error", "Unknown error")
        })
    else:
        return templates.TemplateResponse("partials/progress.html", {
            "request": request,
            "task_id": task_id,
            "progress": status.get("progress", 0),
            "message": status.get("message", "Processing...")
        })


@app.get("/download/{company_slug}/{filename}")
async def download_file(company_slug: str, filename: str):
    """Download a generated file"""
    file_path = get_companies_dir() / company_slug / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@app.get("/application/{company_slug}", response_class=HTMLResponse)
async def view_application(request: Request, company_slug: str):
    """View a specific application's files"""
    company_dir = get_companies_dir() / company_slug
    
    if not company_dir.exists():
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get all files
    files = []
    company_name = company_slug.replace("-", " ").title()
    role = ""
    url = ""
    
    for f in sorted(company_dir.iterdir(), reverse=True):
        if f.name.startswith("."):
            continue
        
        file_type = "other"
        if "resume" in f.name:
            file_type = "resume"
        elif "cover-letter" in f.name:
            file_type = "cover_letter"
        elif "job-description" in f.name:
            file_type = "job_description"
            # Read to get role
            content = f.read_text()
            for line in content.split("\n")[:5]:
                if line.startswith("Role:"):
                    role = line.replace("Role:", "").strip()
                elif line.startswith("URL:"):
                    url = line.replace("URL:", "").strip()
        elif "questions" in f.name:
            file_type = "questions"
        
        files.append({
            "name": f.name,
            "type": file_type,
            "size": f.stat().st_size,
            "is_docx": f.suffix == ".docx"
        })
    
    return templates.TemplateResponse("application.html", {
        "request": request,
        "company_slug": company_slug,
        "company_name": company_name,
        "role": role,
        "url": url,
        "files": files
    })


@app.get("/api/applications")
async def api_list_applications():
    """API endpoint to list applications as JSON"""
    return list_applications()


@app.get("/profile", response_class=HTMLResponse)
async def view_profile(request: Request):
    """View and edit the master professional profile"""
    profile = load_profile()
    
    # If no profile exists, show setup wizard
    if not profile:
        return templates.TemplateResponse("profile_setup.html", {
            "request": request
        })
    
    # Read raw YAML for editing
    profile_path = BASE_PATH / "profile.yaml"
    raw_yaml = ""
    if profile_path.exists():
        raw_yaml = profile_path.read_text()
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "profile": profile,
        "raw_yaml": raw_yaml,
        "has_profile": bool(profile)
    })


@app.post("/profile/setup", response_class=HTMLResponse)
async def setup_profile(request: Request):
    """Handle initial profile setup from wizard (supports multiple jobs, education, projects, awards)"""
    import yaml
    from fastapi.responses import RedirectResponse
    
    try:
        form_data = await request.form()
        form_dict = dict(form_data)
        
        profile = {
            "personal": {
                "name": form_dict.get("personal_name", ""),
                "email": form_dict.get("personal_email", ""),
                "phone": form_dict.get("personal_phone", ""),
                "location": form_dict.get("personal_location", ""),
                "linkedin_url": form_dict.get("personal_linkedin", ""),
                "website": form_dict.get("personal_website", ""),
                "summaries": {
                    "default": form_dict.get("personal_summary", "")
                }
            },
            "skills": {
                "categories": []
            },
            "experience": [],
            "education": [],
            "projects": [],
            "awards": [],
            "key_metrics": []
        }
        
        # Skills categories
        for key, name in [("skills_technical", "Technical Skills"), ("skills_domain", "Domain Expertise"), ("skills_soft", "Soft Skills"), ("skills_certifications", "Certifications")]:
            val = form_dict.get(key, "")
            if val and val.strip():
                profile["skills"]["categories"].append({
                    "name": name,
                    "items": [s.strip() for s in val.split(",") if s.strip()]
                })
        
        # Multiple work experience entries
        job_count = int(form_dict.get("job_count", "0"))
        for i in range(job_count):
            company = form_dict.get(f"job_{i}_company", "").strip()
            title = form_dict.get(f"job_{i}_title", "").strip()
            if company and title:
                highlights_raw = form_dict.get(f"job_{i}_highlights", "")
                highlights = [h.strip() for h in highlights_raw.split("\n") if h.strip()] if highlights_raw else []
                profile["experience"].append({
                    "company": company,
                    "location": form_dict.get(f"job_{i}_location", "").strip(),
                    "roles": [{
                        "title": title,
                        "dates": form_dict.get(f"job_{i}_dates", "").strip(),
                        "highlights": highlights
                    }]
                })
        
        # Multiple education entries
        edu_count = int(form_dict.get("edu_count", "0"))
        for i in range(edu_count):
            degree = form_dict.get(f"edu_{i}_degree", "").strip()
            institution = form_dict.get(f"edu_{i}_institution", "").strip()
            if degree or institution:
                entry = {
                    "degree": degree,
                    "institution": institution,
                    "years": form_dict.get(f"edu_{i}_years", "").strip(),
                }
                honors = form_dict.get(f"edu_{i}_honors", "").strip()
                if honors:
                    entry["honors"] = honors
                profile["education"].append(entry)
        
        # Multiple project entries
        proj_count = int(form_dict.get("proj_count", "0"))
        for i in range(proj_count):
            name = form_dict.get(f"proj_{i}_name", "").strip()
            if name:
                achievements_raw = form_dict.get(f"proj_{i}_achievements", "")
                achievements = [a.strip() for a in achievements_raw.split("\n") if a.strip()] if achievements_raw else []
                tech_raw = form_dict.get(f"proj_{i}_technologies", "")
                technologies = [t.strip() for t in tech_raw.split(",") if t.strip()] if tech_raw else []
                profile["projects"].append({
                    "name": name,
                    "type": form_dict.get(f"proj_{i}_type", "work"),
                    "description": form_dict.get(f"proj_{i}_description", "").strip(),
                    "achievements": achievements,
                    "technologies": technologies
                })
        
        # Multiple award entries
        award_count = int(form_dict.get("award_count", "0"))
        for i in range(award_count):
            name = form_dict.get(f"award_{i}_name", "").strip()
            if name:
                entry = {
                    "name": name,
                    "date": form_dict.get(f"award_{i}_date", "").strip(),
                    "description": form_dict.get(f"award_{i}_description", "").strip()
                }
                org = form_dict.get(f"award_{i}_organization", "").strip()
                if org:
                    entry["organization"] = org
                profile["awards"].append(entry)
        
        profile_path = BASE_PATH / "profile.yaml"
        with open(profile_path, "w") as f:
            yaml.dump(profile, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        return RedirectResponse(url="/profile", status_code=303)
        
    except Exception as e:
        return templates.TemplateResponse("profile_setup.html", {
            "request": request,
            "error": str(e)
        })


@app.post("/profile/save", response_class=HTMLResponse)
async def save_profile_handler(request: Request):
    """Save updated profile from form data or raw YAML.
    
    Handles array-style form fields (name[]) for experience, education,
    projects, awards, and metrics submitted from the profile editor.
    """
    import yaml
    
    try:
        form_data = await request.form()
        # Use getlist for array fields, dict for scalar fields
        form_dict = dict(form_data)
        
        def getlist(key):
            """Extract all values for a repeated form field name."""
            return [v for k, v in form_data.multi_items() if k == key]
        
        # Check if raw YAML was submitted
        if "profile_yaml" in form_dict and form_dict.get("profile_yaml", "").strip():
            profile_yaml = form_dict["profile_yaml"]
            yaml.safe_load(profile_yaml)  # validate
            
            profile_path = BASE_PATH / "profile.yaml"
            with open(profile_path, "w") as f:
                f.write(profile_yaml)
        else:
            profile = load_profile() or {}
            
            # --- Personal info ---
            if "personal" not in profile:
                profile["personal"] = {}
            
            for form_key, profile_key in [
                ("personal_name", "name"),
                ("personal_location", "location"),
                ("personal_email", "email"),
                ("personal_phone", "phone"),
                ("personal_linkedin", "linkedin_url"),
                ("personal_website", "website"),
            ]:
                if form_key in form_dict:
                    profile["personal"][profile_key] = form_dict[form_key]
            
            # --- Summaries ---
            if "summaries" not in profile["personal"]:
                profile["personal"]["summaries"] = {}
            
            for form_key, summary_key in [
                ("personal_summary", "default"),
                ("summary_automation", "automation_focused"),
                ("summary_ai", "ai_focused"),
                ("summary_support", "support_focused"),
            ]:
                if form_key in form_dict:
                    profile["personal"]["summaries"][summary_key] = form_dict[form_key]
            
            # --- Skills (comma-separated lists) ---
            if "skills" in profile and "categories" in profile["skills"]:
                for i, category in enumerate(profile["skills"]["categories"]):
                    form_key = f"skills_{i}"
                    if form_key in form_dict and form_dict[form_key]:
                        profile["skills"]["categories"][i]["items"] = [
                            s.strip() for s in form_dict[form_key].split(",") if s.strip()
                        ]
            
            # --- Experience (array fields) ---
            companies = getlist("exp_company[]")
            titles = getlist("exp_title[]")
            dates_list = getlist("exp_dates[]")
            locations = getlist("exp_location[]")
            highlights_list = getlist("exp_highlights[]")
            
            if companies:
                profile["experience"] = []
                for i, company in enumerate(companies):
                    company = company.strip()
                    title = titles[i].strip() if i < len(titles) else ""
                    if not company and not title:
                        continue
                    highlights_raw = highlights_list[i] if i < len(highlights_list) else ""
                    highlights = [h.strip() for h in highlights_raw.split("\n") if h.strip()]
                    profile["experience"].append({
                        "company": company,
                        "location": locations[i].strip() if i < len(locations) else "",
                        "roles": [{
                            "title": title,
                            "dates": dates_list[i].strip() if i < len(dates_list) else "",
                            "highlights": highlights,
                        }]
                    })
            
            # --- Education (array fields) ---
            edu_degrees = getlist("education_degree[]")
            edu_institutions = getlist("education_institution[]")
            edu_years = getlist("education_years[]")
            edu_honors = getlist("education_honors[]")
            
            if edu_degrees:
                profile["education"] = []
                for i, degree in enumerate(edu_degrees):
                    degree = degree.strip()
                    institution = edu_institutions[i].strip() if i < len(edu_institutions) else ""
                    if not degree and not institution:
                        continue
                    entry = {
                        "degree": degree,
                        "institution": institution,
                        "years": edu_years[i].strip() if i < len(edu_years) else "",
                    }
                    honors = edu_honors[i].strip() if i < len(edu_honors) else ""
                    if honors:
                        entry["honors"] = honors
                    profile["education"].append(entry)
            
            # --- Projects (array fields) ---
            proj_names = getlist("project_name[]")
            proj_types = getlist("project_type[]")
            proj_descriptions = getlist("project_description[]")
            proj_achievements = getlist("project_achievements[]")
            proj_technologies = getlist("project_technologies[]")
            
            if proj_names:
                profile["projects"] = []
                for i, name in enumerate(proj_names):
                    name = name.strip()
                    if not name:
                        continue
                    ach_raw = proj_achievements[i] if i < len(proj_achievements) else ""
                    tech_raw = proj_technologies[i] if i < len(proj_technologies) else ""
                    profile["projects"].append({
                        "name": name,
                        "type": proj_types[i] if i < len(proj_types) else "work",
                        "description": proj_descriptions[i].strip() if i < len(proj_descriptions) else "",
                        "achievements": [a.strip() for a in ach_raw.split("\n") if a.strip()],
                        "technologies": [t.strip() for t in tech_raw.split(",") if t.strip()],
                    })
            
            # --- Awards (array fields) ---
            award_names = getlist("award_name[]")
            award_dates = getlist("award_date[]")
            award_orgs = getlist("award_organization[]")
            award_descs = getlist("award_description[]")
            
            if award_names:
                profile["awards"] = []
                for i, name in enumerate(award_names):
                    name = name.strip()
                    if not name:
                        continue
                    entry = {
                        "name": name,
                        "date": award_dates[i].strip() if i < len(award_dates) else "",
                        "description": award_descs[i].strip() if i < len(award_descs) else "",
                    }
                    org = award_orgs[i].strip() if i < len(award_orgs) else ""
                    if org:
                        entry["organization"] = org
                    profile["awards"].append(entry)
            
            # --- Key Metrics (array fields) ---
            metric_names = getlist("metric_name[]")
            metric_values = getlist("metric_value[]")
            metric_contexts = getlist("metric_context[]")
            
            if metric_names:
                profile["key_metrics"] = []
                for i, name in enumerate(metric_names):
                    name = name.strip()
                    if not name:
                        continue
                    profile["key_metrics"].append({
                        "metric": name,
                        "value": metric_values[i].strip() if i < len(metric_values) else "",
                        "context": metric_contexts[i].strip() if i < len(metric_contexts) else "",
                    })
            
            # Save
            profile_path = BASE_PATH / "profile.yaml"
            with open(profile_path, "w") as f:
                yaml.dump(profile, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        return templates.TemplateResponse("partials/profile_saved.html", {
            "request": request,
            "success": True,
            "message": "Profile saved successfully"
        })
    except yaml.YAMLError as e:
        return templates.TemplateResponse("partials/profile_saved.html", {
            "request": request,
            "success": False,
            "message": f"Invalid YAML: {str(e)}"
        })
    except Exception as e:
        return templates.TemplateResponse("partials/profile_saved.html", {
            "request": request,
            "success": False,
            "message": f"Error saving profile: {str(e)}"
        })


@app.get("/api/profile")
async def api_get_profile():
    """API endpoint to get profile as JSON"""
    return load_profile()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

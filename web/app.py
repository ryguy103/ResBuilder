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
    """Handle initial profile setup from wizard"""
    import yaml
    from fastapi.responses import RedirectResponse
    
    try:
        form_data = await request.form()
        form_dict = dict(form_data)
        
        # Build profile structure
        profile = {
            "personal": {
                "name": form_dict.get("personal_name", ""),
                "email": form_dict.get("personal_email", ""),
                "phone": form_dict.get("personal_phone", ""),
                "location": form_dict.get("personal_location", ""),
                "linkedin_url": form_dict.get("personal_linkedin", ""),
                "summaries": {
                    "default": form_dict.get("personal_summary", "")
                }
            },
            "skills": {
                "categories": []
            },
            "experience": [],
            "projects": [],
            "awards": [],
            "key_metrics": []
        }
        
        # Add skills categories
        if form_dict.get("skills_technical"):
            profile["skills"]["categories"].append({
                "name": "Technical Skills",
                "items": [s.strip() for s in form_dict["skills_technical"].split(",") if s.strip()]
            })
        if form_dict.get("skills_domain"):
            profile["skills"]["categories"].append({
                "name": "Domain Expertise",
                "items": [s.strip() for s in form_dict["skills_domain"].split(",") if s.strip()]
            })
        if form_dict.get("skills_soft"):
            profile["skills"]["categories"].append({
                "name": "Soft Skills",
                "items": [s.strip() for s in form_dict["skills_soft"].split(",") if s.strip()]
            })
        
        # Add work experience
        if form_dict.get("job_company") and form_dict.get("job_title"):
            highlights = []
            if form_dict.get("job_highlights"):
                highlights = [h.strip() for h in form_dict["job_highlights"].split("\n") if h.strip()]
            
            profile["experience"].append({
                "company": form_dict["job_company"],
                "location": form_dict.get("job_location", ""),
                "roles": [{
                    "title": form_dict["job_title"],
                    "dates": form_dict.get("job_dates", ""),
                    "highlights": highlights
                }]
            })
        
        # Save profile
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
    """Save updated profile from form data or raw YAML"""
    import yaml
    
    try:
        form_data = await request.form()
        form_dict = dict(form_data)
        
        # Check if raw YAML was submitted
        if "profile_yaml" in form_dict and form_dict.get("profile_yaml", "").strip():
            # Raw YAML mode - validate and save directly
            profile_yaml = form_dict["profile_yaml"]
            profile = yaml.safe_load(profile_yaml)
            
            profile_path = BASE_PATH / "profile.yaml"
            with open(profile_path, "w") as f:
                f.write(profile_yaml)
        else:
            # Form mode - load existing, update fields, save
            profile = load_profile() or {}
            
            # Update personal info
            if "personal" not in profile:
                profile["personal"] = {}
            
            if "personal_name" in form_dict:
                profile["personal"]["name"] = form_dict["personal_name"]
            if "personal_location" in form_dict:
                profile["personal"]["location"] = form_dict["personal_location"]
            if "personal_email" in form_dict:
                profile["personal"]["email"] = form_dict["personal_email"]
            if "personal_phone" in form_dict:
                profile["personal"]["phone"] = form_dict["personal_phone"]
            if "personal_linkedin" in form_dict:
                profile["personal"]["linkedin_url"] = form_dict["personal_linkedin"]
            
            # Update summaries
            if "summaries" not in profile["personal"]:
                profile["personal"]["summaries"] = {}
            
            if "personal_summary" in form_dict:
                profile["personal"]["summaries"]["default"] = form_dict["personal_summary"]
            if "summary_automation" in form_dict:
                profile["personal"]["summaries"]["automation_focused"] = form_dict["summary_automation"]
            if "summary_ai" in form_dict:
                profile["personal"]["summaries"]["ai_focused"] = form_dict["summary_ai"]
            if "summary_support" in form_dict:
                profile["personal"]["summaries"]["support_focused"] = form_dict["summary_support"]
            
            # Update skills (comma-separated lists)
            if "skills" in profile and "categories" in profile["skills"]:
                for i, category in enumerate(profile["skills"]["categories"]):
                    form_key = f"skills_{i}"
                    if form_key in form_dict and form_dict[form_key]:
                        skills_list = [s.strip() for s in form_dict[form_key].split(",") if s.strip()]
                        profile["skills"]["categories"][i]["items"] = skills_list
            
            # Save updated profile
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

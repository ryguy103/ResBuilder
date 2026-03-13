#!/usr/bin/env python3
"""
prepare.py - Tailor resume and cover letter for a job application
Generates .docx files ready to submit
"""

import os
import re
import sys
import subprocess
import platform
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    print("Missing dependency. Run: pip install python-docx")
    sys.exit(1)

try:
    from anthropic import Anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic")
    sys.exit(1)

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING = True
except ImportError:
    HAS_SCRAPING = False


def scrape_job_posting(url: str) -> dict:
    """Scrape job description from a URL. Returns dict with 'content', 'company', 'role'."""
    if not HAS_SCRAPING:
        print("Missing dependencies. Run: pip install requests beautifulsoup4")
        return None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove script, style, nav, footer elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    # Try to extract company and role from common patterns
    company = None
    role = None
    
    # Look for title tag
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        # Common patterns: "Role at Company", "Role - Company", "Company | Role"
        if ' at ' in title_text:
            parts = title_text.split(' at ', 1)
            role = parts[0].strip()
            company = parts[1].split('|')[0].split('-')[0].strip()
        elif ' - ' in title_text:
            parts = title_text.split(' - ')
            role = parts[0].strip()
            if len(parts) > 1:
                company = parts[1].strip()
        elif ' | ' in title_text:
            parts = title_text.split(' | ')
            role = parts[0].strip()
            if len(parts) > 1:
                company = parts[1].strip()
    
    # Look for structured data (JSON-LD)
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld:
        try:
            import json
            data = json.loads(json_ld.string)
            if isinstance(data, list):
                data = data[0]
            if data.get('@type') == 'JobPosting':
                role = role or data.get('title')
                if data.get('hiringOrganization'):
                    company = company or data['hiringOrganization'].get('name')
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    # Extract main content - look for common job posting containers
    content_selectors = [
        'article',
        '[class*="job-description"]',
        '[class*="jobDescription"]',
        '[class*="job-content"]',
        '[class*="posting-"]',
        '[data-automation*="job"]',
        'main',
        '.content',
        '#content',
    ]
    
    main_content = None
    for selector in content_selectors:
        try:
            main_content = soup.select_one(selector)
            if main_content and len(main_content.get_text(strip=True)) > 200:
                break
        except:
            continue
    
    if not main_content:
        main_content = soup.body if soup.body else soup
    
    # Get text content
    text = main_content.get_text(separator='\n', strip=True)
    
    # Clean up excessive whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    content = '\n'.join(lines)
    
    # Truncate if too long (some pages have lots of extra content)
    if len(content) > 15000:
        content = content[:15000] + "\n\n[Content truncated...]"
    
    if len(content) < 100:
        print("Warning: Extracted content seems too short. The page may require JavaScript.")
        return None
    
    return {
        'content': content,
        'company': company,
        'role': role,
        'url': url
    }


def get_api_key():
    """Get Anthropic API key from environment"""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Get your key at: https://console.anthropic.com/")
        print("Then run: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    return key


def load_profile():
    """Load the master profile from profile.yaml"""
    try:
        import yaml
        profile_path = Path(__file__).parent / "profile.yaml"
        if profile_path.exists():
            with open(profile_path, "r") as f:
                return yaml.safe_load(f) or {}
    except ImportError:
        pass
    return {}


def get_candidate_name():
    """Get the candidate's name from the profile."""
    return load_profile().get("personal", {}).get("name", "the candidate")


def read_master_resume():
    """Read the master resume content, preferring profile.yaml over resume.md"""
    profile = load_profile()
    if profile:
        from core import format_profile_for_ai
        return format_profile_for_ai(profile)

    resume_path = Path(__file__).parent / "resume.md"
    if not resume_path.exists():
        print("Error: No profile.yaml or resume.md found.")
        print("Set up your profile at http://localhost:8000/profile")
        sys.exit(1)
    with open(resume_path, "r") as f:
        return f.read()


def get_job_description(company: str = None, scraped_data: dict = None):
    """Get job description from URL, company folder, or jd.txt file"""
    
    # If we have scraped data, use it
    if scraped_data and scraped_data.get('content'):
        return scraped_data['content']
    
    # Check for existing JD in company folder first
    if company:
        company_slug = company.lower().replace(" ", "-").replace(".", "")
        company_dir = Path("companies") / company_slug
        
        if company_dir.exists():
            # Find the most recent job description file
            jd_files = sorted(company_dir.glob("*--job-description.txt"), reverse=True)
            if jd_files:
                existing_jd = jd_files[0]
                # Read content, skipping the header (first 4 lines)
                full_content = existing_jd.read_text()
                lines = full_content.split("\n")
                # Find where the header ends (after the === line)
                content_start = 0
                for i, line in enumerate(lines):
                    if line.startswith("=" * 10):
                        content_start = i + 2  # Skip the === line and blank line
                        break
                jd_content = "\n".join(lines[content_start:]).strip()
                
                if jd_content:
                    print(f"\nFound existing JD for {company} in {existing_jd.name}")
                    print(f"  ({len(jd_content)} chars)")
                    use_existing = input("Use this JD? [Y/n]: ").strip().lower()
                    if use_existing != 'n':
                        return jd_content
    
    # Fall back to jd.txt
    jd_file = Path("jd.txt")
    
    # Check if jd.txt exists and has content
    if jd_file.exists():
        content = jd_file.read_text().strip()
        if content and "PASTE THE JOB DESCRIPTION HERE" not in content:
            print(f"\nFound job description in jd.txt ({len(content)} chars)")
            use_existing = input("Use this JD? [Y/n]: ").strip().lower()
            if use_existing != 'n':
                return content
    
    # Open editor for user to paste JD
    print("\n" + "=" * 60)
    print("PASTE JOB DESCRIPTION INTO jd.txt")
    print("=" * 60)
    print("\nOpening jd.txt for you to paste the job description...")
    print("Save and close the file when done.\n")
    
    # Clear the file first
    jd_file.write_text("")
    
    # Open in default editor
    if platform.system() == "Darwin":  # macOS
        # Try VS Code first, then TextEdit
        try:
            subprocess.run(["code", "--wait", str(jd_file)], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["open", "-t", "-W", str(jd_file)], check=True)
    else:
        # Linux/other
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(jd_file)], check=True)
    
    # Read the content
    content = jd_file.read_text().strip()
    if not content:
        print("Error: jd.txt is empty")
        sys.exit(1)
    
    print(f"✓ Loaded job description ({len(content)} chars)")
    return content


def get_job_input() -> dict:
    """Get job posting via URL or manual entry. Returns dict with url, company, role, content."""
    print("\n" + "=" * 60)
    print("JOB INPUT")
    print("=" * 60)
    
    if HAS_SCRAPING:
        print("\nOptions:")
        print("  1. Paste a job posting URL")
        print("  2. Enter company/role manually")
        choice = input("\nChoice [1/2]: ").strip()
        
        if choice == "1" or choice.startswith("http"):
            url = choice if choice.startswith("http") else input("Job posting URL: ").strip()
            
            if url:
                scraped = scrape_job_posting(url)
                if scraped:
                    print(f"\n✓ Scraped job posting ({len(scraped['content'])} chars)")
                    
                    # Show extracted info and let user confirm/edit
                    company = scraped.get('company') or ''
                    role = scraped.get('role') or ''
                    
                    print(f"\nExtracted info:")
                    if company:
                        print(f"  Company: {company}")
                    if role:
                        print(f"  Role: {role}")
                    
                    # Let user confirm or override
                    print("\nConfirm or edit (press Enter to keep):")
                    company_input = input(f"  Company [{company}]: ").strip()
                    role_input = input(f"  Role [{role}]: ").strip()
                    
                    return {
                        'url': url,
                        'company': company_input or company,
                        'role': role_input or role,
                        'content': scraped['content']
                    }
                else:
                    print("Failed to scrape URL. Falling back to manual entry.")
    
    # Manual entry
    company = input("\nCompany name: ").strip()
    role = input("Role title: ").strip()
    
    return {
        'url': None,
        'company': company,
        'role': role,
        'content': None
    }


def get_company_and_role():
    """Get company name and role from user (legacy function for compatibility)"""
    print("\n" + "=" * 60)
    company = input("Company name: ").strip()
    role = input("Role title: ").strip()
    return company, role


def get_application_questions() -> list:
    """Collect additional application questions from user"""
    questions = []
    
    print("\n" + "=" * 60)
    has_questions = input("Are there additional application questions? [y/N]: ").strip().lower()
    
    if has_questions != 'y':
        return questions
    
    print("\nEnter each question (press Enter twice when done with each):")
    print("Type 'done' when finished with all questions.\n")
    
    while True:
        print("-" * 40)
        question = input("Question: ").strip()
        
        if question.lower() == 'done' or not question:
            break
        
        questions.append(question)
        print(f"  ✓ Added question #{len(questions)}")
        
        another = input("\nAnother question? [y/N]: ").strip().lower()
        if another != 'y':
            break
    
    if questions:
        print(f"\n✓ Collected {len(questions)} question(s)")
    
    return questions


def answer_questions_with_ai(questions: list, master_resume: str, job_description: str, company: str, role: str, interactive: bool = False) -> list:
    """Answer application questions one at a time, asking for clarification when needed"""
    if not questions:
        return []
    
    client = Anthropic(api_key=get_api_key())
    answers = []
    
    # Build base context dynamically from profile
    base_context = f"""CANDIDATE: {get_candidate_name()}
COMPANY: {company}
ROLE: {role}

CANDIDATE'S FULL RESUME:
{master_resume}

KEY COMPANY CONTEXT FROM JD:
{job_description[:1500]}"""

    print(f"\nAnswering {len(questions)} question(s)...\n")
    
    for i, question in enumerate(questions, 1):
        print(f"{'='*50}")
        print(f"Question {i}/{len(questions)}:")
        print(f"  {question}")
        print(f"{'='*50}")
        
        # Step 1: Check if we need more info (lightweight call)
        check_prompt = f"""{base_context}

QUESTION: {question}

Can you write a strong, specific answer using only the context above?
- If YES: Reply with ANSWER: [your 2-4 sentence answer]
- If NO: Reply with ASK: [one specific question to ask the candidate]

Only ask if the question requires personal insight not in the resume (motivations, specific stories, future goals)."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": check_prompt}]
        )
        
        result = response.content[0].text.strip()
        
        # Step 2: Handle based on response
        if result.startswith("ASK:") and interactive:
            clarifying_question = result.replace("ASK:", "").strip()
            print(f"\n  → Need your input: {clarifying_question}")
            user_input = input("\n  Your answer: ").strip()
            
            if user_input:
                # Generate answer with user's input
                answer_prompt = f"""{base_context}

QUESTION: {question}
CANDIDATE'S INPUT: {user_input}

Write a compelling 2-4 sentence answer in first person. Incorporate the candidate's input naturally. Be authentic, not generic."""

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=300,
                    messages=[{"role": "user", "content": answer_prompt}]
                )
                answer = response.content[0].text.strip()
            else:
                # User skipped - generate best effort
                answer = result.replace("ASK:", "").strip() if len(result) > 60 else f"[Needs personal input - skipped]"
        
        elif result.startswith("ANSWER:"):
            answer = result.replace("ANSWER:", "").strip()
        
        else:
            # Use response as-is if it looks like an answer
            answer = result
        
        answers.append({"question": question, "answer": answer})
        print(f"\n  ✓ Answer:")
        print(f"  {answer[:200]}{'...' if len(answer) > 200 else ''}\n")
    
    return answers


def tailor_resume_with_ai(master_resume: str, job_description: str, company: str, role: str) -> str:
    """Use Claude to tailor the resume - focused single task"""
    client = Anthropic(api_key=get_api_key())
    
    prompt = f"""You are tailoring a resume for a specific job application.

RULES:
1. KEYWORD ALIGNMENT: Use terms from the JD where the candidate has genuine experience
2. REORDER BULLETS: Put the most relevant accomplishments first  
3. PRESERVE METRICS: Always keep $250K savings and 90 min to 3 min response time
4. NO FABRICATION: Only use keywords where there's real experience
5. ACTIVE VOICE: No "exposure to" or "familiar with"
6. Output plain text only, use hyphens (-) for bullet points

MASTER RESUME:
{master_resume}

JOB DESCRIPTION:
{job_description}

COMPANY: {company}
ROLE: {role}

Output the tailored resume in this order:
1. Name and contact info
2. Summary (2-3 sentences tailored to this role)
3. Professional Experience (reordered bullets)
4. Technical Skills
5. Selected Projects
6. Education

Output ONLY the resume content, no explanations or markdown."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text.strip()


def generate_cover_letter_with_ai(master_resume: str, job_description: str, company: str, role: str) -> str:
    """Use Claude to generate cover letter - focused single task"""
    client = Anthropic(api_key=get_api_key())
    
    prompt = f"""You are writing a cover letter for a job application.

CONTEXT:
- Candidate: {get_candidate_name()}
- Company: {company}
- Role: {role}

CANDIDATE'S RESUME:
{master_resume}

JOB DESCRIPTION:
{job_description}

COVER LETTER REQUIREMENTS:
1. Start with "Hi [appropriate name from JD] and team," (research who's hiring)
2. Opening: State the role, show genuine interest (2-3 sentences)
3. Body 1: Connect 2-3 specific accomplishments to their needs, include a metric
4. Body 2: Why this specific company (reference something specific, not generic)
5. Closing: Brief call to action, thank them
6. Keep under 350 words total
7. Tone: Professional but warm, authentic not robotic
8. End with "Sincerely," and the name

Output ONLY the cover letter content, no explanations."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text.strip()


def tailor_with_ai(master_resume: str, job_description: str, company: str, role: str) -> dict:
    """Orchestrate resume and cover letter generation as separate focused calls"""
    
    print("\n[1/2] Tailoring resume...")
    resume = tailor_resume_with_ai(master_resume, job_description, company, role)
    
    print("[2/2] Generating cover letter...")
    cover_letter = generate_cover_letter_with_ai(master_resume, job_description, company, role)
    
    return {"resume": resume, "cover_letter": cover_letter}


def strip_markdown_headings(line: str) -> str:
    """Remove markdown heading markers (# ## ### ####)"""
    return re.sub(r'^#{1,6}\s*', '', line)


def strip_markdown_links(text: str) -> str:
    """Convert [text](url) to just text"""
    return re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)


def add_formatted_text(paragraph, text: str, font_size: int = 10, base_bold: bool = False, base_italic: bool = False, color: RGBColor = None):
    """Add text to paragraph with markdown bold/italic converted to proper formatting"""
    # Strip markdown links first
    text = strip_markdown_links(text)
    
    # Pattern to match **bold**, *italic*, or plain text segments
    pattern = r'(\*\*[^*]+\*\*|\*[^*]+\*|[^*]+)'
    segments = re.findall(pattern, text)
    
    for segment in segments:
        if not segment:
            continue
            
        is_bold = base_bold
        is_italic = base_italic
        clean_text = segment
        
        # Check for bold (**text**)
        if segment.startswith('**') and segment.endswith('**'):
            is_bold = True
            clean_text = segment[2:-2]
        # Check for italic (*text*)
        elif segment.startswith('*') and segment.endswith('*') and len(segment) > 2:
            is_italic = True
            clean_text = segment[1:-1]
        
        if clean_text:
            run = paragraph.add_run(clean_text)
            run.font.size = Pt(font_size)
            run.bold = is_bold
            run.italic = is_italic
            if color:
                run.font.color.rgb = color


def create_docx(content: str, filename: str, is_cover_letter: bool = False):
    """Create a nicely formatted .docx file"""
    doc = Document()
    
    # Set margins
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
    
    lines = content.split("\n")
    i = 0
    first_line = True
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines but add spacing
        if not line:
            i += 1
            continue
        
        # Skip separator lines
        if line.startswith("===") or line.startswith("---") or line.startswith("___"):
            i += 1
            continue
        
        # Strip markdown heading markers
        clean_line = strip_markdown_headings(line)
        
        p = doc.add_paragraph()
        
        # NAME (first non-empty line or # heading)
        if first_line and not clean_line.startswith("-"):
            add_formatted_text(p, clean_line, font_size=18, base_bold=True, color=RGBColor(0, 51, 102))
            p.paragraph_format.space_after = Pt(2)
            first_line = False
        
        # CONTACT INFO (second line, contains | or @)
        elif ("|" in clean_line or "@" in clean_line) and i < 5:
            add_formatted_text(p, clean_line, font_size=10, color=RGBColor(80, 80, 80))
            p.paragraph_format.space_after = Pt(12)
        
        # SECTION HEADERS (all caps or ## headings)
        elif clean_line.isupper() and len(clean_line) > 3:
            add_formatted_text(p, clean_line, font_size=11, base_bold=True, color=RGBColor(0, 51, 102))
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            border_p = doc.add_paragraph()
            border_p.paragraph_format.space_after = Pt(6)
        
        # MARKDOWN ## HEADERS (Professional Experience, Technical Skills, etc.)
        elif line.startswith("## "):
            header_text = clean_line.upper()
            add_formatted_text(p, header_text, font_size=11, base_bold=True, color=RGBColor(0, 51, 102))
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
        
        # MARKDOWN ### HEADERS (Company names)
        elif line.startswith("### "):
            add_formatted_text(p, clean_line, font_size=11, base_bold=True)
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(2)
        
        # MARKDOWN #### HEADERS (Job titles)
        elif line.startswith("#### "):
            add_formatted_text(p, clean_line, font_size=10, base_bold=True)
            p.paragraph_format.space_after = Pt(1)
        
        # COMPANY NAME (contains "Zapier" or company indicators, not a bullet)
        elif ("Zapier" in clean_line or "Remote" in clean_line) and not clean_line.startswith("-"):
            add_formatted_text(p, clean_line, font_size=11, base_bold=True)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
        
        # JOB TITLE (contains title keywords)
        elif any(title in clean_line for title in ["Lead", "Specialist", "Owner", "Manager", "Engineer", "Program"]) and not clean_line.startswith("-") and "Zapier" not in clean_line:
            add_formatted_text(p, clean_line, font_size=10, base_bold=True)
            p.paragraph_format.space_after = Pt(1)
        
        # DATES (contains year patterns or *italic dates*)
        elif (any(year in clean_line for year in ["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "Present"]) and len(clean_line) < 40 and not clean_line.startswith("-")) or (line.startswith("*") and line.endswith("*") and "–" in line):
            # Strip italic markers from dates
            date_text = clean_line.strip("*")
            run = p.add_run(date_text)
            run.italic = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(100, 100, 100)
            p.paragraph_format.space_after = Pt(6)
        
        # BULLET POINTS
        elif clean_line.startswith("-") or clean_line.startswith("•"):
            bullet_text = clean_line.lstrip("-•").strip()
            p.add_run("• ")
            add_formatted_text(p, bullet_text, font_size=10)
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_after = Pt(4)
        
        # SKILLS LINE (contains colon)
        elif ":" in clean_line and not clean_line.startswith("-") and "|" not in clean_line:
            parts = clean_line.split(":", 1)
            if len(parts) == 2:
                # Strip any bold markers from the label
                label = parts[0].strip("*")
                run1 = p.add_run(label + ":")
                run1.bold = True
                run1.font.size = Pt(10)
                add_formatted_text(p, parts[1], font_size=10)
                p.paragraph_format.space_after = Pt(3)
            else:
                add_formatted_text(p, clean_line, font_size=10)
                p.paragraph_format.space_after = Pt(4)
        
        # PROJECT TITLES
        elif ("Framework" in clean_line or "Platform" in clean_line or "Project" in clean_line) and len(clean_line) < 60 and not clean_line.startswith("-"):
            add_formatted_text(p, clean_line, font_size=10, base_bold=True)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
        
        # SUMMARY TEXT (longer paragraphs)
        elif len(clean_line) > 100:
            add_formatted_text(p, clean_line, font_size=10)
            p.paragraph_format.space_after = Pt(8)
        
        # DEFAULT
        else:
            add_formatted_text(p, clean_line, font_size=10)
            p.paragraph_format.space_after = Pt(4)
        
        i += 1
    
    doc.save(filename)
    print(f"  Created: {filename}")


def questions_only_mode():
    """Run in questions-only mode - skip resume/cover letter generation"""
    print("\n" + "=" * 60)
    print("ResBuilder - Application Questions Mode")
    print("=" * 60)
    
    # Get job input (URL or manual)
    job_input = get_job_input()
    company = job_input['company']
    role = job_input['role']
    
    if not company or not role:
        print("Error: Company and role are required")
        sys.exit(1)
    
    jd = get_job_description(company, job_input)
    
    if not jd:
        print("Error: No job description provided")
        sys.exit(1)
    
    # Read master resume for context
    master_resume = read_master_resume()
    
    # Get questions (force the prompt)
    print("\n" + "=" * 60)
    print("Enter application questions:")
    print("Type 'done' when finished.\n")
    
    questions = []
    while True:
        print("-" * 40)
        question = input("Question: ").strip()
        
        if question.lower() == 'done' or not question:
            break
        
        questions.append(question)
        print(f"  ✓ Added question #{len(questions)}")
    
    if not questions:
        print("No questions entered. Exiting.")
        sys.exit(0)
    
    print(f"\n✓ Collected {len(questions)} question(s)")
    
    # Answer questions with interactive mode enabled
    qa_answers = answer_questions_with_ai(questions, master_resume, jd, company, role, interactive=True)
    
    # Create company folder
    date_str = datetime.now().strftime("%Y%m%d")
    company_slug = company.lower().replace(" ", "-").replace(".", "")
    
    company_dir = Path("companies") / company_slug
    company_dir.mkdir(parents=True, exist_ok=True)
    
    # Save job description for reference
    jd_file = company_dir / f"{date_str}--job-description.txt"
    
    # Save Q&A
    qa_file = company_dir / f"{date_str}--questions.txt"
    qa_docx = company_dir / f"{date_str}--questions.docx"
    
    qa_content = f"APPLICATION QUESTIONS - {company.upper()}\n"
    qa_content += f"Role: {role}\n"
    qa_content += "=" * 60 + "\n\n"
    
    for i, qa in enumerate(qa_answers, 1):
        qa_content += f"QUESTION {i}:\n{qa['question']}\n\n"
        qa_content += f"ANSWER:\n{qa['answer']}\n\n"
        qa_content += "-" * 40 + "\n\n"
    
    print("\nGenerating files...")
    
    # Save job description
    jd_content = f"JOB DESCRIPTION - {company.upper()}\n"
    jd_content += f"Role: {role}\n"
    jd_content += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
    if job_input.get('url'):
        jd_content += f"URL: {job_input['url']}\n"
    jd_content += "=" * 60 + "\n\n"
    jd_content += jd
    
    with open(jd_file, "w") as f:
        f.write(jd_content)
    print(f"  Created: {jd_file}")
    
    with open(qa_file, "w") as f:
        f.write(qa_content)
    print(f"  Created: {qa_file}")
    
    create_docx(qa_content, str(qa_docx))
    
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"Files saved to: {company_dir}/")
    print(f"Questions answered: {len(qa_answers)}")
    print("=" * 60 + "\n")


def main():
    # Check for questions-only mode
    if len(sys.argv) > 1 and sys.argv[1] == "--questions":
        questions_only_mode()
        return
    
    # Check for URL mode (direct URL as argument)
    url_arg = None
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url_arg = sys.argv[1]
    
    print("\n" + "=" * 60)
    print("ResBuilder - Resume & Cover Letter Generator")
    print("=" * 60)
    
    # Get job input (URL or manual)
    if url_arg and HAS_SCRAPING:
        scraped = scrape_job_posting(url_arg)
        if scraped:
            print(f"\n✓ Scraped job posting ({len(scraped['content'])} chars)")
            company = scraped.get('company') or ''
            role = scraped.get('role') or ''
            print(f"\nExtracted: {company} - {role}" if company else "")
            print("Confirm or edit (press Enter to keep):")
            company_input = input(f"  Company [{company}]: ").strip()
            role_input = input(f"  Role [{role}]: ").strip()
            job_input = {
                'url': url_arg,
                'company': company_input or company,
                'role': role_input or role,
                'content': scraped['content']
            }
        else:
            print("Failed to scrape URL. Using manual entry.")
            job_input = get_job_input()
    else:
        job_input = get_job_input()
    
    company = job_input['company']
    role = job_input['role']
    
    if not company or not role:
        print("Error: Company and role are required")
        sys.exit(1)
    
    # Get job description (from scraped content, existing file, or jd.txt)
    jd = get_job_description(company, job_input)
    
    if not jd:
        print("Error: No job description provided")
        sys.exit(1)
    
    # Get additional application questions
    questions = get_application_questions()
    
    # Read master resume
    master_resume = read_master_resume()
    
    # Tailor with AI
    result = tailor_with_ai(master_resume, jd, company, role)
    
    # Answer application questions (non-interactive mode for full flow)
    qa_answers = answer_questions_with_ai(questions, master_resume, jd, company, role, interactive=False)
    
    # Create company folder
    date_str = datetime.now().strftime("%Y%m%d")
    company_slug = company.lower().replace(" ", "-").replace(".", "")
    
    company_dir = Path("companies") / company_slug
    company_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filenames
    resume_file = company_dir / f"{date_str}--resume.docx"
    cover_file = company_dir / f"{date_str}--cover-letter.docx"
    
    # Also save plain text versions
    resume_txt = company_dir / f"{date_str}--resume.txt"
    cover_txt = company_dir / f"{date_str}--cover-letter.txt"
    
    # Save job description for reference
    jd_file = company_dir / f"{date_str}--job-description.txt"
    
    print("\nGenerating files...")
    
    # Save job description
    jd_content = f"JOB DESCRIPTION - {company.upper()}\n"
    jd_content += f"Role: {role}\n"
    jd_content += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
    if job_input.get('url'):
        jd_content += f"URL: {job_input['url']}\n"
    jd_content += "=" * 60 + "\n\n"
    jd_content += jd
    
    with open(jd_file, "w") as f:
        f.write(jd_content)
    print(f"  Created: {jd_file}")
    
    # Create .docx files
    create_docx(result["resume"], str(resume_file))
    create_docx(result["cover_letter"], str(cover_file))
    
    # Save plain text versions
    with open(resume_txt, "w") as f:
        f.write(result["resume"])
    print(f"  Created: {resume_txt}")
    
    with open(cover_txt, "w") as f:
        f.write(result["cover_letter"])
    print(f"  Created: {cover_txt}")
    
    # Save Q&A if any
    if qa_answers:
        qa_file = company_dir / f"{date_str}--questions.txt"
        qa_docx = company_dir / f"{date_str}--questions.docx"
        
        # Build Q&A content
        qa_content = f"APPLICATION QUESTIONS - {company.upper()}\n"
        qa_content += f"Role: {role}\n"
        qa_content += "=" * 60 + "\n\n"
        
        for i, qa in enumerate(qa_answers, 1):
            qa_content += f"QUESTION {i}:\n{qa['question']}\n\n"
            qa_content += f"ANSWER:\n{qa['answer']}\n\n"
            qa_content += "-" * 40 + "\n\n"
        
        # Save plain text
        with open(qa_file, "w") as f:
            f.write(qa_content)
        print(f"  Created: {qa_file}")
        
        # Save docx
        create_docx(qa_content, str(qa_docx))
    
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"Files saved to: {company_dir}/")
    if qa_answers:
        print(f"\nApplication questions answered: {len(qa_answers)}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

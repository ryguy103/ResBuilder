# ResBuilder

AI-powered job application tool that tailors resumes and generates cover letters for specific job postings using Claude AI.

## Features

- **AI-Tailored Resumes** — Automatically customizes your resume for each job posting
- **Cover Letter Generation** — Creates personalized cover letters that match the job requirements
- **Job URL Scraping** — Paste a job posting URL and automatically extract the details
- **Web Interface** — Clean, modern UI accessible from your browser
- **Master Profile** — Store all your professional details in one place for AI to draw from
- **Multiple Output Formats** — Generates both `.txt` and `.docx` files
- **Application Tracking** — Organizes all your applications by company

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-username/resbuilder.git
cd resbuilder
make setup   # or: pip install -r requirements.txt
```

### 2. Add your API key

Create a `.env` file in the project root:

```bash
echo 'ANTHROPIC_API_KEY=your-key-here' > .env
```

Get your key at [console.anthropic.com](https://console.anthropic.com/).

### 3. Set up your profile

**Option A — Web UI (recommended):**

```bash
make web
```

Open http://localhost:8000/profile and fill in your information through the guided setup wizard. The wizard walks you through personal info, skills, work experience, education, projects, and awards.

**Option B — Edit YAML directly:**

The first time you run the app, `profile.yaml.example` is automatically copied to `profile.yaml`. Open it and replace the placeholder data with your own:

```bash
# Or copy manually if you want to start before running the app
cp profile.yaml.example profile.yaml
```

> **Tip:** The more detail you include in your profile, the better the AI can tailor your applications. Add every job, skill, project, and achievement you can think of — the AI will intelligently select what's most relevant for each application.

### 4. Start applying

```bash
make web
```

Open http://localhost:8000, click **New Application**, and either paste a job posting URL or enter the details manually. The AI generates a tailored resume and cover letter in seconds.

## One-Click Install (Mac)

1. Download or clone this repository
2. Double-click `install.command` in Finder
3. Follow the prompts to enter your API key
4. Double-click `ResBuilder.command` to launch

## Usage

### Web Interface

1. **New Application**: Click "New Application" and either:
   - Paste a job posting URL to auto-fill details
   - Enter company, role, and job description manually

2. **Generate**: Click "Generate Application" to create:
   - Tailored resume (`.txt` and `.docx`)
   - Cover letter (`.txt` and `.docx`)

3. **Download**: Files are saved to `companies/{company-name}/` and available for download

### Master Profile

The Profile page lets you maintain a comprehensive record of your professional experience. The AI uses this as source material when tailoring applications.

Edit your profile at http://localhost:8000/profile or directly in `profile.yaml`.

Profile sections:
- **Personal Info** — Name, contact, location, LinkedIn, portfolio
- **Professional Summaries** — Multiple versions for different role types
- **Experience** — Full work history with accomplishments
- **Education** — Degrees, bootcamps, certifications
- **Skills** — Technical and soft skills by category
- **Projects** — Notable work and personal projects
- **Awards** — Recognition and achievements
- **Key Metrics** — Quantifiable accomplishments

### CLI Mode

For terminal users:

```bash
# Interactive mode
make prepare

# With URL scraping
make prepare URL=https://jobs.lever.co/company/position

# Answer application questions only
make questions
```

## Project Structure

```
resbuilder/
├── web/                        # Web interface
│   ├── app.py                  # FastAPI application
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS and assets
├── companies/                  # Generated applications (by company)
├── core.py                     # Shared business logic
├── prepare.py                  # CLI entry point
├── profile.yaml.example        # Template profile (copy to profile.yaml)
├── resume.md.example           # Template resume (copy to resume.md)
├── requirements.txt            # Python dependencies
├── Makefile                    # Command shortcuts
├── install.command             # One-click Mac installer
└── build_app.py                # Desktop app builder
```

## Commands

| Command | Description |
|---------|-------------|
| `make web` | Launch web interface at localhost:8000 |
| `make prepare` | CLI: Generate tailored resume + cover letter |
| `make questions` | CLI: Answer application questions only |
| `make setup` | Install Python dependencies |
| `make build` | Create standalone desktop app |
| `make help` | Show all available commands |

## Configuration

### Environment Variables

Create a `.env` file in the project root (never committed to git):

```
ANTHROPIC_API_KEY=your-key-here
```

Or export directly:

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### Profile Configuration

Edit `profile.yaml` to customize (see `profile.yaml.example` for the full schema):

```yaml
personal:
  name: Your Name
  email: you@example.com
  location: City, State
  summaries:
    default: "Your professional summary..."

experience:
  - company: Company Name
    roles:
      - title: Job Title
        dates: Jan 2020 - Present
        highlights:
          - Accomplishment 1
          - Accomplishment 2

skills:
  categories:
    - name: Technical
      items: [Python, JavaScript, SQL]

education:
  - degree: B.S. Computer Science
    institution: University Name
    years: 2014 - 2018

projects:
  - name: Project Name
    type: personal
    description: What you built
    achievements:
      - Key result or impact
    technologies: [React, Python]

awards:
  - name: Award Name
    date: "2023"
    description: Why you received it
```

## Requirements

- Python 3.8+
- Anthropic API key

### Dependencies

Installed automatically via `make setup`:

- `anthropic` — Claude AI API
- `fastapi` + `uvicorn` — Web server
- `python-docx` — Word document generation
- `python-dotenv` — Environment variable loading from `.env`
- `requests` + `beautifulsoup4` — Job posting scraping
- `pyyaml` — Profile configuration
- `jinja2` — HTML templating

## Build Standalone App

```bash
make build
```

The app will be in `dist/ResBuilder.app` (Mac) — double-click to run.

## Troubleshooting

### "API Key Required" error

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your-key-here
```

Or export it:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### Job URL scraping fails

Some job sites block automated requests. If scraping fails:
1. Copy the job description manually
2. Paste it into the "Job Description" field

### Port 8000 already in use

Another application is using port 8000. Either stop the other application or modify `web/app.py` to use a different port.

## License

MIT

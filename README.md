# ResBuilder

AI-powered job application tool that tailors resumes and generates cover letters for specific job postings. Supports multiple AI providers: **Anthropic (Claude)**, **OpenAI (GPT)**, and **Google (Gemini)**.

## Features

- **Multi-Provider AI** — Choose Anthropic, OpenAI, or Google Gemini; SDKs are installed on-demand
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

### 2. Launch and configure

```bash
make web
```

Open http://localhost:8000. On first launch you'll be guided through a setup wizard where you:

1. **Pick an AI provider** (Anthropic, OpenAI, or Google Gemini)
2. **Install the SDK** (one click, no terminal needed)
3. **Paste your API key** (with a link to get one)
4. **Set up your profile** through the guided wizard

That's it — no manual `.env` editing required.

### 3. Start applying

Click **New Application**, paste a job posting URL or enter details manually, and the AI generates a tailored resume and cover letter in seconds.

## One-Click Install (Mac)

1. Download or clone this repository
2. Double-click `install.command` in Finder
3. Follow the prompts
4. Double-click `ResBuilder.command` to launch

## AI Providers

| Provider | Model | Get a Key |
|----------|-------|-----------|
| Anthropic (Claude) | claude-sonnet-4-20250514 | [console.anthropic.com](https://console.anthropic.com/) |
| OpenAI (GPT) | gpt-4o | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Google (Gemini) | gemini-2.0-flash | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

You can switch providers at any time from the **Settings** page. SDKs are only installed when you select a provider, keeping the base install lightweight.

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
├── ai_client.py                # Multi-provider AI abstraction
├── core.py                     # Shared business logic
├── prepare.py                  # CLI entry point
├── profile.yaml.example        # Template profile (copy to profile.yaml)
├── resume.md.example           # Template resume (copy to resume.md)
├── requirements.txt            # Python dependencies (no AI SDKs)
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

### Environment Variables (optional)

The recommended way to configure ResBuilder is through the web UI setup wizard. If you prefer manual configuration, create a `.env` file:

```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
```

Supported providers and their environment variable names:

| Provider | Variable |
|----------|----------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Google | `GOOGLE_API_KEY` |

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
- An API key from one of: Anthropic, OpenAI, or Google

### Dependencies

Installed automatically via `make setup`:

- `fastapi` + `uvicorn` — Web server
- `python-docx` — Word document generation
- `python-dotenv` — Environment variable loading from `.env`
- `requests` + `beautifulsoup4` — Job posting scraping
- `pyyaml` — Profile configuration
- `jinja2` — HTML templating

AI provider SDKs (`anthropic`, `openai`, `google-generativeai`) are installed automatically when you select a provider in the setup wizard.

## Build Standalone App

```bash
make build
```

The app will be in `dist/ResBuilder.app` (Mac) — double-click to run.

**macOS note:** The desktop launcher does **not** use Tkinter (PyInstaller’s windowed build crashes when Tcl/Tk initializes). Your browser opens automatically; configure your AI provider at `/setup` in the app.

**Where data is stored (`.app` build):** Profile, `.env`, and `companies/` live under **`~/Library/Application Support/ResBuilder`** on Mac (not inside the `.app` bundle). Running **`make web`** from a git clone uses the **project folder** instead, so your **`companies/`** list can look empty in the `.app` until you either:

- **Copy** your existing folder:  
  `cp -R /path/to/resbuilder/companies ~/Library/Application\ Support/ResBuilder/`
- **Or** point the `.app` at your clone: create **`~/.resbuilder/data_dir`** containing a **single line** with the **absolute path** to your resbuilder project (the directory that contains `companies/`). Rebuild the app after changing `launcher.py`, or edit the same logic if you ship updates.

Without `data_dir`, the desktop app and terminal workflow use **two different data roots** by design.

## Troubleshooting

### "No AI provider configured" on dashboard

Visit http://localhost:8000/setup to choose a provider and enter your API key.

### SDK installation fails

If the in-app install fails, you can install manually:

```bash
pip install anthropic    # for Anthropic
pip install openai       # for OpenAI
pip install google-generativeai  # for Google Gemini
```

### Job URL scraping fails

Some job sites block automated requests. If scraping fails:
1. Copy the job description manually
2. Paste it into the "Job Description" field

### Port 8000 already in use

Another application is using port 8000. Either stop the other application or modify `web/app.py` to use a different port.

## License

MIT

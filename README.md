# ResBuilder

AI-powered job application tool that tailors resumes and generates cover letters for specific job postings.

## Features

- **AI-Tailored Resumes** - Automatically customizes your resume for each job posting using Claude AI
- **Cover Letter Generation** - Creates personalized cover letters that match the job requirements
- **Job URL Scraping** - Paste a job posting URL and automatically extract the details
- **Web Interface** - Clean, modern UI accessible from your browser
- **Master Profile** - Store all your professional details in one place for AI to draw from
- **Multiple Output Formats** - Generates both `.txt` and `.docx` files
- **Application Tracking** - Organizes all your applications by company

## Quick Start

### Option 1: One-Click Install (Mac)

1. Download or clone this repository
2. Double-click `install.command` in Finder
3. Follow the prompts to enter your API key
4. Double-click `ResBuilder.command` to launch

### Option 2: Command Line

```bash
# Install dependencies
make setup

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Launch the web interface
make web
```

Then open http://localhost:8000 in your browser.

### Option 3: Build Standalone App

```bash
# Build a distributable .app (Mac) or .exe (Windows)
make build
```

The app will be in `dist/ResBuilder.app` - double-click to run.

## Getting an API Key

ResBuilder uses Claude AI from Anthropic. Get your API key at:
https://console.anthropic.com/

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
- **Personal Info** - Name, contact, location
- **Professional Summaries** - Multiple versions for different role types
- **Experience** - Work history with accomplishments
- **Skills** - Technical and soft skills by category
- **Projects** - Notable work and personal projects
- **Awards** - Recognition and achievements
- **Key Metrics** - Quantifiable accomplishments

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
├── web/                    # Web interface
│   ├── app.py             # FastAPI application
│   ├── templates/         # Jinja2 HTML templates
│   └── static/            # CSS and assets
├── companies/             # Generated applications (by company)
├── core.py                # Shared business logic
├── prepare.py             # CLI entry point
├── profile.yaml           # Master professional profile
├── resume.md              # Fallback resume (if no profile)
├── resume.txt             # Plain text resume
├── requirements.txt       # Python dependencies
├── Makefile              # Command shortcuts
├── install.command       # One-click Mac installer
└── build_app.py          # Desktop app builder
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

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required for AI features) |

### Profile Configuration

Edit `profile.yaml` to customize:

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
```

## Requirements

- Python 3.8+
- Anthropic API key

### Dependencies

Installed automatically via `make setup`:

- `anthropic` - Claude AI API
- `fastapi` + `uvicorn` - Web server
- `python-docx` - Word document generation
- `requests` + `beautifulsoup4` - Job posting scraping
- `pyyaml` - Profile configuration
- `jinja2` - HTML templating

## Development

```bash
# Run with auto-reload
make web

# The server watches for file changes automatically
```

## Troubleshooting

### "API Key Required" error

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Or save it permanently (Mac/Linux):
```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Job URL scraping fails

Some job sites block automated requests. If scraping fails:
1. Copy the job description manually
2. Paste it into the "Job Description" field

### Port 8000 already in use

Another application is using port 8000. Either:
- Stop the other application
- Or modify `web/app.py` to use a different port

## License

MIT

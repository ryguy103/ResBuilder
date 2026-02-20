# ============================================================================
# laxjob Makefile - Ryan Laxson's Resume & Cover Letter System
# ============================================================================
# Primary workflow uses markdown/plain text (no LaTeX required).
# LaTeX commands available if you install MacTeX later.
# ============================================================================

OUTPUT_DIR := output
DATE_PREFIX := $(shell date +%Y%m%d)

# ============================================================================
# MARKDOWN WORKFLOW (No LaTeX Required)
# ============================================================================

.PHONY: help view copy save md clean new list done back status tips tailor jd

help: ## Show this help
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "laxjob - Ryan Laxson's Resume System"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "JOB APPLICATION WORKFLOW:"
	@echo "  make new company=X role=Y   Start new application branch"
	@echo "  make jd                     Open jd.txt to paste job description"
	@echo "  make tailor                 Generate AI prompt to tailor resume"
	@echo "  make list                   List all application branches"
	@echo "  make status                 Show current branch & changes"
	@echo "  make done                   Commit & push current branch"
	@echo "  make back                   Return to main branch"
	@echo "  make tips                   Show tailoring tips"
	@echo ""
	@echo "RESUME COMMANDS:"
	@echo "  make view      Display plain text resume in terminal"
	@echo "  make copy      Copy plain text resume to clipboard"
	@echo "  make save      Save dated copy to output/ folder"
	@echo "  make md        Open resume.md in default editor"
	@echo ""
	@echo "LATEX COMMANDS (optional - requires MacTeX):"
	@echo "  make pdf       Build resume PDF"
	@echo "  make cover     Build cover letter PDF"
	@echo ""
	@echo "OTHER:"
	@echo "  make clean     Remove generated files"
	@echo ""

view: ## Display plain text resume in terminal
	@cat resume.txt

copy: ## Copy plain text resume to clipboard (macOS)
	@cat resume.txt | pbcopy
	@echo "✓ Resume copied to clipboard"
	@echo "  Paste into any application form or text field"

save: | $(OUTPUT_DIR) ## Save dated plain text copy to output/
	@cp resume.txt $(OUTPUT_DIR)/$(DATE_PREFIX)--ryan-laxson-resume.txt
	@cp resume.md $(OUTPUT_DIR)/$(DATE_PREFIX)--ryan-laxson-resume.md
	@echo "✓ Saved to $(OUTPUT_DIR)/"
	@echo "  - $(DATE_PREFIX)--ryan-laxson-resume.txt"
	@echo "  - $(DATE_PREFIX)--ryan-laxson-resume.md"

md: ## Open resume.md in default editor
	@open resume.md 2>/dev/null || code resume.md 2>/dev/null || vim resume.md

$(OUTPUT_DIR):
	@mkdir -p $(OUTPUT_DIR)

# ============================================================================
# JOB APPLICATION WORKFLOW
# ============================================================================

new: ## Start new application: make new company=figma role=ai-specialist
	@if [ -z "$(company)" ]; then \
		echo "Usage: make new company=companyname role=jobtitle"; \
		echo "Example: make new company=figma role=ai-specialist"; \
		exit 1; \
	fi
	@ROLE=$${role:-position}; \
	BRANCH="apply/$(company)-$$ROLE"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "Creating application branch: $$BRANCH"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	git checkout -b $$BRANCH; \
	echo ""; \
	echo "✓ Branch created: $$BRANCH"; \
	echo ""; \
	echo "NEXT STEPS:"; \
	echo "  1. Edit resume.md to tailor for this role"; \
	echo "  2. Update resume.txt to match (keep in sync)"; \
	echo "  3. Run 'make copy' to copy to clipboard"; \
	echo "  4. Run 'make done' when finished"; \
	echo ""; \
	echo "Run 'make tips' for tailoring guidance"; \
	echo ""

list: ## List all application branches
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Application Branches"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@git branch -a | grep "apply/" || echo "No application branches yet."
	@echo ""
	@echo "Current branch: $$(git branch --show-current)"
	@echo ""

status: ## Show current branch and uncommitted changes
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Current branch: $$(git branch --show-current)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@git status --short
	@echo ""

done: ## Commit changes and push current branch
	@BRANCH=$$(git branch --show-current); \
	if [ "$$BRANCH" = "main" ]; then \
		echo "Error: You're on main. Create an application branch first:"; \
		echo "  make new company=companyname role=jobtitle"; \
		exit 1; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "Saving application: $$BRANCH"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	git add -A; \
	git commit -m "Tailored resume for $$BRANCH" || echo "Nothing to commit"; \
	git push -u origin $$BRANCH; \
	echo ""; \
	echo "✓ Saved and pushed: $$BRANCH"; \
	echo ""; \
	echo "Run 'make back' to return to main branch"; \
	echo ""

back: ## Return to main branch
	@echo "Switching to main branch..."
	@git checkout main
	@echo ""
	@echo "✓ Back on main"
	@echo ""

tips: ## Show tailoring tips and strength mapping
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "TAILORING TIPS"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "STRENGTH MAPPING - Lead with bullets that match JD keywords:"
	@echo ""
	@echo "  JD mentions AI/automation/chatbots:"
	@echo "    → IncidentBot, AI-powered messaging agents, LLM framework"
	@echo ""
	@echo "  JD mentions Zendesk/support tooling:"
	@echo "    → Problem ticket creation, routing, escalation paths"
	@echo ""
	@echo "  JD mentions data/analytics/metrics:"
	@echo "    → Databricks/Looker/Grafana dashboards"
	@echo ""
	@echo "  JD mentions cross-functional/stakeholders:"
	@echo "    → Partnership with Support/Engineering/Product/GTM"
	@echo ""
	@echo "  JD mentions documentation/playbooks:"
	@echo "    → Authored playbooks, governance models, training"
	@echo ""
	@echo "  JD mentions experimentation/iteration:"
	@echo "    → AI tooling evaluation, LLM prompt framework"
	@echo ""
	@echo "  JD mentions customer experience:"
	@echo "    → Statuspage automation, customer-facing updates"
	@echo ""
	@echo "  JD mentions cost savings/efficiency:"
	@echo "    → \$$250K savings, 90→3 min improvement"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "KEY METRICS (always preserve these):"
	@echo "  • Reduced incident response: 90 min → 3 min"
	@echo "  • Cost savings: \$$250K annually"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

jd: ## Open jd.txt to paste the job description
	@open jd.txt 2>/dev/null || code jd.txt 2>/dev/null || vim jd.txt

tailor: ## Generate AI prompt to tailor resume (paste jd.txt first)
	@if grep -q "PASTE THE JOB DESCRIPTION HERE" jd.txt 2>/dev/null; then \
		echo "Error: Paste the job description into jd.txt first"; \
		echo "Run: make jd"; \
		exit 1; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "AI TAILORING PROMPT"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Copy everything below this line and paste into Claude/ChatGPT:"
	@echo ""
	@echo "================================================================"
	@echo ""
	@echo "Help me tailor my resume for this job. Follow these rules:"
	@echo ""
	@echo "1. KEYWORD ALIGNMENT: Use terms from the JD where I have genuine experience"
	@echo "2. REORDER BULLETS: Put the most relevant accomplishments first"
	@echo "3. PRESERVE METRICS: Always keep \$$250K savings and 90→3 min response time"
	@echo "4. NO FABRICATION: Only use keywords where I have real experience"
	@echo "5. ACTIVE VOICE: No 'exposure to' or 'familiar with'"
	@echo ""
	@echo "=== MY CURRENT RESUME ==="
	@echo ""
	@cat resume.md
	@echo ""
	@echo "=== JOB DESCRIPTION ==="
	@echo ""
	@cat jd.txt
	@echo ""
	@echo "=== WHAT I NEED ==="
	@echo ""
	@echo "1. Analysis table: JD Requirement | My Match | Gap"
	@echo "2. Tailored resume.md (reordered/reframed bullets)"
	@echo "3. Tailored resume.txt (plain text for ATS)"
	@echo ""
	@echo "================================================================"

# ============================================================================
# LATEX WORKFLOW (Optional - requires: brew install --cask mactex-no-gui)
# ============================================================================

.PHONY: pdf all cover website

pdf: | $(OUTPUT_DIR) ## Build resume PDF (requires LaTeX)
	@command -v latexmk >/dev/null 2>&1 || { echo "Error: LaTeX not installed. Run: brew install --cask mactex-no-gui"; exit 1; }
	@echo "Building resume PDF..."
	@latexmk -pdf -interaction=nonstopmode resume.tex
	@mv resume.pdf $(OUTPUT_DIR)/$(DATE_PREFIX)--ryan-laxson-resume.pdf
	@echo "✓ Resume: $(OUTPUT_DIR)/$(DATE_PREFIX)--ryan-laxson-resume.pdf"

cover: | $(OUTPUT_DIR) ## Build cover letter PDF (requires LaTeX)
	@command -v latexmk >/dev/null 2>&1 || { echo "Error: LaTeX not installed. Run: brew install --cask mactex-no-gui"; exit 1; }
	@echo "Building cover letter PDF..."
	@latexmk -pdf -interaction=nonstopmode cover-letter.tex
	@mv cover-letter.pdf $(OUTPUT_DIR)/$(DATE_PREFIX)--ryan-laxson-cover-letter.pdf
	@echo "✓ Cover letter: $(OUTPUT_DIR)/$(DATE_PREFIX)--ryan-laxson-cover-letter.pdf"

all: pdf cover ## Build all PDFs (requires LaTeX)

website: ## Build PUBLIC resume PDF for website (requires LaTeX, main branch only)
	@command -v latexmk >/dev/null 2>&1 || { echo "Error: LaTeX not installed. Run: brew install --cask mactex-no-gui"; exit 1; }
	@if [ "$$(git branch --show-current 2>/dev/null)" != "main" ] && [ -d .git ]; then \
		echo "Error: 'make website' only allowed from main branch"; \
		exit 1; \
	fi
	@echo "Building public resume (no phone/address)..."
	@latexmk -pdf -interaction=nonstopmode resume-public.tex
	@echo "✓ Public resume: resume-public.pdf"

# ============================================================================
# UTILITY
# ============================================================================

clean: ## Remove generated files
	@rm -rf $(OUTPUT_DIR)
	@rm -f *.aux *.log *.out *.toc *.fdb_latexmk *.fls *.synctex.gz *.pdf
	@echo "✓ Cleaned"

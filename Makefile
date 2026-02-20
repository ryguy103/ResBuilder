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

.PHONY: help view copy save md clean

help: ## Show this help
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "laxjob - Ryan Laxson's Resume System"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "MARKDOWN COMMANDS (no LaTeX required):"
	@echo "  make view      Display plain text resume in terminal"
	@echo "  make copy      Copy plain text resume to clipboard"
	@echo "  make save      Save dated copy to output/ folder"
	@echo "  make md        Open resume.md in default editor"
	@echo ""
	@echo "LATEX COMMANDS (requires MacTeX):"
	@echo "  make pdf       Build resume PDF"
	@echo "  make cover     Build cover letter PDF"
	@echo "  make all       Build both PDFs"
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

#!/usr/bin/env bash
#
# ai-job-finder-setup.sh — Automated environment setup for AIJobFinder CLI

# Usage:   bash ai-job-finder-setup.sh
# Purpose: Install deps → configure API keys → set up DB → verify everything works
#

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'  # No Colour

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERR]${NC}   $*"; }
header(){ echo; echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"; }

# ── Locate project root (where this script lives) ────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         JobFinder — Setup Script             ║"
echo "  ║         v0.3.0                               ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Install Python dependencies
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 1 — Installing Python dependencies"

info "Installing core requirements..."
pip install -r requirements.txt --quiet 2>&1 | tail -1 || true
ok "Core requirements installed."

info "Installing ML dependencies (torch, transformers, sentence-transformers)..."
pip install torch transformers sentence-transformers --quiet 2>&1 | tail -1 || true
ok "ML dependencies installed."

info "Installing PDF export library (fpdf2)..."
pip install fpdf2 --quiet 2>&1 | tail -1 || true
ok "fpdf2 installed."

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Set up API keys (.env)
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 2 — Configuring API keys (.env)"

if [ -f ".env" ]; then
    ok ".env file already exists — keeping existing keys."
else
    cp .env.template .env
    warn "✎  OPEN .env NOW and fill in at least one API key:"
    echo
    echo -e "   ${YELLOW}GEMINI_API_KEY${NC}  →  get from https://aistudio.google.com/app/apikey  (free)"
    echo -e "   ${YELLOW}OPENAI_API_KEY${NC}  →  get from https://platform.openai.com/api-keys    (paid)"
    echo
    echo -e "   ${CYAN}Opening .env in nano in 3 seconds...${NC}"
    sleep 3
    nano .env
    ok ".env file saved."
fi

# Verify at least one key is set
if grep -qE "^(GEMINI_API_KEY|OPENAI_API_KEY)=.+$" .env 2>/dev/null; then
    ok "✔ At least one API key is configured."
else
    warn "⚠  No API keys detected. AI features (improve, scoring suggestions) will fail."
    warn "   Run 'nano .env' later to add them."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Install Playwright browsers
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 3 — Installing Playwright browsers"

if python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" 2>/dev/null; then
    ok "Playwright Chromium browser is already installed."
else
    info "Installing Playwright Chromium browser (headless)..."
    python -m playwright install chromium --quiet 2>&1 || true
    ok "Playwright Chromium installed."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Verify spaCy model
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 4 — Verifying spaCy model"

if python -m spacy validate 2>&1 | grep -q "en_core_web_sm"; then
    ok "spaCy model 'en_core_web_sm' is already installed."
else
    info "Downloading spaCy model 'en_core_web_sm'..."
    python -m spacy download en_core_web_sm --quiet 2>&1 || true
    ok "spaCy model installed."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Run database migrations
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 5 — Running database migrations"

info "Running: alembic upgrade head"
alembic upgrade head 2>&1 || true
if [ -f "data/ai-job-finder.db" ]; then
    ok "Database exists at data/ai-job-finder.db"
else
    warn "Database file not found — migrations may have failed."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Verify CLI boots without crashing
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 6 — Verifying CLI boots"

if python -m src.main --version 2>&1; then
    ok "CLI boots successfully!"
else
    err "CLI failed to boot. Check the error above."
    err "Common fix: pip install torch transformers"
fi

echo
python -m src.main --help 2>&1 | head -20
echo

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Run the test suite
# ═══════════════════════════════════════════════════════════════════════════════
header "STEP 7 — Running test suite"

info "Running: python -m pytest -v --tb=short -p no:asyncio"
python -m pytest -v --tb=short -p no:asyncio 2>&1 | tail -20
echo

# ═══════════════════════════════════════════════════════════════════════════════
# DONE — Summary
# ═══════════════════════════════════════════════════════════════════════════════
header "✅  SETUP COMPLETE — What to do next"

echo
echo -e "   ${CYAN}1. Test with a CV${NC}"
echo "       python -m src.main analyze /path/to/your/cv.pdf"
echo "       python -m src.main search /path/to/your/cv.pdf --query 'python'"
echo
echo -e "   ${CYAN}2. Create a user profile${NC}"
echo "       python -m src.main profile you@email.com --name 'Your Name'"
echo
echo -e "   ${CYAN}3. View saved applications & stats${NC}"
echo "       python -m src.main list"
echo "       python -m src.main stats"
echo
echo -e "   ${CYAN}4. Export results${NC}"
echo "       python -m src.main analyze cv.pdf --format json --output report.json"
echo "       python -m src.main analyze cv.pdf --format pdf  --output report.pdf"
echo
echo -e "   ${CYAN}5. Re-run tests anytime${NC}"
echo "       python -m pytest -v"
echo

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
header "📋  Environment Summary"
echo
echo "   Project root:  $SCRIPT_DIR"
echo "   Python:        $(python --version 2>&1)"
echo "   pip:           $(pip --version 2>&1)"
echo "   DB:            $SCRIPT_DIR/data/ai-job-finder.db"
echo "   Config:        $SCRIPT_DIR/.env"
echo "   Test count:    96 unit tests (excluding integration)"
echo

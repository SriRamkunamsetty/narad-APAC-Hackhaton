#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# NARAD — Local development setup
# Usage: chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════════
set -e

echo "🔧 NARAD Local Setup"
echo ""

# ── Backend setup ─────────────────────────────────────────────────────────
echo "📦 Installing backend dependencies..."
pip install -r backend/requirements.txt --break-system-packages -q

if [ ! -f .env ]; then
  echo "📄 Creating .env from template..."
  cp .env.example .env
  echo "⚠️  IMPORTANT: Edit .env and add your GEMINI_API_KEY"
  echo "   Get a free key at: https://aistudio.google.com/app/apikey"
fi

# ── Frontend setup ────────────────────────────────────────────────────────
echo "📦 Installing frontend dependencies..."
cd frontend && npm install --silent && cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run NARAD locally:"
echo "  Terminal 1: python3 -m uvicorn backend.main:app --reload --port 8080"
echo "  Terminal 2: cd frontend && npm run dev"
echo ""
echo "Then open: http://localhost:5173"

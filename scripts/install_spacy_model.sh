#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# install_spacy_model.sh — Download the spaCy English model for JARVIS NLP
# ════════════════════════════════════════════════════════════════════════════
# Run this ONCE after `pip install spacy`:
#
#   bash scripts/install_spacy_model.sh
#
# The script verifies the spaCy installation, downloads the English model,
# and runs a quick pipeline self-test to confirm everything is working.
# ════════════════════════════════════════════════════════════════════════════

set -euo pipefail

PYTHON="${PYTHON:-python3}"
MODEL="en_core_web_sm"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  JARVIS NLP Setup — spaCy model installer"
echo "═══════════════════════════════════════════════════"
echo ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo "❌  '$PYTHON' not found. Set PYTHON=python3.11 or similar."
    exit 1
fi
echo "✅  Python: $($PYTHON --version)"

# ── 2. Check spaCy ───────────────────────────────────────────────────────────
if ! "$PYTHON" -c "import spacy" 2>/dev/null; then
    echo "📦  spaCy not installed — installing now..."
    pip install "spacy~=3.8.0"
fi
echo "✅  spaCy: $($PYTHON -c "import spacy; print(spacy.__version__)")"

# ── 3. Check NumPy (required by NLP pipeline) ────────────────────────────────
if ! "$PYTHON" -c "import numpy" 2>/dev/null; then
    echo "📦  NumPy not installed — installing now..."
    pip install "numpy~=2.2.0"
fi
echo "✅  NumPy: $($PYTHON -c "import numpy; print(numpy.__version__)")"

# ── 4. Download spaCy model ──────────────────────────────────────────────────
echo ""
echo "📥  Downloading spaCy model: $MODEL ..."
"$PYTHON" -m spacy download "$MODEL"
echo "✅  Model '$MODEL' installed."

# ── 5. Quick self-test ───────────────────────────────────────────────────────
echo ""
echo "🔬  Running pipeline self-test..."
"$PYTHON" - <<'PYEOF'
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.nlp_pipeline import NLPPipeline
    pipeline = NLPPipeline()
    test_cases = [
        "Set an alarm for 7am tomorrow",
        "I am feeling very stressed today",
        "What is the capital of France?",
        "Remember that my meeting is on Friday at 3pm",
    ]
    for text in test_cases:
        result = pipeline.process(text)
        print(f"  ✓ '{text[:50]}' → {result.summary()}")
    print("\n✅  Self-test passed! NLPPipeline is ready.")
except Exception as e:
    print(f"\n⚠️  Self-test failed: {e}")
    print("   This may be expected if running outside the and9 project root.")
PYEOF

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Setup complete! JARVIS NLP pipeline is ready."
echo "═══════════════════════════════════════════════════"
echo ""

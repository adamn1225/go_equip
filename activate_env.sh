#!/bin/bash
# Activation script for scraper-pipeline project
# This ensures you're always using the correct virtual environment

echo "🔧 Activating ai_env virtual environment..."
source ai_env/bin/activate

echo "✅ Environment activated!"
echo "📦 Python version: $(python --version)"
echo "🌍 Virtual environment: $VIRTUAL_ENV"

# Optional: Show key package versions
echo ""
echo "📋 Key packages:"
pip list | grep -E "(streamlit|openai|plotly|pandas|requests)" | head -5

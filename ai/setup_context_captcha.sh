#!/bin/bash
"""
Setup Context-Aware CAPTCHA Learning System
Installs all dependencies including system packages
"""

echo "🧠 Setting up Context-Aware CAPTCHA Learning System"
echo "=================================================="

# Check if we're on Ubuntu/Debian or macOS
if command -v apt &> /dev/null; then
    echo "📦 Installing system dependencies (Ubuntu/Debian)..."
    sudo apt update
    sudo apt install -y tesseract-ocr tesseract-ocr-eng
    echo "✅ Tesseract OCR installed"
elif command -v brew &> /dev/null; then
    echo "📦 Installing system dependencies (macOS)..."
    brew install tesseract
    echo "✅ Tesseract OCR installed"
else
    echo "⚠️  Please install tesseract-ocr manually:"
    echo "   - Ubuntu/Debian: sudo apt install tesseract-ocr"
    echo "   - macOS: brew install tesseract"
    echo "   - Windows: Download from: https://github.com/UB-Mannheim/tesseract/wiki"
fi

# Install Python packages
echo "🐍 Installing Python packages..."
pip install -r ai/requirements_context_captcha.txt

echo "🤖 Testing installation..."
python3 -c "
import torch
import torchvision
import cv2
import pytesseract
from PIL import Image
import numpy as np

print(f'✅ PyTorch {torch.__version__}')
print(f'✅ Torchvision {torchvision.__version__}')
print(f'✅ OpenCV {cv2.__version__}')
print(f'✅ Tesseract available: {pytesseract.get_tesseract_version()}')

# Test GPU
if torch.cuda.is_available():
    print(f'🚀 CUDA GPU available: {torch.cuda.get_device_name(0)}')
else:
    print('💻 CPU mode (no CUDA GPU detected)')

print('✅ All dependencies installed successfully!')
"

echo ""
echo "🚀 Setup Complete!"
echo "=================="
echo "Run the context-aware learner with:"
echo "   python3 ai/captcha_context_learner.py"
echo ""
echo "🧩 What this system can do:"
echo "   - Extract question text from CAPTCHA images"
echo "   - Understand different question types (most/least/color/etc.)"
echo "   - Describe puzzle images using AI vision models"
echo "   - Track success rates by question pattern"
echo "   - Learn from your solving patterns"
echo ""
echo "💡 Pro tip: The system learns better with diverse question types!"

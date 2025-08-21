#!/bin/bash
# Setup CAPTCHA Learning System with CUDA support

set -e

echo "🚀 Setting up CAPTCHA Learning System for NVIDIA GPU..."

# Check for NVIDIA GPU
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
    echo "⚠️  No NVIDIA GPU detected. Will install CPU-only version."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "captcha_env" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv captcha_env
fi

# Activate environment
echo "🔧 Activating environment..."
source captcha_env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install PyTorch with CUDA support (if available)
echo "🔥 Installing PyTorch with CUDA support..."
if command -v nvidia-smi &> /dev/null; then
    # Install CUDA version
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    # Install CPU version
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install other requirements
echo "📚 Installing other dependencies..."
pip install -r ai/requirements_captcha_learning.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 To get started:"
echo "   1. Activate environment: source captcha_env/bin/activate"
echo "   2. Collect training data: python ai/captcha_learning_system.py --mode collect"
echo "   3. Train model: python ai/captcha_learning_system.py --mode train"
echo "   4. Check data: python ai/captcha_learning_system.py --mode info"
echo ""

# Test PyTorch installation
echo "🧪 Testing PyTorch installation..."
source captcha_env/bin/activate
python -c "
import torch
import torchvision
print(f'✅ PyTorch version: {torch.__version__}')
print(f'✅ Torchvision version: {torchvision.__version__}')
print(f'🖥️  CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'🚀 GPU: {torch.cuda.get_device_name(0)}')
    print(f'💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')
else:
    print('💻 Running on CPU')
"

echo ""
echo "🎉 Ready to start learning from CAPTCHAs!"

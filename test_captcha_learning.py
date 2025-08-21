#!/usr/bin/env python3
"""
Quick test script for CAPTCHA learning system
"""

import os
import sys
from pathlib import Path

def check_setup():
    """Check if the learning system is properly set up"""
    print("🔍 Checking CAPTCHA Learning System setup...")
    
    # Check files
    required_files = [
        'ai/captcha_learning_system.py',
        'ai/captcha_solver_enhanced.py', 
        'ai/requirements_captcha_learning.txt',
        'setup_captcha_learning.sh'
    ]
    
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING!")
    
    # Check virtual environment
    if Path('captcha_env').exists():
        print("   ✅ Virtual environment created")
        
        # Check if PyTorch is installed
        try:
            import sys
            sys.path.append('captcha_env/lib/python*/site-packages')
            import torch
            print(f"   ✅ PyTorch {torch.__version__} installed")
            print(f"   🖥️  CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"   🚀 GPU: {torch.cuda.get_device_name(0)}")
        except ImportError:
            print("   ⚠️  PyTorch not found in environment")
            print("   💡 Run: ./setup_captcha_learning.sh")
    else:
        print("   ❌ Virtual environment not found")
        print("   💡 Run: ./setup_captcha_learning.sh")

def show_usage():
    """Show usage instructions"""
    print("""
🎯 CAPTCHA Learning System - Quick Start:

1. 📦 Setup (first time only):
   ./setup_captcha_learning.sh

2. 🔧 Activate environment:  
   source captcha_env/bin/activate

3. 📚 Collect training data:
   python ai/captcha_learning_system.py --mode collect
   
   # While your scraper is running and encounters CAPTCHAs:
   # - Type 'start' when CAPTCHA appears
   # - Solve it normally  
   # - Type 'save success' or 'save failed'
   # - Repeat 50+ times for good training data

4. 🏋️  Train your model:
   python ai/captcha_learning_system.py --mode train

5. 📊 Check progress:
   python ai/captcha_learning_system.py --mode info

6. 🚀 Use enhanced solver in your scraper:
   # Edit your scraper to use ai/captcha_solver_enhanced.py
   # It will automatically collect data AND use your trained model!

🧠 Learning Opportunities:
   - Modify the CNN architecture in CaptchaCNN class
   - Experiment with different optimizers and learning rates
   - Add data augmentation for better generalization
   - Try transfer learning with pre-trained models

📈 Expected Results:
   - 50+ samples: ~60-70% accuracy
   - 200+ samples: ~75-85% accuracy  
   - 500+ samples: ~85-95% accuracy on similar CAPTCHAs
""")

if __name__ == '__main__':
    print("🧠 CAPTCHA Learning System Test")
    print("=" * 40)
    
    check_setup()
    show_usage()
    
    # Basic functionality test
    try:
        from ai.captcha_learning_system import CaptchaDataCollector
        collector = CaptchaDataCollector()
        print("\n✅ Learning system imports successfully!")
        print("🎉 Ready to start collecting CAPTCHA data!")
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        print("💡 Make sure to run: ./setup_captcha_learning.sh")
    
    print("\n🚀 Happy learning!")

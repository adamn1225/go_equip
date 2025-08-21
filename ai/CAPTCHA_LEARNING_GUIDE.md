# 🧠 CAPTCHA Learning System Guide

## 🎯 What This Does
- **Watches you solve CAPTCHAs** and records the data
- **Trains a CNN model** using PyTorch on your NVIDIA GPU  
- **Learns patterns** to eventually solve CAPTCHAs automatically
- **Perfect for learning** PyTorch, CUDA, and computer vision!

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
chmod +x setup_captcha_learning.sh
./setup_captcha_learning.sh
```

### 2. Activate Environment  
```bash
source captcha_env/bin/activate
```

## 📚 Usage Guide

### Phase 1: Data Collection
```bash
# Start data collection mode
python ai/captcha_learning_system.py --mode collect

# When a CAPTCHA appears in your scraper:
# 1. Type 'start' and press Enter
# 2. Solve the CAPTCHA normally
# 3. Type 'save success' if solved, or 'save failed' if failed
# 4. Repeat for 50-100 CAPTCHAs for good training data
```

### Phase 2: Model Training
```bash
# Train CNN model on your data
python ai/captcha_learning_system.py --mode train --epochs 50

# Check your training data
python ai/captcha_learning_system.py --mode info
```

## 🔥 Integration with Your Scraper

The system creates these files:
- `captcha_training_data/screenshots/` - CAPTCHA images
- `captcha_training_data/solutions/` - Your solving data
- `captcha_training_data/models/` - Trained CNN models

## 💡 Learning Path

### Beginner Level:
1. **Data Collection** - Learn how training data is structured
2. **Model Architecture** - Understand CNN layers in `CaptchaCNN` class
3. **Training Loop** - See how PyTorch trains models

### Intermediate Level:
1. **Modify the CNN** - Try different architectures
2. **Data Augmentation** - Add transforms for better generalization
3. **Advanced Loss Functions** - Experiment with different objectives

### Advanced Level:  
1. **Multi-task Learning** - Predict CAPTCHA type AND solution
2. **Attention Mechanisms** - Focus on important image regions
3. **Transfer Learning** - Use pre-trained models like ResNet

## 🧪 Experiment Ideas

### Easy Experiments:
```python
# Try different CNN architectures
model = torchvision.models.resnet18(pretrained=True)
model.fc = nn.Linear(model.fc.in_features, 2)

# Adjust learning parameters  
python ai/captcha_learning_system.py --mode train --epochs 100 --batch-size 16
```

### Advanced Experiments:
1. **Object Detection** - Detect CAPTCHA elements before solving
2. **Reinforcement Learning** - Learn optimal clicking sequences
3. **GAN-based Augmentation** - Generate synthetic CAPTCHA data

## 📊 Expected Results

With your complex hCaptcha puzzles:
- **50+ training samples**: ~60-70% accuracy
- **200+ training samples**: ~75-85% accuracy  
- **500+ training samples**: ~85-95% accuracy

## 🔧 Troubleshooting

### CUDA Issues:
```bash
# Check GPU status
nvidia-smi

# Test PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Memory Issues:
```bash
# Reduce batch size
python ai/captcha_learning_system.py --mode train --batch-size 4
```

## 🎯 Next Steps

1. **Collect 50-100 CAPTCHA samples** while using your scraper
2. **Train your first model** and see the results
3. **Iterate and improve** the model architecture
4. **Integrate with your scraper** for automated solving

This is a perfect project to learn PyTorch, CUDA programming, and computer vision while solving a real business problem! 🚀

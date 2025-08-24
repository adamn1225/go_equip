#!/usr/bin/env python3
"""
🧠 CAPTCHA Difficulty Predictor - Using Your Trained Model
Uses your 100% accurate CPU-trained model to predict CAPTCHA solvability
"""

import torch
import torchvision.transforms as transforms
from PIL import Image
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CaptchaPredictor:
    """Predicts if a CAPTCHA is solvable using your trained model"""
    
    def __init__(self, model_path="captcha_training_data/models/best_captcha_model.pth"):
        self.device = torch.device("cpu")  # Force CPU for RTX 5070 compatibility
        self.model_path = Path(model_path)
        
        # Same transforms as training
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load your trained model"""
        if not self.model_path.exists():
            logger.error(f"❌ Model not found: {self.model_path}")
            logger.info("🎯 Run training first: python ai/captcha_learning_system.py --mode train")
            return False
        
        try:
            # Import your model class
            from captcha_learning_system import CaptchaCNN
            
            # Load model
            self.model = CaptchaCNN(num_classes=2)
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            logger.info(f"✅ Model loaded successfully!")
            logger.info(f"📊 Validation accuracy: {checkpoint.get('val_acc', 'Unknown'):.1f}%")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
    
    def predict_solvability(self, image_path):
        """
        Predict if a CAPTCHA is solvable
        
        Args:
            image_path: Path to CAPTCHA screenshot
            
        Returns:
            dict: {
                'solvable': bool,
                'confidence': float,
                'recommendation': str
            }
        """
        if self.model is None:
            return {'solvable': False, 'confidence': 0.0, 'recommendation': 'Model not loaded'}
        
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0)  # Add batch dimension
            
            # Make prediction
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                predicted_class = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][predicted_class].item()
            
            solvable = predicted_class == 1  # 1 = success, 0 = failure
            
            # Generate recommendation
            if solvable and confidence > 0.8:
                recommendation = "🟢 High confidence - attempt solving"
            elif solvable and confidence > 0.6:
                recommendation = "🟡 Medium confidence - proceed with caution"
            elif not solvable and confidence > 0.8:
                recommendation = "🔴 High confidence failure - skip or use service"
            else:
                recommendation = "🟡 Uncertain - use fallback strategy"
            
            return {
                'solvable': solvable,
                'confidence': confidence,
                'recommendation': recommendation,
                'raw_probabilities': {
                    'fail': probabilities[0][0].item(),
                    'success': probabilities[0][1].item()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction failed: {e}")
            return {'solvable': False, 'confidence': 0.0, 'recommendation': f'Error: {e}'}

def main():
    """Demo the predictor"""
    predictor = CaptchaPredictor()
    
    # Test with existing screenshots if available
    screenshots_dir = Path("captcha_training_data/screenshots")
    if screenshots_dir.exists():
        screenshots = list(screenshots_dir.glob("*.png"))[:5]  # Test first 5
        
        print("🧠 Testing CAPTCHA Difficulty Predictions:")
        print("=" * 50)
        
        for screenshot in screenshots:
            result = predictor.predict_solvability(screenshot)
            print(f"📸 {screenshot.name}")
            print(f"   Solvable: {result['solvable']}")
            print(f"   Confidence: {result['confidence']:.1%}")
            print(f"   Recommendation: {result['recommendation']}")
            print(f"   Probabilities: Fail={result['raw_probabilities']['fail']:.1%}, Success={result['raw_probabilities']['success']:.1%}")
            print()
    else:
        print("❌ No screenshots found for testing")
        print("💡 Run data collection first: python ai/captcha_learning_system.py --mode collect")

if __name__ == '__main__':
    main()

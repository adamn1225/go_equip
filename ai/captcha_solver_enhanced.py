#!/usr/bin/env python3
"""
Enhanced CAPTCHA Solver with Learning Integration
Automatically collects data during scraping and can use trained models
"""

import json
import time
import logging
import requests
from pathlib import Path
from PIL import ImageGrab, Image
import numpy as np

try:
    import torch
    import torchvision.transforms as transforms
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    print("⚠️  PyTorch not available. Run: ./setup_captcha_learning.sh")

logger = logging.getLogger(__name__)

class LearningCAPTCHASolver:
    """Enhanced CAPTCHA solver with learning capabilities"""
    
    def __init__(self, api_key_2captcha=None, data_dir="captcha_training_data"):
        self.api_key_2captcha = api_key_2captcha
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "screenshots").mkdir(exist_ok=True)
        (self.data_dir / "solutions").mkdir(exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)
        
        # Load trained model if available
        self.model = None
        self.device = None
        self.transform = None
        
        if PYTORCH_AVAILABLE:
            self._load_trained_model()
    
    def _load_trained_model(self):
        """Load the best trained model if available"""
        model_path = self.data_dir / "models" / "best_captcha_model.pth"
        
        if not model_path.exists():
            logger.info("🤖 No trained model found. Will collect training data.")
            return
        
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            # Load model architecture (simplified for inference)
            from ai.captcha_learning_system import CaptchaCNN
            self.model = CaptchaCNN(num_classes=2).to(self.device)
            
            # Load trained weights
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            # Setup image transforms
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
            logger.info(f"🧠 Loaded trained model (Val Acc: {checkpoint.get('val_acc', 0):.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            self.model = None
    
    def predict_captcha_solvability(self, screenshot_path=None):
        """Use trained model to predict if CAPTCHA can be solved"""
        if not self.model or not screenshot_path:
            return None
        
        try:
            # Load and preprocess image
            image = Image.open(screenshot_path)
            image_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Make prediction
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence = probabilities.max().item()
                prediction = outputs.argmax(dim=1).item()
            
            success_prob = probabilities[0][1].item()  # Probability of success
            
            logger.info(f"🧠 AI Prediction: {success_prob*100:.1f}% chance of success")
            
            return {
                'can_solve': prediction == 1,
                'confidence': confidence,
                'success_probability': success_prob
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction failed: {e}")
            return None
    
    def solve_captcha_with_learning(self, site_url, site_key, captcha_type="hcaptcha"):
        """Solve CAPTCHA with learning integration"""
        session_start = time.time()
        
        # Take screenshot for analysis/learning
        screenshot = self._take_screenshot()
        screenshot_path = None
        if screenshot:
            screenshot_path = self._save_screenshot(screenshot)
        
        # Try AI prediction first if model is available
        ai_prediction = None
        if self.model and screenshot_path:
            ai_prediction = self.predict_captcha_solvability(screenshot_path)
            
            # If AI is very confident it will fail, skip API call
            if ai_prediction and ai_prediction['success_probability'] < 0.2:
                logger.info("🧠 AI predicts low success rate, skipping API call")
                self._save_learning_data(screenshot_path, success=False, 
                                       method='ai_skip', session_time=time.time()-session_start)
                return None
        
        # Try 2captcha API
        result = None
        if self.api_key_2captcha:
            try:
                result = self._solve_with_2captcha(site_url, site_key, captcha_type)
            except Exception as e:
                logger.error(f"API solving failed: {e}")
        
        # Save learning data
        success = result is not None
        method = 'api_success' if success else 'api_failed'
        session_time = time.time() - session_start
        
        self._save_learning_data(screenshot_path, success=success, 
                               method=method, session_time=session_time,
                               ai_prediction=ai_prediction)
        
        return result
    
    def _solve_with_2captcha(self, site_url, site_key, captcha_type):
        """Solve using 2captcha API (same as before)"""
        # Submit CAPTCHA
        submit_data = {
            'key': self.api_key_2captcha,
            'pageurl': site_url
        }
        
        if captcha_type == "hcaptcha":
            submit_data.update({
                'method': 'hcaptcha',
                'sitekey': site_key
            })
        else:  # recaptcha
            submit_data.update({
                'method': 'userrecaptcha', 
                'googlekey': site_key
            })
        
        response = requests.post("http://2captcha.com/in.php", 
                               data=submit_data, timeout=30)
        
        if not response.text.startswith('OK|'):
            logger.error(f"2captcha submission failed: {response.text}")
            return None
        
        captcha_id = response.text.split('|')[1]
        logger.info(f"CAPTCHA submitted to 2captcha: {captcha_id}")
        
        # Poll for solution  
        for attempt in range(24):  # 2 minutes max
            time.sleep(5)
            
            result = requests.get("http://2captcha.com/res.php", params={
                'key': self.api_key_2captcha,
                'action': 'get', 
                'id': captcha_id
            }, timeout=10)
            
            if result.text == 'CAPCHA_NOT_READY':
                continue
            elif result.text.startswith('OK|'):
                solution = result.text.split('|')[1]
                logger.info("✅ CAPTCHA solved by 2captcha!")
                return solution
            else:
                logger.error(f"2captcha error: {result.text}")
                return None
        
        logger.error("2captcha timeout")
        return None
    
    def _take_screenshot(self):
        """Take screenshot of current screen"""
        try:
            screenshot = ImageGrab.grab()
            return np.array(screenshot)
        except:
            return None
    
    def _save_screenshot(self, screenshot):
        """Save screenshot and return path"""
        if screenshot is None:
            return None
        
        timestamp = int(time.time() * 1000)
        filename = f"captcha_{timestamp}.png"
        filepath = self.data_dir / "screenshots" / filename
        
        Image.fromarray(screenshot).save(filepath)
        return str(filepath)
    
    def _save_learning_data(self, screenshot_path, success, method, session_time, ai_prediction=None):
        """Save data for learning"""
        learning_data = {
            'timestamp': time.time(),
            'screenshot': screenshot_path.split('/')[-1] if screenshot_path else None,
            'success': success,
            'method': method,
            'session_time': session_time,
            'ai_prediction': ai_prediction
        }
        
        # Save to learning data
        data_file = self.data_dir / "solutions" / f"auto_session_{int(time.time())}.json"
        with open(data_file, 'w') as f:
            json.dump(learning_data, f, indent=2)
        
        logger.info(f"💾 Saved learning data: {method} ({'✅' if success else '❌'})")
    
    def get_learning_stats(self):
        """Get statistics about collected learning data"""
        sessions = list((self.data_dir / "solutions").glob("*session*.json"))
        
        if not sessions:
            return "📊 No learning data collected yet"
        
        total_sessions = len(sessions)
        successful_sessions = 0
        api_successes = 0
        manual_successes = 0
        ai_predictions = 0
        
        for session_file in sessions:
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                
                if data.get('success', False):
                    successful_sessions += 1
                    
                    method = data.get('method', '')
                    if 'api' in method:
                        api_successes += 1
                    elif 'manual' in method:
                        manual_successes += 1
                
                if data.get('ai_prediction'):
                    ai_predictions += 1
                    
            except:
                continue
        
        stats = f"""
📊 CAPTCHA Learning Statistics:
   Total Sessions: {total_sessions}
   Success Rate: {successful_sessions/total_sessions*100:.1f}%
   API Successes: {api_successes}
   Manual Successes: {manual_successes}
   AI Predictions: {ai_predictions}
   Model Available: {'✅' if self.model else '❌'}
        """
        
        return stats.strip()

# Test the enhanced solver
if __name__ == '__main__':
    solver = LearningCAPTCHASolver()
    print(solver.get_learning_stats())

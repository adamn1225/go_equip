#!/usr/bin/env python3
"""
Context-Aware CAPTCHA Learning System
Captures both the visual puzzle AND the question/prompt for complete understanding
"""

import json
import time
import logging
import requests
import pytesseract
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageGrab
from datetime import datetime
import re

try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    from transformers import BlipProcessor, BlipForConditionalGeneration
    PYTORCH_AVAILABLE = True
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ContextAwareCAPTCHALearner:
    """Enhanced CAPTCHA learner that understands questions AND images"""
    
    def __init__(self, data_dir="captcha_training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "full_screenshots").mkdir(exist_ok=True)
        (self.data_dir / "puzzle_crops").mkdir(exist_ok=True)
        (self.data_dir / "question_crops").mkdir(exist_ok=True)
        (self.data_dir / "solutions").mkdir(exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)
        
        # Load vision-language model if available
        self.vision_model = None
        self.vision_processor = None
        if TRANSFORMERS_AVAILABLE:
            try:
                self.vision_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                self.vision_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
                logger.info("🤖 Vision-Language model loaded (BLIP)")
            except:
                logger.warning("⚠️  Could not load BLIP model")
        
        self.recording = False
        self.session_data = {}
        
    def start_context_collection(self):
        """Start interactive collection with question context"""
        logger.info("🧠 Context-Aware CAPTCHA Learning")
        logger.info("=====================================")
        logger.info("Instructions:")
        logger.info("   1. Type 'start' when CAPTCHA appears")
        logger.info("   2. I'll capture the question AND puzzle")
        logger.info("   3. Solve normally (I'll watch your clicks)")
        logger.info("   4. Type 'save success' or 'save failed'")
        logger.info("   5. Type 'analyze' to see what I learned")
        logger.info("   6. Type 'quit' to exit")
        
        while True:
            command = input("\n🤖 Command (start/save success/save failed/analyze/quit): ").strip().lower()
            
            if command == "start":
                self._start_context_recording()
            elif command in ["save success", "save failed"]:
                success = "success" in command
                self._save_context_session(success)
            elif command == "analyze":
                self._analyze_recent_session()
            elif command == "quit":
                logger.info("👋 Goodbye!")
                break
            else:
                logger.info("❓ Unknown command. Try: start, save success, save failed, analyze, quit")
    
    def _start_context_recording(self):
        """Start recording with full context capture"""
        if self.recording:
            logger.warning("⚠️  Already recording!")
            return
            
        self.recording = True
        logger.info("🔴 Recording started - analyzing CAPTCHA...")
        
        # Take full screenshot
        screenshot = self._take_full_screenshot()
        if not screenshot:
            logger.error("❌ Screenshot failed")
            return
        
        # Analyze the screenshot
        analysis = self._analyze_captcha_context(screenshot)
        
        self.session_data = {
            'timestamp': datetime.now().isoformat(),
            'start_time': time.time(),
            'full_screenshot': self._save_screenshot(screenshot, 'full'),
            'context_analysis': analysis,
            'user_actions': []
        }
        
        logger.info("📸 Full screenshot captured")
        if analysis.get('question_text'):
            logger.info(f"📝 Question detected: '{analysis['question_text']}'")
        if analysis.get('puzzle_type'):
            logger.info(f"🧩 Puzzle type: {analysis['puzzle_type']}")
        
        logger.info("✨ Now solve the CAPTCHA - I'm watching!")
    
    def _analyze_captcha_context(self, screenshot):
        """Analyze screenshot to extract question and puzzle context"""
        analysis = {
            'question_text': None,
            'puzzle_type': None,
            'question_region': None,
            'puzzle_region': None,
            'image_description': None
        }
        
        try:
            # Convert to PIL Image
            pil_image = Image.fromarray(screenshot)
            
            # 1. Try to find and extract question text
            analysis['question_text'] = self._extract_question_text(pil_image)
            analysis['question_region'] = self._find_question_region(pil_image)
            
            # 2. Find puzzle region
            analysis['puzzle_region'] = self._find_puzzle_region(pil_image)
            
            # 3. Classify puzzle type from question
            if analysis['question_text']:
                analysis['puzzle_type'] = self._classify_puzzle_type(analysis['question_text'])
            
            # 4. Generate image description using vision model
            if self.vision_model and analysis['puzzle_region']:
                puzzle_crop = pil_image.crop(analysis['puzzle_region'])
                analysis['image_description'] = self._describe_puzzle_image(puzzle_crop)
            
        except Exception as e:
            logger.error(f"❌ Context analysis failed: {e}")
        
        return analysis
    
    def _extract_question_text(self, image):
        """Extract question text using OCR"""
        try:
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Look for text in upper portion (where questions usually are)
            height, width = cv_image.shape[:2]
            question_area = cv_image[0:int(height*0.3), :]  # Top 30%
            
            # Preprocess for OCR
            gray = cv2.cvtColor(question_area, cv2.COLOR_BGR2GRAY)
            
            # OCR with Tesseract
            question_text = pytesseract.image_to_string(gray).strip()
            
            # Clean up the text
            question_text = re.sub(r'\s+', ' ', question_text)
            question_text = question_text.replace('\n', ' ')
            
            if len(question_text) > 10:  # Reasonable question length
                return question_text
            
        except Exception as e:
            logger.debug(f"OCR failed: {e}")
        
        return None
    
    def _find_question_region(self, image):
        """Find the region containing the question text"""
        # Heuristic: Questions are usually in top 30% of image
        width, height = image.size
        return (0, 0, width, int(height * 0.3))
    
    def _find_puzzle_region(self, image):
        """Find the region containing the puzzle grid"""
        # Heuristic: Puzzle is usually in bottom 70% of image
        width, height = image.size
        return (0, int(height * 0.3), width, height)
    
    def _classify_puzzle_type(self, question_text):
        """Classify puzzle type based on question text"""
        if not question_text:
            return "unknown"
        
        text_lower = question_text.lower()
        
        # Pattern matching for different question types
        patterns = {
            'counting_most': ['most', 'maximum', 'highest number'],
            'counting_least': ['least', 'minimum', 'fewest', 'smallest number'],
            'counting_exact': ['exactly', 'with 3', 'with 4', 'with 5', 'with 6'],
            'color_selection': ['red', 'blue', 'green', 'yellow', 'purple', 'orange'],
            'size_comparison': ['largest', 'biggest', 'smallest', 'tiniest'],
            'object_type': ['flower', 'car', 'bicycle', 'airplane', 'animal'],
            'attribute_matching': ['upside down', 'facing left', 'facing right', 'open', 'closed']
        }
        
        for puzzle_type, keywords in patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return puzzle_type
        
        return "generic"
    
    def _describe_puzzle_image(self, puzzle_image):
        """Use vision model to describe the puzzle image"""
        try:
            inputs = self.vision_processor(puzzle_image, return_tensors="pt")
            out = self.vision_model.generate(**inputs, max_length=50)
            description = self.vision_processor.decode(out[0], skip_special_tokens=True)
            return description
        except Exception as e:
            logger.debug(f"Image description failed: {e}")
            return None
    
    def _take_full_screenshot(self):
        """Take full screen screenshot"""
        try:
            screenshot = ImageGrab.grab()
            return np.array(screenshot)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def _save_screenshot(self, screenshot, prefix):
        """Save screenshot with timestamp"""
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}.png"
        filepath = self.data_dir / "full_screenshots" / filename
        
        Image.fromarray(screenshot).save(filepath)
        return str(filepath.name)
    
    def _save_context_session(self, success):
        """Save session with full context"""
        if not self.recording:
            logger.warning("⚠️  No active recording")
            return
        
        self.recording = False
        
        # Final screenshot
        final_screenshot = self._take_full_screenshot()
        if final_screenshot is not None:
            final_filename = self._save_screenshot(final_screenshot, 'final')
            self.session_data['final_screenshot'] = final_filename
        
        # Complete session data
        self.session_data.update({
            'success': success,
            'duration': time.time() - self.session_data['start_time'],
            'completion_time': datetime.now().isoformat()
        })
        
        # Save session
        session_file = self.data_dir / "solutions" / f"context_session_{int(time.time())}.json"
        with open(session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{status} Context session saved!")
        logger.info(f"📁 File: {session_file}")
        logger.info(f"⏱️  Duration: {self.session_data['duration']:.1f}s")
        
        if self.session_data['context_analysis']['question_text']:
            logger.info(f"📝 Question: {self.session_data['context_analysis']['question_text']}")
        if self.session_data['context_analysis']['puzzle_type']:
            logger.info(f"🧩 Type: {self.session_data['context_analysis']['puzzle_type']}")
    
    def _analyze_recent_session(self):
        """Analyze the most recent session"""
        sessions = sorted(list((self.data_dir / "solutions").glob("context_session_*.json")))
        
        if not sessions:
            logger.info("📊 No sessions to analyze")
            return
        
        latest_session = sessions[-1]
        
        try:
            with open(latest_session, 'r') as f:
                data = json.load(f)
            
            logger.info("🔍 Latest Session Analysis:")
            logger.info("="*40)
            
            # Basic info
            status = "✅ SUCCESS" if data.get('success') else "❌ FAILED"
            logger.info(f"Result: {status}")
            logger.info(f"Duration: {data.get('duration', 0):.1f}s")
            
            # Context analysis
            context = data.get('context_analysis', {})
            if context.get('question_text'):
                logger.info(f"📝 Question: '{context['question_text']}'")
            if context.get('puzzle_type'):
                logger.info(f"🧩 Puzzle Type: {context['puzzle_type']}")
            if context.get('image_description'):
                logger.info(f"👁️  Image: {context['image_description']}")
            
            # Learning insights
            self._generate_learning_insights(data)
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
    
    def _generate_learning_insights(self, session_data):
        """Generate insights from session data"""
        context = session_data.get('context_analysis', {})
        success = session_data.get('success', False)
        question_text = context.get('question_text', '')
        puzzle_type = context.get('puzzle_type', 'unknown')
        
        logger.info("\n💡 Learning Insights:")
        logger.info("-" * 20)
        
        if question_text and puzzle_type != 'unknown':
            if success:
                logger.info(f"✅ Successfully handled '{puzzle_type}' puzzle")
                logger.info(f"   Question pattern: '{question_text[:50]}...'")
            else:
                logger.info(f"❌ Failed on '{puzzle_type}' puzzle")
                logger.info(f"   Challenging pattern: '{question_text[:50]}...'")
        
        # Suggest improvements
        if not success:
            if 'most' in question_text.lower():
                logger.info("💭 Tip: 'Most' questions need counting and comparison")
            elif 'least' in question_text.lower():
                logger.info("💭 Tip: 'Least' questions need counting and finding minimum")
            elif any(color in question_text.lower() for color in ['red', 'blue', 'green']):
                logger.info("💭 Tip: Color questions need accurate color detection")
    
    def get_learning_statistics(self):
        """Get comprehensive learning statistics"""
        sessions = list((self.data_dir / "solutions").glob("context_session_*.json"))
        
        if not sessions:
            return "📊 No context-aware sessions found"
        
        stats = {
            'total_sessions': len(sessions),
            'successful_sessions': 0,
            'puzzle_types': {},
            'question_patterns': {},
            'avg_duration': 0
        }
        
        total_duration = 0
        
        for session_file in sessions:
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                
                if data.get('success'):
                    stats['successful_sessions'] += 1
                
                # Puzzle type analysis
                context = data.get('context_analysis', {})
                puzzle_type = context.get('puzzle_type', 'unknown')
                if puzzle_type not in stats['puzzle_types']:
                    stats['puzzle_types'][puzzle_type] = {'total': 0, 'success': 0}
                
                stats['puzzle_types'][puzzle_type]['total'] += 1
                if data.get('success'):
                    stats['puzzle_types'][puzzle_type]['success'] += 1
                
                # Duration
                duration = data.get('duration', 0)
                total_duration += duration
                
            except:
                continue
        
        if stats['total_sessions'] > 0:
            stats['avg_duration'] = total_duration / stats['total_sessions']
        
        # Format output
        result = f"""
📊 Context-Aware CAPTCHA Learning Statistics:
============================================
Total Sessions: {stats['total_sessions']}
Success Rate: {stats['successful_sessions']/stats['total_sessions']*100:.1f}%
Average Duration: {stats['avg_duration']:.1f}s

🧩 Puzzle Type Performance:
"""
        
        for puzzle_type, data in stats['puzzle_types'].items():
            success_rate = data['success'] / data['total'] * 100 if data['total'] > 0 else 0
            result += f"   {puzzle_type}: {success_rate:.1f}% ({data['success']}/{data['total']})\n"
        
        return result.strip()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Context-Aware CAPTCHA Learning")
    parser.add_argument('--mode', choices=['collect', 'analyze', 'stats'], 
                       default='collect', help='Mode of operation')
    parser.add_argument('--data-dir', default='captcha_training_data',
                       help='Data directory')
    
    args = parser.parse_args()
    
    learner = ContextAwareCAPTCHALearner(args.data_dir)
    
    if args.mode == 'collect':
        learner.start_context_collection()
    elif args.mode == 'stats':
        print(learner.get_learning_statistics())
    elif args.mode == 'analyze':
        learner._analyze_recent_session()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
CAPTCHA Learning System - Watches manual solving to train CNN model
Perfect for learning PyTorch/CUDA with your new NVIDIA GPU!
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import json
import time
from datetime import datetime
import os
import threading
from PIL import Image, ImageGrab
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaptchaDataCollector:
    """Collects training data by watching manual CAPTCHA solving"""
    
    def __init__(self, data_dir="captcha_training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "screenshots").mkdir(exist_ok=True)
        (self.data_dir / "solutions").mkdir(exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)
        
        self.recording = False
        self.session_data = {}
        
        logger.info(f"Data collector initialized: {self.data_dir}")
        
    def start_interactive_collection(self):
        """Start interactive data collection session"""
        logger.info("Starting CAPTCHA learning session...")
        logger.info("Instructions:")
        logger.info("   1. Type 'start' when CAPTCHA appears")
        logger.info("   2. Solve the CAPTCHA normally") 
        logger.info("   3. Type 'save success' or 'save failed' when done")
        logger.info("   4. Type 'quit' to exit")
        
        while True:
            command = input("\n🤖 Enter command (start/save success/save failed/quit): ").strip().lower()
            
            if command == "start":
                self._start_recording()
            elif command in ["save success", "save failed"]:
                success = "success" in command
                self._save_session(success)
            elif command == "quit":
                logger.info("Goodbye")
                break
            else:
                logger.info("Unknown command. Use: start, save success, save failed, or quit")
    
    def _start_recording(self):
        """Start recording a solving session"""
        if not self.recording:
            self.recording = True
            logger.info("Recording started - Solve the CAPTCHA now.")
            
            self.session_data = {
                'timestamp': datetime.now().isoformat(),
                'screenshots': [],
                'start_time': time.time()
            }
            
            # Take initial screenshot
            screenshot = self._take_screenshot()
            filename = self._save_screenshot(screenshot, 'initial')
            self.session_data['screenshots'].append({
                'timestamp': time.time(),
                'filename': filename,
                'type': 'initial'
            })
            
            logger.info("Initial screenshot captured")
    
    def _take_screenshot(self):
        """Capture current screen focused on browser area"""
        try:
            # Capture full screen
            screenshot = ImageGrab.grab()
            return np.array(screenshot)
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def _save_screenshot(self, screenshot, prefix):
        """Save screenshot to disk"""
        if screenshot is None:
            return None
            
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}.png"
        filepath = self.data_dir / "screenshots" / filename
        
        # Convert to PIL and save
        Image.fromarray(screenshot).save(filepath)
        return filename
    
    def _save_session(self, success=True):
        """Save the current session data"""
        if not self.recording:
            logger.warning("No active recording session")
            return
        
        self.recording = False
        logger.info("Saving session data...")

        # Take final screenshot
        final_screenshot = self._take_screenshot()
        if final_screenshot is not None:
            filename = self._save_screenshot(final_screenshot, 'final')
            self.session_data['screenshots'].append({
                'timestamp': time.time(),
                'filename': filename,
                'type': 'final'
            })
        
        # Add session metadata
        self.session_data.update({
            'success': success,
            'duration': time.time() - self.session_data['start_time'],
            'screenshot_count': len(self.session_data['screenshots'])
        })
        
        # Save session metadata
        session_file = self.data_dir / "solutions" / f"session_{int(time.time())}.json"
        with open(session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)

        status = "SUCCESS" if success else "FAILED"
        logger.info(f"{status} Session saved: {session_file}")
        logger.info(f"Screenshots: {len(self.session_data['screenshots'])}")
        logger.info(f"Duration: {self.session_data['duration']:.1f}s")

class CaptchaCNN(nn.Module):
    """CNN model for CAPTCHA solving - GPU optimized"""
    
    def __init__(self, num_classes=2):  # Success/Failure classification to start
        super(CaptchaCNN, self).__init__()
        
        # Feature extraction layers
        self.features = nn.Sequential(
            # First conv block
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            
            # Second conv block  
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Third conv block
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # Fourth conv block
            nn.Conv2d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((7, 7))
        )
        
        # Classification layers
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(512 * 7 * 7, 2048),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(2048, 1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

class CaptchaTrainer:
    """Trains CNN model on collected CAPTCHA data"""
    
    def __init__(self, data_dir="captcha_training_data"):
        self.data_dir = Path(data_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Using device: {self.device}")
        if self.device.type == "cuda":
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
        
        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
    def load_training_data(self):
        """Load collected training data"""
        sessions = list((self.data_dir / "solutions").glob("session_*.json"))
        
        if not sessions:
            logger.error("No training data found! Collect some data first.")
            return None, None

        logger.info(f"Loading {len(sessions)} training sessions...")

        images = []
        labels = []
        
        for session_file in sessions:
            try:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                
                # Load final screenshot (result of solving attempt)
                final_screenshot = None
                for screenshot in session['screenshots']:
                    if screenshot['type'] == 'final':
                        img_path = self.data_dir / "screenshots" / screenshot['filename']
                        if img_path.exists():
                            final_screenshot = Image.open(img_path)
                            break
                
                if final_screenshot:
                    # Apply transforms
                    img_tensor = self.transform(final_screenshot)
                    images.append(img_tensor)
                    
                    # Label: 1 for success, 0 for failure
                    labels.append(1 if session.get('success', False) else 0)
                
            except Exception as e:
                logger.warning(f"Skipped session {session_file}: {e}")

        if not images:
            logger.error("No valid training images found!")
            return None, None

        logger.info(f"Loaded {len(images)} training samples")
        logger.info(f"Success rate: {sum(labels)/len(labels)*100:.1f}%")
        
        return torch.stack(images), torch.tensor(labels, dtype=torch.long)
    
    def train_model(self, epochs=20, batch_size=8, learning_rate=0.001):
        """Train the CNN model"""
        logger.info("Starting model training...")
        
        # Load data
        images, labels = self.load_training_data()
        if images is None:
            return None
        
        # Create dataset
        dataset = torch.utils.data.TensorDataset(images, labels)
        
        # Split into train/validation
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
        
        # Create data loaders
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Initialize model
        model = CaptchaCNN(num_classes=2).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        
        logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        # Training loop
        best_val_acc = 0.0
        
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_images, batch_labels in train_loader:
                batch_images = batch_images.to(self.device)
                batch_labels = batch_labels.to(self.device)
                
                optimizer.zero_grad()
                outputs = model(batch_images)
                loss = criterion(outputs, batch_labels)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += batch_labels.size(0)
                train_correct += predicted.eq(batch_labels).sum().item()
            
            train_acc = 100.0 * train_correct / train_total
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for batch_images, batch_labels in val_loader:
                    batch_images = batch_images.to(self.device)
                    batch_labels = batch_labels.to(self.device)
                    
                    outputs = model(batch_images)
                    _, predicted = outputs.max(1)
                    val_total += batch_labels.size(0)
                    val_correct += predicted.eq(batch_labels).sum().item()
            
            val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                model_path = self.data_dir / "models" / "best_captcha_model.pth"
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_acc': val_acc,
                    'train_acc': train_acc
                }, model_path)
            
            logger.info(f"Epoch [{epoch+1}/{epochs}] - Train Acc: {train_acc:.2f}% | Val Acc: {val_acc:.2f}%")
        
        logger.info(f"Training completed! Best validation accuracy: {best_val_acc:.2f}%")
        return model

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="CAPTCHA Learning System")
    parser.add_argument('--mode', choices=['collect', 'train', 'info'], 
                       default='collect', help='Mode: collect data or train model')
    parser.add_argument('--data-dir', default='captcha_training_data', 
                       help='Directory for training data')
    parser.add_argument('--epochs', type=int, default=20, 
                       help='Training epochs')
    parser.add_argument('--batch-size', type=int, default=8, 
                       help='Training batch size')
    
    args = parser.parse_args()
    
    if args.mode == 'collect':
        collector = CaptchaDataCollector(args.data_dir)
        collector.start_interactive_collection()
        
    elif args.mode == 'train':
        trainer = CaptchaTrainer(args.data_dir)
        model = trainer.train_model(epochs=args.epochs, batch_size=args.batch_size)
        
    elif args.mode == 'info':
        data_dir = Path(args.data_dir)
        if not data_dir.exists():
            logger.info("No training data directory found")
            return
        
        sessions = list((data_dir / "solutions").glob("session_*.json"))
        screenshots = list((data_dir / "screenshots").glob("*.png"))
        models = list((data_dir / "models").glob("*.pth"))

        logger.info(f"Training Data Summary:")
        logger.info(f"   Sessions: {len(sessions)}")
        logger.info(f"   Screenshots: {len(screenshots)}")
        logger.info(f"   Models: {len(models)}")
        
        if sessions:
            success_count = 0
            for session_file in sessions:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                    if session.get('success', False):
                        success_count += 1
            
            logger.info(f"   Success Rate: {success_count/len(sessions)*100:.1f}%")

if __name__ == '__main__':
    main()

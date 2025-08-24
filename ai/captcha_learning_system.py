#!/usr/bin/env python3
"""
🎓 CAPTCHA Learning System - Educational Edition
Perfect for learning PyTorch/CUDA with your new NVIDIA GPU!

📚 MACHINE LEARNING CONCEPTS EXPLAINED:

🧠 WHAT IS MACHINE LEARNING?
Instead of programming explicit rules, we show the computer lots of examples
and let it figure out patterns. Like teaching a child to recognize cats by
showing thousands of cat photos instead of describing "pointy ears, whiskers..."

🔍 WHAT IS A CONVOLUTIONAL NEURAL NETWORK (CNN)?
A type of AI designed for image recognition. It mimics how your visual cortex works:
- Early layers detect simple features (edges, colors)  
- Middle layers detect shapes and textures
- Deep layers detect objects ("this is a flower")
- Final layers make decisions ("I can solve this CAPTCHA")

🎯 OUR SPECIFIC TASK:
We're training a model to look at CAPTCHA screenshots and predict:
"Can I successfully solve this CAPTCHA or will I fail?"

🏗️ THE TRAINING PROCESS:
1. COLLECT DATA: Take screenshots when you solve CAPTCHAs, record success/failure
2. PREPARE DATA: Resize images, normalize colors, split into train/test sets
3. BUILD MODEL: Create a neural network architecture (the "brain")
4. TRAIN MODEL: Show it thousands of examples, let it learn patterns
5. VALIDATE MODEL: Test on unseen data to make sure it actually learned
6. USE MODEL: Give it new CAPTCHA screenshots and get predictions

🔬 KEY TERMS YOU'LL SEE:
- Tensor: Multi-dimensional array (like a 3D spreadsheet for images)
- Forward Pass: Data flowing through the network to make a prediction
- Backward Pass: Calculating how to improve the model (using calculus!)
- Loss: How wrong the model's predictions are
- Gradient: Direction to adjust parameters to reduce loss
- Epoch: One complete pass through all training data
- Batch: Group of images processed together (for efficiency)
- Learning Rate: How big steps to take when adjusting the model
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
    """
    CNN (Convolutional Neural Network) model for CAPTCHA solving
    
    🧠 WHAT IS A CNN?
    Think of it like your brain processing vision:
    - Early layers detect simple features (edges, colors)
    - Deeper layers detect complex patterns (shapes, objects)
    - Final layers make decisions based on what it "sees"
    
    🏗️ ARCHITECTURE OVERVIEW:
    Input Image → Feature Detection → Pattern Recognition → Decision
    """
    
    def __init__(self, num_classes=2):  # 2 classes: "Can solve CAPTCHA" vs "Cannot solve"
        super(CaptchaCNN, self).__init__()  # Initialize the parent PyTorch neural network class
        
        # 🔍 FEATURE EXTRACTION SECTION
        # This part "looks" at the image and finds important visual patterns
        self.features = nn.Sequential(  # Sequential = run these layers one after another
            
            # 🧱 FIRST CONVOLUTIONAL BLOCK - "Edge Detection"
            # Input: Raw RGB image (3 color channels: Red, Green, Blue)
            nn.Conv2d(
                in_channels=3,      # 3 = RGB colors coming in
                out_channels=64,    # 64 = number of different "filters" to learn
                kernel_size=7,      # 7x7 pixel window that slides across image
                stride=2,           # Skip 2 pixels each step (makes image smaller/faster)
                padding=3           # Add border pixels so we don't lose edge info
            ),
            # 📊 ANALOGY: Think of 64 different "detectives" each looking for different patterns
            # One might detect horizontal lines, another vertical lines, etc.
            
            nn.BatchNorm2d(64),     # 🧹 "Normalize" data to train faster & more stable
            # ANALOGY: Like adjusting brightness/contrast consistently
            
            nn.ReLU(inplace=True),  # 🚪 "Activation Function" - decides what info to keep
            # ReLU = "if negative, make it 0, else keep it"
            # ANALOGY: Like a bouncer - only lets "excited neurons" pass through
            
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),  # 🔽 Shrink image size
            # Takes 3x3 area and keeps only the MAXIMUM value
            # ANALOGY: Like zooming out - keeps the most important info, discards details
            
            # 🧱 SECOND CONVOLUTIONAL BLOCK - "Shape Detection"
            # Now looking for more complex patterns in the simplified image
            nn.Conv2d(64, 128, kernel_size=3, padding=1),  # 64→128 = learn MORE patterns
            nn.BatchNorm2d(128),    # Keep training stable
            nn.ReLU(inplace=True),  # Keep only "excited" neurons
            nn.MaxPool2d(2, 2),     # Shrink image more
            
            # 🧱 THIRD CONVOLUTIONAL BLOCK - "Object Parts Detection"
            # Even more complex patterns (like "flower petal" or "car wheel")
            nn.Conv2d(128, 256, kernel_size=3, padding=1),  # 128→256 = EVEN MORE patterns
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            # 🧱 FOURTH CONVOLUTIONAL BLOCK - "Object Detection"
            # Highest-level features (like "this looks like a complete flower")
            nn.Conv2d(256, 512, kernel_size=3, padding=1),  # 256→512 = MOST patterns
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            
            # 🎯 ADAPTIVE POOLING - Force output to be exactly 7x7 pixels
            # No matter what size image goes in, we get consistent 7x7 output
            nn.AdaptiveAvgPool2d((7, 7))  # Average (not max) pooling for final layer
        )
        
        # 🧠 CLASSIFICATION SECTION - "Decision Making"
        # Takes the visual features and decides: "Can I solve this CAPTCHA?"
        self.classifier = nn.Sequential(
            
            nn.Dropout(0.5),        # 🎲 Randomly "turn off" 50% of neurons during training
            # WHY? Prevents "overfitting" - forces model to not rely on specific neurons
            # ANALOGY: Like studying with random pages blocked out - makes you more robust
            
            nn.Linear(              # 🔗 "Fully Connected Layer" - every input connects to every output
                in_features=512 * 7 * 7,  # Input: 512 patterns × 7×7 pixels = 25,088 numbers
                out_features=2048          # Output: 2048 "decision neurons"
            ),
            # MATH EXPLANATION: We flattened 512 different 7x7 feature maps into one long list
            # Each of the 25,088 input numbers connects to each of the 2048 outputs
            # That's 51,380,224 connections! (This is why we need a GPU)
            
            nn.ReLU(inplace=True),  # Keep only positive decision signals
            nn.Dropout(0.5),        # Again, randomly turn off neurons to prevent overfitting
            
            nn.Linear(2048, 1024),  # 🔗 Smaller decision layer - distill information
            nn.ReLU(inplace=True),
            
            nn.Linear(1024, num_classes)  # 🎯 FINAL DECISION: 2 outputs
            # Output[0] = confidence this CAPTCHA will FAIL
            # Output[1] = confidence this CAPTCHA will SUCCEED
            # Whichever is higher wins!
        )
        
    def forward(self, x):
        """
        🚀 THE FORWARD PASS - How data flows through the neural network
        
        This is like an assembly line where an image gets processed step by step:
        1. Raw image goes into feature extraction
        2. Features get flattened into a list
        3. List goes through decision-making layers
        4. Final prediction comes out
        
        INPUT: x = batch of images, shape [batch_size, 3, height, width]
        Example: [8, 3, 224, 224] = 8 images, RGB, 224x224 pixels each
        """
        
        # 🔍 STEP 1: FEATURE EXTRACTION
        # Run the image through all the convolutional layers
        x = self.features(x)  
        # OUTPUT SHAPE: [batch_size, 512, 7, 7]
        # MEANING: For each image, we now have 512 different 7x7 "feature maps"
        # Each feature map highlights where certain patterns appear in the image
        
        # 🔄 STEP 2: FLATTEN FOR DECISION MAKING
        # Neural network classifiers need a flat list, not a 3D cube
        x = x.view(x.size(0), -1)  
        # BEFORE: [batch_size, 512, 7, 7] = 3D data
        # AFTER:  [batch_size, 25088] = flat list (512 × 7 × 7 = 25,088)
        # ANALOGY: Like taking a Rubik's cube apart and laying all pieces in a line
        
        # 🧠 STEP 3: MAKE DECISION
        # Pass the flattened features through decision-making layers
        x = self.classifier(x)
        # OUTPUT SHAPE: [batch_size, 2]
        # MEANING: For each image, get 2 numbers:
        #   x[i][0] = "confidence this CAPTCHA will fail"
        #   x[i][1] = "confidence this CAPTCHA will succeed"
        
        return x
        # The training process will teach the network to output higher numbers
        # for the correct answer and lower numbers for the wrong answer

class CaptchaTrainer:
    """Trains CNN model on collected CAPTCHA data"""
    
    def __init__(self, data_dir="captcha_training_data"):
        self.data_dir = Path(data_dir)
        
        # 🚀 SMART DEVICE SELECTION - RTX 5070 now supported with CUDA 12.8!
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Using device: {self.device}")
        if self.device.type == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            capability = torch.cuda.get_device_capability(0)
            logger.info(f"🚀 GPU: {gpu_name}")
            logger.info(f"⚡ Compute Capability: sm_{capability[0]}{capability[1]}")
            logger.info(f"💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
            
            if capability >= (12, 0):
                logger.info("🎉 RTX 50-series GPU detected with full PyTorch support!")
        else:
            import os
            cpu_count = os.cpu_count()
            logger.info(f"🖥️  CPU: {cpu_count} cores - optimizing for multi-core training")
            torch.set_num_threads(cpu_count)
            torch.set_num_interop_threads(cpu_count)
        
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
        """
        🎓 TRAIN THE CNN MODEL - This is where the "learning" happens!
        
        🚀 OPTIMIZED FOR RTX 5070 WITH CUDA 12.8:
        - Full GPU acceleration with Blackwell architecture support
        - Automatic batch size optimization for GPU/CPU
        - Multi-core CPU fallback if needed
        
        🔄 TRAINING PROCESS OVERVIEW:
        1. Show the model examples (images + correct answers)
        2. Model makes predictions 
        3. Calculate how wrong the predictions are (loss)
        4. Adjust the model's "weights" to be less wrong
        5. Repeat thousands of times until model gets smart!
        
        PARAMETERS EXPLAINED:
        - epochs: How many times to show ALL training data (20 = see everything 20 times)
        - batch_size: How many images to process at once (8 = process 8 images together)  
        - learning_rate: How big steps to take when adjusting (0.001 = small careful steps)
        """
        
        # 🎯 AUTO-OPTIMIZE BATCH SIZE FOR DEVICE
        if self.device.type == "cpu":
            batch_size = min(batch_size, 4)
            logger.info(f"🖥️  CPU training optimized: batch_size={batch_size}")
        else:
            # GPU can handle larger batches
            logger.info(f"� GPU training: batch_size={batch_size}")
            
        logger.info("Starting model training...")
    
    def train_model_original(self, epochs=20, batch_size=8, learning_rate=0.001):
        """
        🎓 TRAIN THE CNN MODEL - This is where the "learning" happens!
        
        🔄 TRAINING PROCESS OVERVIEW:
        1. Show the model examples (images + correct answers)
        2. Model makes predictions 
        3. Calculate how wrong the predictions are (loss)
        4. Adjust the model's "weights" to be less wrong
        5. Repeat thousands of times until model gets smart!
        
        PARAMETERS EXPLAINED:
        - epochs: How many times to show ALL training data (20 = see everything 20 times)
        - batch_size: How many images to process at once (8 = process 8 images together)  
        - learning_rate: How big steps to take when adjusting (0.001 = small careful steps)
        """
        logger.info("Starting model training...")
        
        # 📊 STEP 1: LOAD AND PREPARE DATA
        images, labels = self.load_training_data()
        if images is None:
            return None
        
        # 🎲 STEP 2: CREATE DATASET AND SPLIT IT
        dataset = torch.utils.data.TensorDataset(images, labels)
        # EXPLANATION: Pairs each image with its correct answer (success/fail)
        
        # 📚 Split data: 80% for training, 20% for testing how well we learned
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
        # WHY SPLIT? We need "unseen" data to test if model actually learned vs just memorized
        
        # 🚚 STEP 3: CREATE DATA LOADERS (Efficient Batch Processing)
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        # ANALOGY: Like organizing books into carts for librarians to process efficiently
        
        # 🏗️ STEP 4: INITIALIZE THE MODEL AND TRAINING TOOLS
        model = CaptchaCNN(num_classes=2).to(self.device)  # Move model to GPU if available
        
        # 📏 LOSS FUNCTION - "How wrong are our predictions?"
        criterion = nn.CrossEntropyLoss()  
        # EXPLANATION: Measures difference between what model predicted vs correct answer
        # If model says 90% confident it will fail, but it actually succeeded = HIGH LOSS
        
        # 🎯 OPTIMIZER - "How to adjust the model to be less wrong?"
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        # ADAM = Smart algorithm that adjusts learning based on recent progress
        # ANALOGY: Like a GPS that adjusts route based on current traffic
        
        logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        # EXPLANATION: Shows how many individual "weights" the model has to learn
        # Typical CNN has millions of parameters!
        
        # 🏆 TRAINING TRACKING
        best_val_acc = 0.0  # Keep track of best performance so far
        
        # 🔄 MAIN TRAINING LOOP - The Heart of Machine Learning!
        for epoch in range(epochs):
            logger.info(f"Starting epoch {epoch+1}/{epochs}")
            
            # 📖 TRAINING PHASE - Show model examples and let it learn
            model.train()  # Tell PyTorch "we're in learning mode" (affects dropout, etc.)
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_images, batch_labels in train_loader:
                # 📦 PROCESS ONE BATCH of images
                batch_images = batch_images.to(self.device)  # Move to GPU
                batch_labels = batch_labels.to(self.device)  # Move to GPU
                
                # 🧠 STEP A: FORWARD PASS - Make predictions
                optimizer.zero_grad()  # Clear previous gradients (like clearing a calculator)
                outputs = model(batch_images)  # Get model's predictions
                
                # 📏 STEP B: CALCULATE LOSS - How wrong were we?
                loss = criterion(outputs, batch_labels)  # Compare predictions to correct answers
                
                # 🔄 STEP C: BACKWARD PASS - Learn from mistakes
                loss.backward()  # Calculate how to adjust each parameter
                # MAGIC HAPPENS HERE: PyTorch calculates gradients using calculus!
                
                # 🎯 STEP D: UPDATE MODEL - Apply the adjustments
                optimizer.step()  # Actually adjust the model parameters
                
                # 📊 TRACK STATISTICS for this batch
                train_loss += loss.item()
                _, predicted = outputs.max(1)  # Get the class with highest confidence
                train_total += batch_labels.size(0)
                train_correct += predicted.eq(batch_labels).sum().item()
            
            # 📈 Calculate training accuracy for this epoch
            train_acc = 100.0 * train_correct / train_total
            
            # 🧪 VALIDATION PHASE - Test on unseen data
            model.eval()  # Tell PyTorch "we're in evaluation mode" (turns off dropout)
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():  # Don't calculate gradients (saves memory & speed)
                for batch_images, batch_labels in val_loader:
                    batch_images = batch_images.to(self.device)
                    batch_labels = batch_labels.to(self.device)
                    
                    outputs = model(batch_images)  # Make predictions
                    _, predicted = outputs.max(1)  # Get predicted class
                    val_total += batch_labels.size(0)
                    val_correct += predicted.eq(batch_labels).sum().item()
            
            val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0
            
            # 💾 SAVE BEST MODEL - Keep the version that performs best on validation
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                model_path = self.data_dir / "models" / "best_captcha_model.pth"
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),  # The learned parameters
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_acc': val_acc,
                    'train_acc': train_acc
                }, model_path)
                logger.info(f"🎉 New best model saved! Validation accuracy: {val_acc:.2f}%")
            
            # 📊 LOG PROGRESS
            logger.info(f"Epoch [{epoch+1}/{epochs}] - Train Acc: {train_acc:.2f}% | Val Acc: {val_acc:.2f}%")
            
            # 🎯 TRAINING INSIGHTS for beginners:
            if train_acc > val_acc + 10:
                logger.info("📚 Note: Training accuracy much higher than validation = possible overfitting")
                logger.info("💡 Consider: more data, dropout, or early stopping")
            elif val_acc > train_acc:
                logger.info("✨ Great! Validation accuracy higher than training = good generalization")
        
        logger.info(f"🏁 Training completed! Best validation accuracy: {best_val_acc:.2f}%")
        logger.info(f"🧠 The model has learned to predict CAPTCHA solvability with {best_val_acc:.1f}% accuracy!")
        
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

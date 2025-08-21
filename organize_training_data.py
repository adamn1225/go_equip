#!/usr/bin/env python3
"""
Organize CAPTCHA training data into sessions for the learning system
Converts individual solution files into training sessions
"""

import json
import os
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def organize_training_data(data_dir="captcha_training_data"):
    """Convert individual solutions into training sessions"""
    data_path = Path(data_dir)
    solutions_dir = data_path / "solutions"
    screenshots_dir = data_path / "screenshots"
    
    # Find all solution files
    solution_files = list(solutions_dir.glob("solution_*.json"))
    logger.info(f"Found {len(solution_files)} solution files")
    
    if not solution_files:
        logger.error("No solution files found!")
        return
    
    # Create training sessions from solutions
    sessions_created = 0
    
    for solution_file in solution_files:
        try:
            with open(solution_file, 'r') as f:
                solution_data = json.load(f)
            
            # Extract timestamp from filename or solution data
            if 'timestamp' in solution_data:
                timestamp = solution_data['timestamp']
            else:
                # Extract from filename: solution_20250821_145906.json
                filename = solution_file.name
                timestamp_str = filename.replace('solution_', '').replace('.json', '')
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').isoformat()
            
            # Find corresponding screenshot
            screenshot_pattern = f"screenshot_{timestamp_str}*.png"
            screenshots = list(screenshots_dir.glob(screenshot_pattern))
            
            if not screenshots:
                # Try worker screenshots: worker*_screenshot_timestamp.png
                worker_pattern = f"worker*_screenshot_{timestamp_str}*.png"
                screenshots = list(screenshots_dir.glob(worker_pattern))
            
            if not screenshots:
                logger.warning(f"No screenshot found for {solution_file.name}")
                continue
            
            screenshot_path = str(screenshots[0])
            
            # Create session data
            session_data = {
                "session_id": f"session_{timestamp_str}",
                "timestamp": timestamp,
                "screenshot_path": screenshot_path,
                "solution": solution_data.get('solution', 'unknown'),
                "success": solution_data.get('success', True),
                "method": solution_data.get('method', 'manual'),
                "captcha_type": solution_data.get('captcha_type', 'unknown'),
                "processing_time": solution_data.get('processing_time', 0)
            }
            
            # Save as session file
            session_file = solutions_dir / f"session_{timestamp_str}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            sessions_created += 1
            logger.info(f"Created session: {session_file.name}")
            
        except Exception as e:
            logger.error(f"Error processing {solution_file.name}: {e}")
    
    logger.info(f"Successfully created {sessions_created} training sessions")
    
    # Also create sessions for screenshots without solutions (from enhanced scraper)
    logger.info("Creating sessions for screenshots without solutions...")
    
    all_screenshots = list(screenshots_dir.glob("*.png"))
    screenshots_with_sessions = sessions_created
    
    for screenshot in all_screenshots:
        screenshot_name = screenshot.name
        
        # Check if this screenshot already has a session
        timestamp_parts = screenshot_name.split('_')
        if len(timestamp_parts) >= 2:
            try:
                # Extract timestamp from various formats
                if 'worker' in screenshot_name:
                    # worker4_screenshot_20250821_175514.png
                    timestamp_str = '_'.join(timestamp_parts[-2:]).replace('.png', '')
                else:
                    # screenshot_20250821_145906.png
                    timestamp_str = '_'.join(timestamp_parts[-2:]).replace('.png', '')
                
                session_file = solutions_dir / f"session_{timestamp_str}.json"
                
                if not session_file.exists():
                    # Create a basic session for CAPTCHA screenshots
                    session_data = {
                        "session_id": f"session_{timestamp_str}",
                        "timestamp": datetime.now().isoformat(),
                        "screenshot_path": str(screenshot),
                        "solution": "unlabeled",
                        "success": False,  # Unknown success status
                        "method": "automated_capture",
                        "captcha_type": "unknown",
                        "processing_time": 0,
                        "needs_labeling": True
                    }
                    
                    with open(session_file, 'w') as f:
                        json.dump(session_data, f, indent=2)
                    
                    sessions_created += 1
                    
            except Exception as e:
                logger.warning(f"Could not create session for {screenshot_name}: {e}")
    
    logger.info(f"Total sessions created: {sessions_created}")
    logger.info(f"Training data is now organized for the learning system!")

if __name__ == "__main__":
    organize_training_data()

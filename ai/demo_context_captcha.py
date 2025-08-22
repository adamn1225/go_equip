#!/usr/bin/env python3
"""
Demo: Context-Aware CAPTCHA Learning
Shows how the system handles different question types
"""

import json
from pathlib import Path

# Mock session data to demonstrate the concept
mock_sessions = [
    {
        "timestamp": "2025-08-22T10:30:00",
        "success": True,
        "duration": 12.3,
        "context_analysis": {
            "question_text": "Please click on the flower with the most petals",
            "puzzle_type": "counting_most", 
            "image_description": "a grid showing 9 different flowers with varying numbers of petals"
        }
    },
    {
        "timestamp": "2025-08-22T10:35:00", 
        "success": False,
        "duration": 18.7,
        "context_analysis": {
            "question_text": "Please click on the flower with the least petals",
            "puzzle_type": "counting_least",
            "image_description": "a grid showing 9 different flowers, some with 3 petals, others with 5-8 petals"
        }
    },
    {
        "timestamp": "2025-08-22T10:40:00",
        "success": True, 
        "duration": 8.9,
        "context_analysis": {
            "question_text": "Select all flowers containing exactly 6 petals",
            "puzzle_type": "counting_exact",
            "image_description": "a grid of flowers where some have exactly 6 petals and others have different amounts"
        }
    },
    {
        "timestamp": "2025-08-22T10:45:00",
        "success": True,
        "duration": 6.2, 
        "context_analysis": {
            "question_text": "Click on all the red flowers",
            "puzzle_type": "color_selection",
            "image_description": "a mix of red, yellow, and pink flowers in a 3x3 grid"
        }
    }
]

def demo_context_awareness():
    """Demonstrate how context-aware learning solves the question variation problem"""
    
    print("🧠 Context-Aware CAPTCHA Learning Demo")
    print("=" * 50)
    print()
    print("🎯 THE PROBLEM YOU IDENTIFIED:")
    print("   Traditional systems only look at images, but hCAPTCHA questions change:")
    print("   • 'Click the flower with the MOST petals'")
    print("   • 'Click the flower with the LEAST petals'") 
    print("   • 'Select flowers with EXACTLY 6 petals'")
    print("   • 'Choose all RED flowers'")
    print()
    print("✨ OUR SOLUTION:")
    print("   Capture BOTH the question text AND the puzzle image!")
    print()
    
    # Analyze the mock sessions
    print("📊 LEARNING SESSION ANALYSIS:")
    print("-" * 30)
    
    question_patterns = {}
    
    for i, session in enumerate(mock_sessions, 1):
        context = session["context_analysis"]
        success = "✅" if session["success"] else "❌"
        
        print(f"\n🔍 Session {i}: {success}")
        print(f"   Question: '{context['question_text']}'")
        print(f"   Type: {context['puzzle_type']}")
        print(f"   Duration: {session['duration']}s")
        print(f"   Image: {context['image_description']}")
        
        # Track patterns
        pattern = context['puzzle_type']
        if pattern not in question_patterns:
            question_patterns[pattern] = {'total': 0, 'success': 0}
        question_patterns[pattern]['total'] += 1
        if session['success']:
            question_patterns[pattern]['success'] += 1
    
    print("\n" + "=" * 50)
    print("🎓 LEARNING INSIGHTS:")
    print()
    
    for pattern, stats in question_patterns.items():
        success_rate = stats['success'] / stats['total'] * 100
        status = "🎯" if success_rate >= 100 else "⚠️" if success_rate >= 50 else "❌"
        
        print(f"{status} {pattern.replace('_', ' ').title()}: {success_rate:.0f}% success rate")
        
        # Specific insights
        if pattern == "counting_least" and success_rate < 100:
            print("   💡 Insight: Need to focus on finding MINIMUM counts")
        elif pattern == "counting_most" and success_rate >= 100:
            print("   💡 Insight: Successfully handling MAXIMUM counts")
        elif pattern == "color_selection" and success_rate >= 100:
            print("   💡 Insight: Color detection working well")
    
    print("\n🚀 NEXT STEPS:")
    print("   1. Run: ./ai/setup_context_captcha.sh")
    print("   2. Start learning: python3 ai/captcha_context_learner.py")
    print("   3. Train on different question patterns")
    print("   4. Build AI model that understands questions + images")
    print()
    print("💪 ADVANTAGES:")
    print("   ✅ Handles question variations automatically")
    print("   ✅ Learns patterns for each question type")
    print("   ✅ Adapts to new question formats")
    print("   ✅ Combines OCR + Computer Vision + NLP")
    print("   ✅ Gets smarter with each solving session")

def show_question_classification_demo():
    """Show how questions get classified into actionable types"""
    
    print("\n" + "=" * 50)
    print("🔤 QUESTION CLASSIFICATION DEMO")
    print("=" * 50)
    
    test_questions = [
        "Please click on the flower with the most petals",
        "Select the flower with the least petals", 
        "Choose all flowers containing exactly 6 petals",
        "Click on all the red flowers",
        "Select the largest flower",
        "Pick all upside down airplanes",
        "Choose vehicles facing left"
    ]
    
    # Simulate classification (this is what the real system does)
    classifications = [
        "counting_most",
        "counting_least", 
        "counting_exact",
        "color_selection",
        "size_comparison",
        "attribute_matching",
        "attribute_matching"
    ]
    
    print("Question Text → Classified Type → Action Strategy")
    print("-" * 70)
    
    for question, classification in zip(test_questions, classifications):
        strategy = get_strategy_for_type(classification)
        print(f"'{question[:35]}...' → {classification} → {strategy}")
    
def get_strategy_for_type(puzzle_type):
    """Get solving strategy for each puzzle type"""
    strategies = {
        "counting_most": "Count objects, select maximum",
        "counting_least": "Count objects, select minimum", 
        "counting_exact": "Count objects, select matches",
        "color_selection": "Detect colors, select matches",
        "size_comparison": "Measure sizes, select by criteria",
        "attribute_matching": "Detect attributes, filter matches"
    }
    return strategies.get(puzzle_type, "Generic pattern matching")

if __name__ == "__main__":
    demo_context_awareness()
    show_question_classification_demo()
    
    print("\n🎉 Ready to solve your CAPTCHA question variation problem!")
    print("   The system now understands context, not just images!")

#!/usr/bin/env python3
"""
Simple test to verify the Jutge Problem Solver system
"""

import os
from jutge_solver import JutgeProblemSolver, Config

def test_problem_reading():
    """Test reading and analyzing a problem"""
    print("🧪 Testing problem reading...")
    
    config = Config.load_from_env()
    config.load_env_file()
    
    solver = JutgeProblemSolver(config)
    
    # Test without authentication first (public problem)
    try:
        problem_info = solver.problem_analyzer.analyze_problem("P68688_en")
        if problem_info["success"]:
            print("✅ Problem reading successful!")
            print(f"   Title: {problem_info['title']}")
            print(f"   Author: {problem_info['author']}")
            return True
        else:
            print(f"❌ Problem reading failed: {problem_info.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Problem reading failed with exception: {e}")
        return False

def test_authentication():
    """Test Jutge authentication"""
    print("🧪 Testing Jutge authentication...")
    
    config = Config.load_from_env()
    config.load_env_file()
    
    if not config.jutge.email or not config.jutge.password:
        print("❌ Jutge credentials not found in environment")
        return False
    
    solver = JutgeProblemSolver(config)
    
    try:
        if solver.authenticate():
            print("✅ Jutge authentication successful!")
            return True
        else:
            print("❌ Jutge authentication failed")
            return False
    except Exception as e:
        print(f"❌ Jutge authentication failed with exception: {e}")
        return False

def test_openai_setup():
    """Test OpenAI API setup (without actual call)"""
    print("🧪 Testing OpenAI setup...")
    
    config = Config.load_from_env()
    config.load_env_file()
    
    if not config.openai.api_key:
        print("❌ OpenAI API key not found in environment")
        print("   Please add OPENAI_API_KEY to your .env file")
        return False
    
    try:
        solver = JutgeProblemSolver(config)
        print("✅ OpenAI client initialized successfully!")
        print(f"   Model: {config.openai.model}")
        return True
    except Exception as e:
        print(f"❌ OpenAI setup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Jutge Problem Solver System")
    print("=" * 50)
    
    tests = [
        test_problem_reading,
        test_authentication,
        test_openai_setup
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 50)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All tests passed! System is ready to use.")
        print("\nTry running:")
        print("  python cli.py solve P68688_en")
    else:
        print("⚠️  Some tests failed. Please check your configuration.")
        print("\nTo setup configuration:")
        print("  python cli.py config --interactive")

if __name__ == "__main__":
    main()
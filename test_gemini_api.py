"""
Test script for Gemini API integration.
This script tests the basic functionality of the Gemini API module.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the gemini_api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module we want to test
from gemini_api import _check_gemini_availability, APIError # Changed import


def test_gemini_availability():
    """Test if Gemini API is available and properly configured"""
    print("Testing Gemini API availability...")
    try:
        result = _check_gemini_availability() # Changed function call
        if result:
            print("✅ Gemini API is available and properly configured!")
        else:
            print("❌ Gemini API is not available or not properly configured.")
        return result
    except Exception as e:
        print(f"❌ Gemini API is not available: {e}")
        return False


def test_simple_generation():
    """Test a simple text generation with Gemini API"""
    try:
        # Only import these if the API is available
        import google.generativeai as genai

        print("\nTesting simple text generation...")

        # Get API key from environment variable or config
        from utils import get_api_key_securely
        api_key = get_api_key_securely("gemini")

        # Create a model instance (Corrected)
        model = genai.GenerativeModel('gemini-1.5-flash') # Changed client

        # Generate content
        response = model.generate_content(
            "Say hello in 3 different languages."
        )

        if response and response.text:
            print("✅ Successfully generated text:")
            print("-" * 40)
            print(response.text)
            print("-" * 40)
            return True
        else:
            print("❌ Failed to generate text.")
            return False
    except Exception as e:
        print(f"❌ Error during text generation: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("GEMINI API TEST SCRIPT")
    print("=" * 50)

    # Test API availability
    if not test_gemini_availability():
        print("\nCannot proceed with further tests as Gemini API is not available.")
        return

    # Test simple text generation
    test_simple_generation()

    print("\nTests completed!")


if __name__ == "__main__":
    main()
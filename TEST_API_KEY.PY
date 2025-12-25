"""
Test if API key is being loaded correctly
"""

import os
from dotenv import load_dotenv

print("Testing API Key Loading...")
print("-" * 60)

# Load .env file
load_dotenv()

# Check if key exists
api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    print(f"✓ API key found!")
    print(f"  Key starts with: {api_key[:10]}...")
    print(f"  Key length: {len(api_key)} characters")
    
    if api_key.startswith("sk-"):
        print(f"✓ Key format looks correct (starts with 'sk-')")
    else:
        print(f"✗ WARNING: Key doesn't start with 'sk-'")
        print(f"  Your key starts with: {api_key[:5]}...")
else:
    print("✗ API key NOT found!")
    print("\nTroubleshooting steps:")
    print("1. Check if .env file exists:")
    print(f"   .env file exists: {os.path.exists('.env')}")
    print("\n2. Check .env file contents:")
    print("   Run: Get-Content .env")
    print("\n3. Make sure .env has this format:")
    print("   OPENAI_API_KEY=sk-your-key-here")
    print("   (No spaces around =)")

print("-" * 60)
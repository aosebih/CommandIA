"""
Manual check script for the CommandIA AI module.

It calls the real Gemini API, so it is NOT part of the automated suite.
The offline test suite lives in tests/ (pytest), and the golden dataset
runner is tests/test_golden_dataset.py.

Usage: python -m backend.test_ai
"""
import os
import sys

from ai.ai_service import AIService

# The replies are in Arabic/Franco-Arabic: the Windows console defaults to
# cp1252 and would crash on the first non-ASCII character.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Test messages in different dialects
TEST_CASES = [
    {
        "name": "French inquiry",
        "message": "Bonjour, quel est le prix de ce produit ?",
        "conversation": "french",
        "context": {"item_id": "shirt_001", "price": 2500, "total_price_da": 2500},
    },
    {
        "name": "Franco-Arabic order intent",
        "message": "Rani bghit nchri had produit",
        "conversation": "darija",
        "context": {"item_id": "shirt_001", "price": 2500, "total_price_da": 2500},
    },
    {
        "name": "Franco-Arabic name",
        "message": "Ismi Ahmed Benali",
        "conversation": "darija",
    },
    {
        "name": "Franco-Arabic phone",
        "message": "Numéro ta3i 0550123456",
        "conversation": "darija",
    },
    {
        "name": "Franco-Arabic wilaya",
        "message": "Ana men Alger",
        "conversation": "darija",
    },
    {
        "name": "Franco-Arabic delivery",
        "message": "Home delivery, domicile",
        "conversation": "darija",
    },
    {
        "name": "Franco-Arabic address",
        "message": "Rue Didouche Mourad, Commune Alger Centre",
        "conversation": "darija",
    },
]


def run_manual_tests():
    """Run basic AI tests against the real API."""
    print("Testing CommandIA AI Module...")
    print("=" * 60)
    
    try:
        # Check API key
        if not os.getenv("GEMINI_API_KEY"):
            print("⚠️  Warning: GEMINI_API_KEY not set in environment")
            print("   Set it with: set GEMINI_API_KEY=your_key (Windows) or export GEMINI_API_KEY=your_key")
            print("   Tests will fail without API key.")
            return
        
        service = AIService()
        # One conversation per dialect: the mirror rule locks the language on
        # the first message, so mixing dialects in a single conversation would
        # always answer in the language of the first one.
        conversations = {}

        # Run test cases
        for i, test in enumerate(TEST_CASES, 1):
            print(f"\n{i}. {test['name']}")
            print(f"   Input: {test['message']}")

            conv_id = conversations.get(test["conversation"])
            result = service.process_message(
                user_message=test["message"],
                conversation_id=conv_id,
                product_context=test.get("context"),
            )
            conversations[test["conversation"]] = result["conversation_id"]

            print(f"   Language: {result.get('language')}")
            print(f"   State: {result.get('state')}")
            print(f"   Missing: {result.get('missing_fields')}")
            print(f"   Collected: {len(result.get('collected_fields', {}))} fields")
            print(f"   Response: {result['response_text'][:80]}...")
            if result.get("error"):
                print(f"   ❌ Error: {result['error']}")
            if result.get("escalated"):
                print("   ⚠️  ESCALATED")
            print("-" * 40)
        
        print("\n✅ Test script completed")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_manual_tests()

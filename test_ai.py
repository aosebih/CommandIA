"""
Test script for CommandIA AI module.
Tests basic conversation flows with sample messages in different dialects.
"""
import os
from ai_service import AIService

# Test messages in different dialects
TEST_CASES = [
    {
        "name": "French inquiry",
        "message": "Bonjour, quel est le prix de ce produit ?",
        "context": {"item_id": "shirt_001", "price": 2500, "total_price_da": 2500},
    },
    {
        "name": "Franco-Arabic order intent",
        "message": "Rani bghit nchri had produit",
        "context": {"item_id": "shirt_001", "price": 2500, "total_price_da": 2500},
    },
    {
        "name": "Franco-Arabic name",
        "message": "Ismi Ahmed Benali",
    },
    {
        "name": "Franco-Arabic phone",
        "message": "Numéro ta3i 0550123456",
    },
    {
        "name": "Franco-Arabic wilaya",
        "message": "Ana men Alger",
    },
    {
        "name": "Franco-Arabic delivery",
        "message": "Home delivery, domicile",
    },
    {
        "name": "Franco-Arabic address",
        "message": "Rue Didouche Mourad, Commune Alger Centre",
    },
]


def test_ai():
    """Run basic AI tests."""
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
        conv_id = None
        
        # Run test cases
        for i, test in enumerate(TEST_CASES, 1):
            print(f"\n{i}. {test['name']}")
            print(f"   Input: {test['message']}")
            
            result = service.process_message(
                user_message=test["message"],
                conversation_id=conv_id,
                product_context=test.get("context"),
            )
            conv_id = result["conversation_id"]
            
            print(f"   Language: {result.get('language')}")
            print(f"   State: {result.get('state')}")
            print(f"   Missing: {result.get('missing_fields')}")
            print(f"   Collected: {len(result.get('collected_fields', {}))} fields")
            print(f"   Response: {result['response_text'][:80]}...")
            if result.get("escalated"):
                print("   ⚠️  ESCALATED")
            print("-" * 40)
        
        print("\n✅ Test script completed")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_ai()

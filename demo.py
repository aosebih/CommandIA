"""
CommandIA AI Demo - Interactive demo of the AI module.
"""
import os
from ai_service import AIService

def demo():
    """Interactive demo."""
    print("=" * 60)
    print("CommandIA AI Brain Demo (Gemini API + Pydantic)")
    print("=" * 60)
    print()
    
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Set it with: $env:GEMINI_API_KEY='your-api-key'")
        return
    
    service = AIService()
    conv_id = None
    product_context = {
        "item_id": "hoodie_001",
        "quantity": 1,
        "size_color": "L/Black",
        "price": 3500,
        "total_price_da": 3500,
    }
    
    print("Starting conversation. Type 'quit' to exit, 'reset' to reset.")
    print("Product context: Hoodie_001 (3500 DA)")
    print()
    
    while True:
        try:
            user_msg = input("You: ").strip()
            if user_msg.lower() in ['quit', 'exit', 'q']:
                break
            if user_msg.lower() == 'reset':
                if conv_id:
                    service.reset_conversation(conv_id)
                    print("Conversation reset.\n")
                continue
            if not user_msg:
                continue
            
            result = service.process_message(
                user_message=user_msg,
                conversation_id=conv_id,
                product_context=product_context,
            )
            conv_id = result["conversation_id"]
            
            print(f"AI: {result['response_text']}")
            print(f"[State: {result['state']}, Collected: {len(result['collected_fields'])}/5, Missing: {result['missing_fields']}]")
            if result.get('escalated'):
                print("[ESCALATED - Human handoff required]")
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    demo()

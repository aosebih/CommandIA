
import os
import sys

from ai.ai_service import AIService

# The replies are in Arabic/Franco-Arabic: the Windows console defaults to
# cp1252 and would crash on the first non-ASCII character.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def demo():
    
  
    print("CommandIA AI Brain Demo (Gemini API + Pydantic)")
   
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
            
            print(f"AI: {result.get('response_text', '')}")
            print(f"[State: {result['state']}, Collected: {len(result['collected_fields'])}/5, Missing: {result['missing_fields']}]")
            if result.get('escalated'):
                print("[ESCALATED - Human handoff required]")
            print()
            
        except KeyboardInterrupt:
            break
        except EOFError:
            # stdin is closed (no TTY, e.g. inside a container): leave the loop
            # instead of spinning on the same error forever.
            print()
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    demo()

# CommandIA AI Module

AI Brain for CommandIA using **Gemini API** with **Pydantic** schema validation. Implements the "5 Sacred Fields" extraction, conversational state machine, and multilingual support (Algerian Darija, Franco-Arabic, French, English) as specified in the PRD.

## Architecture

- **`ai_brain.py`** - Core AI logic with Gemini integration and state management
- **`ai_service.py`** - Service wrapper for easy integration
- **`schemas.py`** - Pydantic models for order extraction and validation
- **`system_prompt.py`** - V1 system prompt with all rules and guardrails
- **`wilayas.py`** - Canonical names and code validation for all 69 supported Wilayas
- **`config.py`** - Configuration management
- **`test_ai.py`** - Basic test suite
- **`demo.py`** - Interactive CLI demo

## Requirements

- Python 3.10+
- Gemini API key
- Dependencies in `requirements.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set environment variable for Gemini API key:

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

**Windows (CMD):**
```cmd
set GEMINI_API_KEY=your-api-key-here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Optional: Set model (defaults to `gemini-2.5-flash`)
```bash
export GEMINI_MODEL="gemini-2.5-flash"
```

## Usage

### Quick Test

```bash
python test_ai.py
```

### Interactive Demo

```bash
python demo.py
```

### Programmatic Usage

```python
from ai_service import AIService

service = AIService()
result = service.process_message(
    user_message="Rani bghit nchri had produit",
    product_context={
        "item_id": "hoodie_001",
        "price": 3500,
        "total_price_da": 3500,
    }
)

print(result["reply_to_customer"])
print(result["extracted_data"])
# response_text and order_data remain available as compatibility keys.
print(result["state"])  # INQUIRY, ORDER_INTENT, DATA_COLLECTION, CONFIRMATION, ESCALATION
```

## Features

### 5 Sacred Fields (PRD 3.2)
1. **customer_name** - Full name (min 1 first name)
2. **phone_number** - Algerian format (05/06/07 + 8 digits, 10 total)
3. **wilaya_code** - Must identify one of the 69 supported Algerian Wilayas
4. **delivery_type** - HOME or DESK
5. **address** - Commune/street details

### Language Support
- Algerian Darija (Arabic script)
- Franco-Arabic (Latin + numerals like 3andkom, bchhal)
- French
- English

**Mirror rule**: AI mirrors the user's initial message language.

### Guardrails (PRD 3.3)
- No unauthorized discounts (prices are fixed)
- Haggle defense ("Les prix sont fixes, mais la qualité est garantie!")
- Dynamic shipping calculation support
- Human handoff on escalation (>3 failed attempts, frustration, bulk pricing)

### State Machine (PRD 4.0)
- State 0: INQUIRY - Answer product questions
- State 1: ORDER_INTENT - User wants to buy
- State 2: DATA_COLLECTION - Collect 5 sacred fields
- State 3: CONFIRMATION - Summarize and confirm
- ESCALATION - Flag for human intervention

### Extraction response
The AI output is validated against the Pydantic response model:
```json
{
  "reply_to_customer": "Customer-facing message",
  "extracted_data": {
    "customer_name": "String or null",
    "phone_number": "10-digit Algerian number or null",
    "wilaya_code": "Integer from 1 to 69 or null",
    "delivery_type": "HOME, DESK, or null",
    "address": "String or null",
    "order_items": [
      {
        "product_name": "String",
        "quantity": "Positive integer",
        "size_color": "String or null",
        "unit_price_da": "Non-negative number or null"
      }
    ],
    "subtotal_da": "Non-negative number or null",
    "shipping_fee_da": "Non-negative number or null",
    "total_price_da": "Non-negative number or null",
    "order_status": "PENDING_CONFIRMATION, CONFIRMED, or REQUIRES_HUMAN"
  }
}
```

The server validates the phone number and wilaya code before updating conversation state. The legacy `response_text` and `order_data` result keys remain available for the current CLI and callers while integrations migrate to the canonical keys.

## Implementation Notes

- Uses **Gemini API** (`google-genai` SDK v1.41.0) - **no fine-tuning** as requested
- Pydantic v2 for validation of extracted fields
- Prompt engineering only approach
- Structured output with JSON responses
- Conversation state tracking across turns
- Phone number validation for Algerian format (regex)
- Wilaya validation against official list

## Testing Example

Sample Franco-Arabic conversation:
1. "Rani bghit nchri had produit" → Detects order intent
2. "Ismi Ahmed Benali" → Collects name
3. "0550123456" → Collects phone (validated)
4. "Alger" → Collects wilaya (validated)
5. "HOME" → Delivery type
6. "Rue Didouche, Alger Centre" → Address → Moves to CONFIRMATION

## Next Steps

This module is ready to integrate with:
- FastAPI webhook pipeline (Meta Graph API for Instagram DMs)
- Supabase for persisting orders
- Merchant dashboard (Next.js)

See `CommandIA_Roadmap.pdf` and `CommandIA_PRD (1).pdf` for full specs.

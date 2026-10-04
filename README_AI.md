# CommandIA AI Module

AI Brain for CommandIA using **Gemini API** with **Pydantic** schema validation. Implements the "5 Sacred Fields" extraction, conversational state machine, and multilingual support (Algerian Darija, Franco-Arabic, French, English) as specified in the PRD.

## Architecture

- **`ai_brain.py`** - Core AI logic with Gemini integration and state management
- **`ai_service.py`** - Service wrapper for easy integration
- **`schemas.py`** - Pydantic models for order extraction and validation
- **`system_prompt.py`** - V1 system prompt with all rules and guardrails
- **`wilayas.py`** - List of 58 Algerian Wilayas with validation
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

print(result["response_text"])
print(result["order_data"])
print(result["state"])  # INQUIRY, ORDER_INTENT, DATA_COLLECTION, CONFIRMATION, ESCALATION
```

## Features

### 5 Sacred Fields (PRD 3.2)
1. **customer_name** - Full name (min 1 first name)
2. **phone_number** - Algerian format (05/06/07 + 8 digits, 10 total)
3. **wilaya** - Must match 1 of 58 official Algerian Wilayas
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

### JSON Schema
Exact schema from roadmap enforced:
```json
{
  "order_id": "uuid-v4",
  "customer_name": "String",
  "phone_number": "String (10 Digits: 05/06/07...)",
  "wilaya": "String (1-58)",
  "delivery_type": "Enum ('HOME', 'DESK')",
  "address": "String (Commune / Location Details)",
  "product_details": {
    "item_id": "String",
    "quantity": "Integer",
    "size_color": "String"
  },
  "total_price_da": "Float",
  "order_status": "Enum ('PENDING_CONFIRMATION', 'CONFIRMED', 'REQUIRES_HUMAN')"
}
```

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

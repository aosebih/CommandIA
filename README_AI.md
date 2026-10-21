# CommandIA AI Module

AI Brain for CommandIA using **Gemini API** with **Pydantic** schema validation. Implements the "5 Sacred Fields" extraction, conversational state machine, and multilingual support (Algerian Darija, Franco-Arabic, French, English) as specified in the PRD.

## Architecture

- **`ai_brain.py`** - Core AI logic with Gemini integration and state management
- **`ai_service.py`** - Service wrapper for easy integration
- **`schemas.py`** - Pydantic models for order extraction and validation
- **`system_prompt.py`** - V1 system prompt with all rules and guardrails
- **`wilayas.py`** - Canonical names and code validation for all 69 supported Wilayas
- **`config.py`** - Configuration management
- **`app.py`** - FastAPI service (Meta webhook, `/healthz`, `/chat`)
- **`order_store.py`** - Supabase persistence for extracted orders
- **`tests/`** - Offline pytest suite + golden dataset runner
- **`test_ai.py`** - Manual check script against the real API
- **`demo.py`** - Interactive CLI demo

## Requirements

- Python 3.10+
- Gemini API key
- Dependencies in `requirements.txt` (`requirements-dev.txt` for the tests)

## Installation

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Configuration

Copy the template and fill in the values:

```bash
cp .env.example .env    # Windows PowerShell: Copy-Item .env.example .env
```

At minimum `GEMINI_API_KEY` is required. Every other variable is optional and
disables the related feature while it holds a placeholder value.

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

### Model selection

The default is `gemini-3.5-flash-lite` (~2s per reply) with
`gemini-3.5-flash` as fallback.

> `gemini-2.5-flash` returns **404** for newly created API keys
> ("model is not available to new users"), so it must not be used as the
> primary model.

```bash
export GEMINI_MODEL="gemini-3.5-flash-lite"
export GEMINI_MODEL_FALLBACKS="gemini-3.5-flash"
```

Transient provider errors (429, 5xx) are retried with an exponential backoff
(`MAX_RETRIES`, `RETRY_BASE_DELAY`) before the fallback model is tried.

## Usage

### Quick Test

```bash
pytest tests/ -q                # offline suite, no API call
python test_ai.py                # manual check against the real API
```

### Interactive Demo

```bash
python demo.py
```

### HTTP Service

```bash
uvicorn app:app --port 8000
```

| Route | Method | Description |
|-------|--------|-------------|
| `/healthz` | GET | Liveness probe, public |
| `/webhook` | GET | Meta verification challenge (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| `/webhook` | POST | Meta webhook, HMAC `X-Hub-Signature-256` verified, deduplicated on `message.mid` |
| `/chat` | POST | Development endpoint, requires the `X-API-Key` header (`COMMANDIA_API_KEY`) |

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{"message":"Rani bghit nchri had produit"}'
```

### Docker

```bash
docker build -t commandia .
docker run --rm -p 8000:8000 --env-file .env commandia
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

A malformed field never discards a whole order: `_sanitize_extraction` drops the
invalid value (invalid phone, out-of-range wilaya, unknown delivery type) and the
remaining fields are kept, so the bot simply asks for the missing field again.

## Implementation Notes

- Uses **Gemini API** (`google-genai` SDK v1.41.0) - **no fine-tuning** as requested
- Pydantic v2 for validation of extracted fields
- Prompt engineering only approach
- Structured output with JSON responses
- Conversation state tracking across turns
- Phone number validation for Algerian format (regex), shared with the state machine
  so a number is re-validated on every turn
- Wilaya validation against official list (69 wilayas)
- Model fallback chain with retry/backoff on transient provider errors

## Testing

### Offline suite (no API call)

```bash
pytest tests/ -q
```

The suite stubs the Gemini client, so it is deterministic and free. It covers
the language detection, the state machine, the extraction sanitizer and the
HTTP service.

### Golden dataset (real API)

```bash
# Windows PowerShell
$env:COMMANDIA_GOLDEN="1"; pytest tests/test_golden_dataset.py -q
```

`tests/golden_dataset.json` holds the reference multi-turn conversations in
French, Darija and English. It is the regression net for prompt changes and
model upgrades.

Sample Franco-Arabic conversation:
1. "Rani bghit nchri had produit" → Detects order intent
2. "Ismi Ahmed Benali" → Collects name
3. "0550123456" → Collects phone (validated)
4. "Alger" → Collects wilaya (validated)
5. "HOME" → Delivery type
6. "Rue Didouche, Alger Centre" → Address → Moves to CONFIRMATION

## Next Steps

- Merchant dashboard (Next.js)

See `prd.txt` and `roadmap.txt` for the full specifications.

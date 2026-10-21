# CommandIA - Résumé du Répertoire

## Vue d'ensemble

**CommandIA** est un moteur conversationnel IA destiné au e-commerce algérien. Il traite les messages reçus sur les réseaux sociaux (Instagram/Facebook DMs), répond aux questions produits, guide l'utilisateur vers l'achat, et extrait automatiquement des commandes structurées (JSON) prêtes à être expédiées (Cash on Delivery - COD).

Ce dépôt contient le **module "AI Brain"** : le cœur IA qui comprend les dialectes locaux et extrait les données de commande.

---

## Structure des fichiers

| Fichier | Rôle |
|---------|------|
| `ai_brain.py` | Logique IA centrale + machine à états conversationnelle |
| `ai_service.py` | Wrapper de service (gestion multi-conversations) |
| `schemas.py` | Modèles Pydantic (5 Champs Sacrés + commande complète) |
| `system_prompt.py` | Prompt système V1 (règles, guardrails, dialectes) |
| `wilayas.py` | Liste des 69 wilayas algériennes + validation |
| `config.py` | Chargement des variables d'environnement |
| `app.py` | Service FastAPI (webhook Meta, `/healthz`, `/chat`) |
| `order_store.py` | Persistance des commandes vers Supabase (REST) |
| `demo.py` | Démo interactive en ligne de commande |
| `tests/` | Suite de tests offline (pytest) + jeu de données golden |
| `Dockerfile` / `.dockerignore` | Image de production (python:3.12-slim) |
| `requirements.txt` / `requirements-dev.txt` | Dépendances runtime / développement |
| `.env.example` | Modèle de configuration |
| `README_AI.md` | Documentation du module IA |
| `prd.txt` | Product Requirements Document |
| `roadmap.txt` | Feuille de route 4 semaines + division des tâches |

---

## Stack technique

- **Python 3.10+**
- **Gemini API** (`google-genai` SDK v1.41.0) — modèle `gemini-3.5-flash-lite` par défaut,
  repli `gemini-3.5-flash` (`GEMINI_MODEL_FALLBACKS`), retries avec backoff exponentiel
- **Pydantic v2** — validation stricte des schémas JSON
- **FastAPI + Uvicorn** — webhooks Meta (Instagram/Facebook DMs)
- **httpx** — client HTTP
- **python-dotenv** — gestion du `.env`

> ⚠️ `gemini-2.5-flash` renvoie **404** pour les nouvelles clés API
> (« no longer available to new users »). Ne pas repasser en 2.5-flash.

> Approche : **prompt engineering uniquement**, aucun fine-tuning (conforme au PRD).


---

## Architecture logique

### 1. Machine à états conversationnelle (`ai_brain.py`)

Le parcours utilisateur est suivi via 5 états pour éviter les boucles infinies :

| État | Nom | Comportement |
|------|-----|--------------|
| 0 | `INQUIRY` | Répond aux questions produits (prix, taille, couleur) |
| 1 | `ORDER_INTENT` | L'utilisateur veut acheter → démarre la collecte |
| 2 | `DATA_COLLECTION` | Collecte les 5 Champs Sacrés un par un |
| 3 | `CONFIRMATION` | Récapitule et demande validation finale |
| — | `ESCALATION` | Transfert humain (frustration, tarif bulk, >3 échecs) |

### 2. Méthodes principales de `AIBrain`

- `process_message(user_message, conversation_state, product_context)` — Point d'entrée : appelle Gemini, parse la réponse, met à jour l'état, retourne réponse + données extraites.
- `_generate_content(prompt)` — Appel Gemini avec **repli de modèle** (chain `GEMINI_MODEL` → `GEMINI_MODEL_FALLBACKS`) et **retries/backoff** sur les erreurs transitoires (408/409/429/5xx).
- `_is_transient(error)` — Distingue une erreur transitoire (retry) d'une erreur de configuration (clé invalide, modèle inconnu).
- `_detect_language(message)` — Détection de langue : script arabe → Darija, marqueurs franco-arabes → Franco-arabe, puis Français/Anglais. Les chiffres seuls ne sont jamais un signal.
- `_sanitize_extraction(parsed)` — Rend l'extraction tolérante : un champ invalide (téléphone, wilaya, type de livraison) est mis à `null` au lieu de faire perdre toute la commande.
- `_update_missing_fields(extracted)` — Calcule les champs manquants et **revalide** téléphone + wilaya à chaque tour.
- `_signals_order_intent(message)` — Détecte une intention d'achat explicite (repli utilisé quand le modèle ne renvoie pas d'état).
- `_create_fallback_order(state)` — Construit une commande de secours en cas d'erreur API.
- `_build_history(state)` — Reconstruit l'historique (5 derniers échanges).
- `_parse_ai_response(raw)` — Extrait le JSON (blocs markdown ` ```json ` ou JSON brut).
- `_update_conversation_state(...)` — Met à jour champs collectés, statut, escalade et état (résolution : guardrails → monotone → heuristiques → état renvoyé par le modèle).
- `_build_fallback_result(state, error)` — Réponse dégradée en cas d'échec API (toujours avec la clé `language`).
- `_get_fallback_response(language, error)` — Message d'erreur traduit (FR/EN/Darija/Franco-arabe).
- `reset_conversation(...)` — Réinitialise une conversation.

### 3. Wrapper de service (`ai_service.py`)

- `AIService` maintient un dictionnaire `_conversations` (id → état).
- `process_message(...)` — Récupère/crée l'état, délègue à `AIBrain`, stocke le résultat.
- `get_conversation_state(...)`, `reset_conversation(...)`, `delete_conversation(...)`.

### 4. Validation Pydantic (`schemas.py`)

Enums : `DeliveryType` (HOME/DESK), `OrderStatus` (PENDING_CONFIRMATION/CONFIRMED/REQUIRES_HUMAN).
Modèles : `OrderItem`, `OrderExtractionData`, `OrderExtractionResponse`, `Order`.

---

## Les "5 Champs Sacrés" (PRD 3.2)

| # | Champ | Règle de validation |
|---|-------|---------------------|
| 1 | `customer_name` | Nom complet (au moins un prénom) |
| 2 | `phone_number` | Format algérien : 05/06/07 + 8 chiffres = 10 chiffres |
| 3 | `wilaya` | Doit correspondre à l'une des 69 wilayas officielles |
| 4 | `delivery_type` | `HOME` (domicile/ldar) ou `DESK` (stop-desk/bureau) |
| 5 | `address` | Commune/rue (HOME) ou commune/agence (DESK) |

---

## Schéma JSON de sortie (contrat de données)

```json
{
  "reply_to_customer": "String",
  "extracted_data": {
    "customer_name": "String or null",
    "phone_number": "String or null",
    "wilaya_code": "Integer (1-69) or null",
    "delivery_type": "HOME|DESK|null",
    "address": "String or null",
    "order_items": [
      { "product_name": "String", "quantity": "Integer", "size_color": "String or null", "unit_price_da": "Float or null" }
    ],
    "subtotal_da": "Float or null",
    "shipping_fee_da": "Float or null",
    "total_price_da": "Float or null",
    "order_status": "PENDING_CONFIRMATION|CONFIRMED|REQUIRES_HUMAN"
  }
}
```

**Règle de calcul des prix** : `subtotal_da = Σ(unit_price_da × quantity)`, `shipping_fee_da` appliqué **une seule fois** par commande selon wilaya + type de livraison, `total_price_da = subtotal_da + shipping_fee_da`.

---

## Guardrails métier (PRD 3.3)

- **Aucune remise non autorisée** : prix fixes.
- **Défense anti-négociation** : « Les prix sont fixes, mais la qualité est garantie ! ».
- **Calcul dynamique de livraison** selon wilaya et type (HOME vs DESK).
- **Transfert humain** : frustration, tarif en gros, ou échec après 3 tentatives.

---

## Support multilingue

4 langues/dialectes gérés : **Darija** (arabe), **Franco-arabe** (latin + chiffres), **Français**, **Anglais**.
**Règle du miroir** : l'IA répond toujours dans la langue du message initial de l'utilisateur.

---

## Utilisation

### Installation
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # tests
```

### Configuration
```powershell
Copy-Item .env.example .env   # puis renseigner GEMINI_API_KEY
```

### Lancement
```bash
pytest tests/ -q               # suite offline (aucun appel API)
uvicorn app:app --port 8000    # service FastAPI
python demo.py                  # démo interactive
docker build -t commandia .    # image de production
docker run --rm -p 8000:8000 --env-file .env commandia
```

### Tests golden (réseau)
```bash
# Reconstruction de la conversation "darija_full_booking" contre l'API réelle
$env:COMMANDIA_GOLDEN="1"; pytest tests/test_golden_dataset.py -q
```

### Usage programmatique
```python
from ai_service import AIService

service = AIService()
result = service.process_message(
    user_message="Rani bghit nchri had produit",
    product_context={"item_id": "hoodie_001", "price": 3500, "total_price_da": 3500},
)
print(result["response_text"], result["state"], result["order_data"])
```

---

## Points d'attention / dette technique

Les problèmes bloquants du premier jet ont été corrigés :

1. ~~`wilayas.py` — erreur de syntaxe~~ → corrigé (`WILAYA_CODE_TO_NAME` valide, une seule définition de chaque fonction).
2. ~~`wilayas_fixed.py` — encodage cassé~~ → fichier supprimé (dead code).
3. ~~`wilaya_code` vs `wilaya` — imports incohérents~~ → corrigé (`wilaya_code` partout, `get_wilaya_name` / `get_wilaya_code` / `is_valid_wilaya`).
4. ~~`.gitignore` incomplet~~ → `.env`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/` sont ignorés ; les `.pyc` déjà trackés ont été dé-trackés.

Dette restante (non bloquante) :

- `ai_service.py` garde les conversations en mémoire : le service est **stateless entre les
  redémarrages**. Passer à un store Redis/Supabase avant la mise en production.
- La détection d'intention d'achat repose en partie sur une liste de marqueurs ; le prompt
  demande aussi au modèle de renvoyer `conversation_state`, mais le modèle ne le fait pas
  toujours de façon fiable.
- `prd.txt` mentionne OpenAI/Anthropic et « 58 wilayas » : le code utilise Gemini et
  69 wilayas. Écart à documenter (le PRD n'est pas à jour).

---

## Prochaines étapes (intégration)

- ✅ Pipeline webhook **FastAPI** (`app.py`) : `GET /webhook` (challenge Meta),
  `POST /webhook` (signature HMAC vérifiée, déduplication par `mid`),
  `GET /healthz`, `POST /chat` (développement, protégé par `COMMANDIA_API_KEY`).
- ✅ Persistance **Supabase** (`order_store.py`) : écriture de la commande au format
  canonique `roadmap.txt` (160-174) via l'API REST.
- ✅ Conteneurisation **Docker** (`python:3.12-slim`, non-root, healthcheck).
- ⬜ Dashboard marchand **Next.js**.

Voir `prd.txt` et `roadmap.txt` pour les spécifications complètes.

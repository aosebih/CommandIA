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
| `wilayas.py` | Liste des 58 wilayas algériennes + validation |
| `wilayas_fixed.py` | Version corrigée (attention : encodage mojibake) |
| `config.py` | Chargement des variables d'environnement |
| `demo.py` | Démo interactive en ligne de commande |
| `test_ai.py` | Suite de tests de base |
| `requirements.txt` | Dépendances Python |
| `.env.example` | Modèle de configuration |
| `README_AI.md` | Documentation du module IA |
| `prd.txt` | Product Requirements Document |
| `roadmap.txt` | Feuille de route 4 semaines + division des tâches |

---

## Stack technique

- **Python 3.10+**
- **Gemini API** (`google-genai` SDK v1.41.0) — modèle `gemini-2.5-flash` par défaut
- **Pydantic v2** — validation stricte des schémas JSON
- **FastAPI + Uvicorn** — prévu pour les webhooks Meta
- **httpx** — client HTTP
- **python-dotenv** — gestion du `.env`

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
- `_detect_language(message)` — Détection de langue par heuristique : comptage des caractères arabes (Darija), motifs franco-arabes (`3`, `7`, `bch`, `kifach`, `rani`…), mots-clés français, sinon anglais.
- `_update_missing_fields(extracted)` — Calcule les champs manquants et valide téléphone + wilaya.
- `_create_fallback_order(state)` — Construit une commande de secours en cas d'erreur API.
- `_build_history(state)` — Reconstruit l'historique (5 derniers échanges).
- `_parse_ai_response(raw)` — Extrait le JSON (blocs markdown ` ```json ` ou JSON brut).
- `_update_conversation_state(...)` — Met à jour champs collectés, statut, escalade et état.
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
| 3 | `wilaya` | Doit correspondre à l'une des 58 wilayas officielles |
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
    "wilaya_code": "Integer (1-58) or null",
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
```

### Configuration
```powershell
$env:GEMINI_API_KEY="votre-cle-api"
```

### Lancement
```bash
python test_ai.py   # tests de base
python demo.py      # démo interactive
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

1. **`wilayas.py` — erreur de syntaxe** : `WILAYA_CODE_TO_NAME` contient des valeurs non-échappées (ex. `1: Adrar`) → ces lignes sont **invalides en Python**. De plus, le dictionnaire et les fonctions `get_wilaya_name` / `get_wilaya_code` sont **définis deux fois** (lignes 104-125 puis 128-149).
2. **`wilayas_fixed.py` — encodage cassé** : caractères accentués mal encodés (mojibake `BÃ©jaÃ¯a` au lieu de `Béjaïa`).
3. **`wilaya_code` vs `wilaya`** : `ai_brain.py` importe `is_valid_wilaya`, `get_wilaya_code`, `get_wilaya_name`, `ALGERIAN_WILAYAS_LIST` — vérifier que les imports ne cassent pas à cause des erreurs du point 1.
4. **`.gitignore`** n'ignore que `.env.example` (devrait aussi ignorer `.env` et `__pycache__/`).

---

## Prochaines étapes (intégration)

- Pipeline webhook **FastAPI** (Meta Graph API pour DMs Instagram).
- Persistance **Supabase** (tables Orders, Merchants, Products, Conversations).
- Dashboard marchand **Next.js**.

Voir `prd.txt` et `roadmap.txt` pour les spécifications complètes.

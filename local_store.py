"""Thread-safe JSON persistence for the local CommandIA workspace.

The store keeps the exact shapes the React frontend already uses. State is
written atomically to ``data/state.json`` and seeded from ``data/seed.json``
on first use, so the demo works without Supabase or any external database.
"""
import copy
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from auth import hash_password

ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_FILE = ROOT / "data" / "state.json"
DEFAULT_SEED_FILE = ROOT / "data" / "seed.json"

DEFAULT_RULES: Dict[str, Any] = {
    "zones": {"Alger": 600, "Oran": 800, "Constantine": 800, "Other Wilayas": 900},
    "opens": "09:00",
    "closes": "18:00",
    "behavior": "Flag for human intervention",
    "instructions": "Escalate address changes. Never confirm without review.",
    "tone": "Warm and concise",
    "languages": "French / Algerian Arabic",
    "maxDiscount": 0,
    "freeAbove": 12000,
}

DEFAULT_SETTINGS: Dict[str, bool] = {"ai": True, "ig": False}

DEMO_USER = {
    "name": "Demo User",
    "email": "demo@commandia.dz",
    "password": "demo1234",
}

FALLBACK_SEED: Dict[str, Any] = {
    "convs": [],
    "orders": [],
    "products": [],
}


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


class LocalStore:
    def __init__(
        self,
        path: Optional[Path | str] = None,
        seed_path: Optional[Path | str] = None,
    ):
        self.path = Path(path or os.getenv("COMMANDIA_DATA_FILE", DEFAULT_STATE_FILE))
        self.seed_path = Path(seed_path or DEFAULT_SEED_FILE)
        self._lock = threading.RLock()
        self._state = self._load()

    # --- persistence ---------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return self._normalize(_read_json(self.path))
            except (OSError, ValueError, json.JSONDecodeError):
                # A damaged state file must not take the whole demo down.
                pass
        try:
            seed = _read_json(self.seed_path)
        except (OSError, ValueError, json.JSONDecodeError):
            seed = copy.deepcopy(FALLBACK_SEED)
        return self._normalize(seed)

    def _normalize(self, state: Dict[str, Any]) -> Dict[str, Any]:
        normalized = copy.deepcopy(state)
        if "conversations" not in normalized:
            normalized["conversations"] = normalized.pop("convs", [])
        normalized.setdefault("orders", [])
        normalized.setdefault("products", [])
        normalized.setdefault("rules", copy.deepcopy(DEFAULT_RULES))
        settings = normalized.get("settings")
        normalized["settings"] = {
            **copy.deepcopy(DEFAULT_SETTINGS),
            **(settings if isinstance(settings, dict) else {}),
        }

        users = normalized.get("users")
        if not isinstance(users, list):
            users = []
        if not any(user.get("email", "").casefold() == DEMO_USER["email"] for user in users):
            users.append({
                "name": DEMO_USER["name"],
                "email": DEMO_USER["email"],
                "password_hash": hash_password(DEMO_USER["password"]),
            })
        normalized["users"] = users

        max_order = max((int(order.get("id", 0)) for order in normalized["orders"]), default=1042)
        max_product = max((int(product.get("id", 0)) for product in normalized["products"]), default=0)
        normalized["next_order_id"] = max(int(normalized.get("next_order_id", 0)), max_order + 1)
        normalized["next_product_id"] = max(int(normalized.get("next_product_id", 0)), max_product + 1)
        return normalized

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self._state, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    # --- users ---------------------------------------------------------------

    @staticmethod
    def public_user(user: Dict[str, Any]) -> Dict[str, str]:
        return {"name": user["name"], "email": user["email"]}

    def find_user(self, email: str) -> Optional[Dict[str, Any]]:
        needle = (email or "").strip().casefold()
        with self._lock:
            for user in self._state["users"]:
                if user.get("email", "").casefold() == needle:
                    return copy.deepcopy(user)
        return None

    def create_user(self, name: str, email: str, password: str) -> Dict[str, str]:
        clean_email = email.strip().lower()
        with self._lock:
            if self.find_user(clean_email):
                raise ValueError("An account with this email already exists")
            user = {
                "name": name.strip(),
                "email": clean_email,
                "password_hash": hash_password(password),
            }
            self._state["users"].append(user)
            self._save()
            return self.public_user(user)

    # --- conversations -------------------------------------------------------

    def conversations(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._state["conversations"])

    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            conversation = self._conversation(conversation_id)
            return copy.deepcopy(conversation) if conversation else None

    def _conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        for conversation in self._state["conversations"]:
            if int(conversation.get("id", -1)) == int(conversation_id):
                return conversation
        return None

    def update_conversation(self, conversation_id: int, **changes: Any) -> Dict[str, Any]:
        with self._lock:
            conversation = self._conversation(conversation_id)
            if conversation is None:
                raise KeyError(conversation_id)
            conversation.update(changes)
            self._save()
            return copy.deepcopy(conversation)

    def update_mode(self, conversation_id: int, mode: str) -> str:
        self.update_conversation(conversation_id, m=mode)
        return mode

    def append_message(self, conversation_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            conversation = self._conversation(conversation_id)
            if conversation is None:
                raise KeyError(conversation_id)
            conversation.setdefault("msgs", []).append(copy.deepcopy(message))
            conversation["ts"] = message.get("time", "Now")
            conversation["un"] = 0
            self._save()
            return copy.deepcopy(message)

    # --- orders --------------------------------------------------------------

    def orders(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._state["orders"])

    def find_order_for_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            for order in self._state["orders"]:
                if int(order.get("conversationId", -1)) == int(conversation_id):
                    return copy.deepcopy(order)
        return None

    def create_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            created = copy.deepcopy(order)
            if not created.get("id"):
                created["id"] = int(self._state["next_order_id"])
                self._state["next_order_id"] += 1
            else:
                self._state["next_order_id"] = max(
                    int(self._state["next_order_id"]), int(created["id"]) + 1
                )
            self._state["orders"].append(created)
            self._save()
            return copy.deepcopy(created)

    def set_order_status(self, order_id: int, status: str) -> str:
        with self._lock:
            for order in self._state["orders"]:
                if int(order.get("id", -1)) == int(order_id):
                    order["st"] = status
                    self._save()
                    return status
        raise KeyError(order_id)

    # --- products ------------------------------------------------------------

    def products(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._state["products"])

    def save_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            product_id = product.get("id")
            if product_id:
                for existing in self._state["products"]:
                    if int(existing.get("id", -1)) == int(product_id):
                        existing.update({
                            "n": product["n"],
                            "p": product["p"],
                            "s": product["s"],
                        })
                        self._save()
                        return copy.deepcopy(existing)
            created = {
                "id": int(product_id or self._state["next_product_id"]),
                "n": product["n"],
                "p": product["p"],
                "s": product["s"],
            }
            self._state["next_product_id"] = max(
                int(self._state["next_product_id"]), created["id"] + 1
            )
            self._state["products"].append(created)
            self._save()
            return copy.deepcopy(created)

    # --- settings and rules --------------------------------------------------

    def settings(self) -> Dict[str, bool]:
        with self._lock:
            return copy.deepcopy(self._state["settings"])

    def set_ai(self, enabled: bool) -> Dict[str, bool]:
        with self._lock:
            self._state["settings"]["ai"] = bool(enabled)
            self._save()
            return copy.deepcopy(self._state["settings"])

    def set_instagram(self, connected: bool) -> Dict[str, bool]:
        with self._lock:
            self._state["settings"]["ig"] = bool(connected)
            self._save()
            return copy.deepcopy(self._state["settings"])

    def rules(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state["rules"])

    def save_rules(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._state["rules"] = copy.deepcopy(rules)
            self._save()
            return copy.deepcopy(self._state["rules"])

"""Deterministic offline replies used when Gemini is not configured.

The real AI engine remains the primary path. This module only keeps the demo
usable out of the box, for example on a fresh checkout with no API key.
"""
import re
from typing import Any, Dict, List, Optional

ORDER_MARKERS = (
    "commande", "commander", "acheter", "achete", "nchri", "bghit",
    "order", "buy", "purchase", "3tini", "3tina",
)
HUMAN_MARKERS = (
    "humain", "personne", "agent", "human", "person", "real person",
    "nass", "3ayet", "responsable",
)
SHIPPING_MARKERS = (
    "livraison", "livrer", "delivery", "shipping", "wilaya", "domicile",
    "stop desk", "stop-desk", "bureau",
)
GREETING_MARKERS = ("salam", "bonjour", "salut", "hello", "hi", "ahlan", "labas")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _detect_language(text: str) -> str:
    if re.search(r"[\u0600-\u06ff]", text):
        return "darija"
    if _has_any(text, ("bonjour", "salut", "merci", "livraison", "commande", "prix", "disponible")):
        return "french"
    if _has_any(text, ("hello", "please", "price", "delivery", "order", "available", "thank")):
        return "english"
    return "franco_arabic"


def _find_product(text: str, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_length = 0
    for product in products:
        name = _normalize(str(product.get("n", "")))
        if name and name in text and len(name) > best_length:
            best = product
            best_length = len(name)
    return best


def _product_reply(product: Dict[str, Any], language: str) -> str:
    name = product.get("n", "ce produit")
    price = int(float(product.get("p", 0)))
    stock = int(float(product.get("s", 0)))
    if language == "english":
        if stock:
            return f"Yes, {name} is available at {price:,} DA with {stock} in stock. Would you like to order?"
        return f"{name} is currently out of stock. I can flag your request so the team restocks it."
    if language == "french":
        if stock:
            return f"Oui, {name} est disponible à {price:,} DA ({stock} en stock). Souhaitez-vous commander ?"
        return f"{name} est actuellement en rupture de stock. Je peux signaler votre demande à l'équipe."
    if stock:
        return f"Oui, {name} kayen b {price:,} DA ({stock} f stock). Bghit tcommandi ?"
    return f"{name} ma kayench daba f stock. N3ayet l'équipe bach yraj3ouh."


def _order_reply(language: str) -> str:
    if language == "english":
        return "With pleasure. To prepare the order, send me your full name, phone number, wilaya and delivery address."
    if language == "french":
        return "Avec plaisir. Pour préparer la commande, envoyez-moi votre nom complet, téléphone, wilaya et adresse de livraison."
    return "Bsahtek. Bach nwejjed commande, 3tini smitek kamel, téléphone, wilaya w adresse ta3 livraison."


def _human_reply(language: str) -> str:
    if language == "english":
        return "Of course. I am flagging this conversation for a team member who can help you directly."
    if language == "french":
        return "Bien sûr. Je transmets cette conversation à un membre de l'équipe qui pourra vous aider directement."
    return "Bien sûr. Rani n3ayet l wa7ed men l'équipe bach y3awnek direct."


def _shipping_reply(language: str, rules: Dict[str, Any]) -> str:
    zones = rules.get("zones") or {}
    prices = ", ".join(f"{zone}: {int(float(fee)):,} DA" for zone, fee in zones.items())
    if language == "english":
        return f"We deliver across Algeria. Delivery fees: {prices}. Tell me your wilaya and I will confirm the total."
    if language == "french":
        return f"Nous livrons partout en Algérie. Frais de livraison : {prices}. Indiquez-moi votre wilaya et je confirme le total."
    return f"Nous livrons partout en Algérie. Frais: {prices}. 3tini wilaya w nconfirmi total."


def fallback_result(
    text: str,
    conversation: Dict[str, Any],
    products: List[Dict[str, Any]],
    rules: Dict[str, Any],
) -> Dict[str, Any]:
    normalized = _normalize(text)
    language = _detect_language(normalized)
    product = _find_product(normalized, products)

    if product:
        reply = _product_reply(product, language)
        state = "INQUIRY"
        intent = "Product inquiry"
    elif _has_any(normalized, ORDER_MARKERS):
        reply = _order_reply(language)
        state = "ORDER_INTENT"
        intent = "Ready to order"
    elif _has_any(normalized, HUMAN_MARKERS):
        reply = _human_reply(language)
        state = "ESCALATION"
        intent = "Wants a human"
    elif _has_any(normalized, SHIPPING_MARKERS):
        reply = _shipping_reply(language, rules)
        state = "INQUIRY"
        intent = "Delivery question"
    elif _has_any(normalized, GREETING_MARKERS):
        reply = {
            "english": "Hello! How can I help you today?",
            "french": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
            "darija": "Salam ! Kifach n9der n3awnek ?",
        }.get(language, "Salam ! Kifach n9der n3awnek ?")
        state = "INQUIRY"
        intent = conversation.get("intent") or "New conversation"
    else:
        reply = {
            "english": "Thanks for your message. I can help with product availability, delivery fees or placing an order.",
            "french": "Merci pour votre message. Je peux vous aider avec la disponibilité, les frais de livraison ou une commande.",
            "darija": "Merci 3la message. N9der n3awnek b les produits, livraison wla commande.",
        }.get(language, "Merci 3la message. N9der n3awnek b les produits, livraison wla commande.")
        state = "INQUIRY"
        intent = conversation.get("intent") or "General inquiry"

    return {
        "reply_to_customer": reply,
        "response_text": reply,
        "state": state,
        "language": language,
        "missing_fields": [],
        "collected_fields": {},
        "extracted_data": {"order_status": "PENDING_CONFIRMATION"},
        "order_data": {},
        "conversation_id": str(conversation.get("id", "")),
        "error": None,
        "fallback": True,
        "intent": intent,
    }

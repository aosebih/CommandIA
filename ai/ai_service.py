from typing import Any, Dict, Optional

from ai.ai_brain import AIBrain, ConversationState


class AIService:

    def __init__(self, api_key: Optional[str] = None, conversation_store=None):
        self.brain = AIBrain(api_key=api_key)
        self._conversations: Dict[str, ConversationState] = {}
        self.conversation_store = conversation_store

    def _store(self):
        return getattr(self, "conversation_store", None)

    def process_message(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        product_context: Optional[Dict[str, Any]] = None,
        merchant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = None
        if conversation_id and conversation_id in self._conversations:
            state = self._conversations[conversation_id]
        elif conversation_id and self._store():
            state = self._store().load(
                conversation_id, merchant_id=merchant_id
            )
        if state is None:
            state = ConversationState(conversation_id=conversation_id)
        if merchant_id:
            state.merchant_id = merchant_id

        result = self.brain.process_message(
            user_message=user_message,
            conversation_state=state,
            product_context=product_context,
        )

        conv_id = result["conversation_id"]
        self._conversations[conv_id] = state
        if self._store():
            db_id = self._store().save(
                state,
                customer_ig_id=conv_id,
                merchant_id=state.merchant_id,
                user_message=user_message,
                bot_message=result.get("reply_to_customer"),
            )
            if db_id:
                state.db_conversation_id = db_id
                result["db_conversation_id"] = db_id

        result["open_order_id"] = state.open_order_id
        result["merchant_id"] = state.merchant_id
        return result

    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        if conversation_id not in self._conversations:
            return None
        state = self._conversations[conversation_id]
        return {
            "conversation_id": state.conversation_id,
            "state": state.state,
            "collected_fields": state.collected_fields,
            "missing_fields": state.missing_fields,
            "escalated": state.escalated,
            "attempts": state.attempts,
            "language": state.language,
        }

    def reset_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = ConversationState(
                conversation_id=conversation_id
            )
            return True
        return False

    def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

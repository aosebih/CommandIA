"""
AI Service wrapper for CommandIA.
Provides clean interface for processing messages with Gemini API.
"""
from typing import Optional, Dict, Any
from ai_brain import AIBrain, ConversationState


class AIService:
    """
    Service layer for AI operations.
    Uses Gemini API (no fine-tuning) as specified in requirements.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.brain = AIBrain(api_key=api_key)
        # Store active conversations
        self._conversations: Dict[str, ConversationState] = {}
    
    def process_message(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        product_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message.
        
        Args:
            user_message: The user's message
            conversation_id: Optional conversation ID to continue existing conversation
            product_context: Optional product context (item_id, price, etc.)
        
        Returns:
            Response with message and extracted order data
        """
        # Get or create conversation state
        if conversation_id and conversation_id in self._conversations:
            state = self._conversations[conversation_id]
        else:
            state = ConversationState(conversation_id=conversation_id)
        
        # Process message
        result = self.brain.process_message(
            user_message=user_message,
            conversation_state=state,
            product_context=product_context,
        )
        
        # Store updated state
        conv_id = result["conversation_id"]
        self._conversations[conv_id] = state
        
        return result
    
    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation state by ID."""
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
        """Reset a conversation."""
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = ConversationState(conversation_id=conversation_id)
            return True
        return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

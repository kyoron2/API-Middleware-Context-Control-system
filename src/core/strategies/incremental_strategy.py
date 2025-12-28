"""Incremental summarization strategy implementation"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime

from ...models.openai import Message
from ...models.adaptive_summarization import IncrementalConfig


@dataclass
class SummaryState:
    """State for incremental summarization"""
    summary_text: str
    depth: int
    created_at: datetime
    message_count: int


class IncrementalStrategy:
    """
    Incremental summarization strategy
    
    Maintains a rolling summary that accumulates over time.
    Keeps recent N messages complete and summarizes older ones.
    Resets when maximum depth is reached.
    """
    
    def __init__(self, config: IncrementalConfig):
        """
        Initialize incremental strategy
        
        Args:
            config: Incremental configuration
        """
        self.config = config
        
        # Session-specific summary states
        self._summary_states: Dict[str, SummaryState] = {}
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        return len(text) // 4
    
    def _get_summary_state(self, session_id: str) -> Optional[SummaryState]:
        """
        Get summary state for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary state or None if not found
        """
        return self._summary_states.get(session_id)
    
    def _save_summary_state(
        self,
        session_id: str,
        summary_text: str,
        depth: int,
        message_count: int
    ) -> None:
        """
        Save summary state for a session
        
        Args:
            session_id: Session identifier
            summary_text: Summary text
            depth: Current summary depth
            message_count: Number of messages summarized
        """
        self._summary_states[session_id] = SummaryState(
            summary_text=summary_text,
            depth=depth,
            created_at=datetime.utcnow(),
            message_count=message_count
        )
    
    def _reset_summary_state(self, session_id: str) -> None:
        """
        Reset summary state for a session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._summary_states:
            del self._summary_states[session_id]
    
    def _should_trigger_summarization(
        self,
        messages: List[Message],
        session_id: str
    ) -> bool:
        """
        Check if summarization should be triggered
        
        Args:
            messages: Current messages
            session_id: Session identifier
            
        Returns:
            True if summarization should be triggered
        """
        # Get previous state
        state = self._get_summary_state(session_id)
        
        if state is None:
            # First time - trigger if we have enough messages
            return len(messages) > self.config.summary_window + self.config.keep_recent
        
        # Trigger if we've accumulated enough new messages since last summary
        new_message_count = len(messages) - state.message_count
        return new_message_count >= self.config.summary_window
    
    def _should_reset_depth(self, session_id: str) -> bool:
        """
        Check if summary depth should be reset
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if depth should be reset
        """
        state = self._get_summary_state(session_id)
        if state is None:
            return False
        
        return state.depth >= self.config.max_summary_depth
    
    def _create_summary_prompt(
        self,
        messages: List[Message],
        previous_summary: Optional[str] = None
    ) -> str:
        """
        Create prompt for summary generation
        
        Args:
            messages: Messages to summarize
            previous_summary: Previous summary text (if exists)
            
        Returns:
            Prompt text for LLM
        """
        # Build conversation text
        conversation_parts = []
        for msg in messages:
            conversation_parts.append(f"{msg.role}: {msg.content}")
        
        conversation_text = "\n".join(conversation_parts)
        
        if previous_summary:
            prompt = f"""You are summarizing a conversation incrementally.

Previous Summary:
{previous_summary}

New Messages:
{conversation_text}

Please create an updated summary that:
1. Incorporates key information from the new messages
2. Maintains important context from the previous summary
3. Removes redundant or less important details
4. Keeps the summary concise (max 500 words)

Updated Summary:"""
        else:
            prompt = f"""You are summarizing a conversation.

Messages:
{conversation_text}

Please create a concise summary that:
1. Captures the main topics and key points
2. Preserves important entities, decisions, and actions
3. Maintains chronological flow
4. Keeps the summary concise (max 500 words)

Summary:"""
        
        return prompt
    
    async def _generate_summary(
        self,
        messages: List[Message],
        previous_summary: Optional[str],
        provider_manager=None
    ) -> str:
        """
        Generate summary using LLM
        
        Args:
            messages: Messages to summarize
            previous_summary: Previous summary (if exists)
            provider_manager: Provider manager for API calls
            
        Returns:
            Generated summary text
            
        Note:
            This is a placeholder. Full implementation requires provider_manager
            to make actual API calls.
        """
        # Create prompt
        prompt = self._create_summary_prompt(messages, previous_summary)
        
        # TODO: Call LLM via provider_manager
        # For now, create a simple summary
        if previous_summary:
            summary = f"{previous_summary}\n\n[New: {len(messages)} messages added]"
        else:
            summary = f"[Summary of {len(messages)} messages]"
        
        return summary
    
    async def apply(
        self,
        messages: List[Message],
        session_id: str,
        provider_manager=None
    ) -> List[Message]:
        """
        Apply incremental summarization strategy
        
        Args:
            messages: Messages to process
            session_id: Session identifier
            provider_manager: Provider manager for LLM calls
            
        Returns:
            Processed messages with incremental summarization applied
        """
        if not messages:
            return []
        
        # Check if we need to reset depth
        if self._should_reset_depth(session_id):
            self._reset_summary_state(session_id)
        
        # Check if summarization should be triggered
        if not self._should_trigger_summarization(messages, session_id):
            # Not enough messages yet, return as-is
            return messages
        
        # Separate system messages
        system_messages = [msg for msg in messages if msg.role == "system"]
        other_messages = [msg for msg in messages if msg.role != "system"]
        
        # Keep recent messages
        recent_messages = other_messages[-self.config.keep_recent:]
        messages_to_summarize = other_messages[:-self.config.keep_recent]
        
        if not messages_to_summarize:
            # Nothing to summarize
            return messages
        
        # Get previous summary state
        previous_state = self._get_summary_state(session_id)
        previous_summary = previous_state.summary_text if previous_state else None
        previous_depth = previous_state.depth if previous_state else 0
        
        # Generate new summary
        new_summary = await self._generate_summary(
            messages_to_summarize,
            previous_summary,
            provider_manager
        )
        
        # Save new state
        new_depth = previous_depth + 1
        self._save_summary_state(
            session_id,
            new_summary,
            new_depth,
            len(messages)
        )
        
        # Create summary message
        summary_message = Message(
            role="system",
            content=f"{self.config.summary_prefix} (Depth {new_depth}): {new_summary}"
        )
        
        # Combine: system messages + summary + recent messages
        result = system_messages + [summary_message] + recent_messages
        
        return result
    
    def get_summary_info(self, session_id: str) -> Optional[Dict]:
        """
        Get summary information for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with summary info or None
        """
        state = self._get_summary_state(session_id)
        if state is None:
            return None
        
        return {
            "depth": state.depth,
            "message_count": state.message_count,
            "created_at": state.created_at.isoformat(),
            "summary_length": len(state.summary_text)
        }
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear summary state for a session
        
        Args:
            session_id: Session identifier
        """
        self._reset_summary_state(session_id)

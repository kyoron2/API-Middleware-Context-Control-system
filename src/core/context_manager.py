"""Context management with reduction strategies"""

from typing import List, Tuple, Optional
from abc import ABC, abstractmethod

from ..models.openai import Message
from ..models.session import ContextConfig
from ..models.adaptive_summarization import AdaptiveSummarizationConfig


class ContextStrategy(ABC):
    """Abstract base class for context reduction strategies"""

    @abstractmethod
    async def reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Reduce context according to strategy
        
        Args:
            messages: List of messages to reduce
            config: Context configuration
            
        Returns:
            Tuple of (reduced messages, optional summary)
        """
        pass


class TruncationStrategy(ContextStrategy):
    """Truncation strategy - remove oldest messages"""

    async def reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Reduce context by removing oldest messages
        
        Preserves system messages if configured
        Keeps the most recent N messages
        """
        if len(messages) <= config.max_turns:
            return messages, None
        
        # Separate system messages from others
        system_messages = []
        other_messages = []
        
        for msg in messages:
            if msg.role == "system" and config.preserve_system_message:
                system_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # Calculate how many non-system messages to keep
        max_other = config.max_turns - len(system_messages)
        if max_other < 0:
            max_other = 0
        
        # Keep most recent messages
        kept_messages = other_messages[-max_other:] if max_other > 0 else []
        
        # Combine system messages with kept messages
        result = system_messages + kept_messages
        
        return result, None


class SlidingWindowStrategy(ContextStrategy):
    """Sliding window strategy - keep recent messages within token budget"""

    def estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages"""
        total = 0
        for msg in messages:
            # Rough estimation: 1 token ≈ 4 characters
            total += len(msg.content) // 4
            # Add overhead for role and structure
            total += 4
        return total

    async def reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Reduce context using sliding window based on token budget
        
        Keeps most recent messages that fit within token budget
        """
        # Separate system messages
        system_messages = []
        other_messages = []
        
        for msg in messages:
            if msg.role == "system" and config.preserve_system_message:
                system_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # Calculate tokens used by system messages
        system_tokens = self.estimate_tokens(system_messages)
        remaining_budget = config.max_tokens - system_tokens
        
        if remaining_budget <= 0:
            return system_messages, None
        
        # Add messages from most recent, staying within budget
        kept_messages = []
        current_tokens = 0
        
        for msg in reversed(other_messages):
            msg_tokens = self.estimate_tokens([msg])
            if current_tokens + msg_tokens <= remaining_budget:
                kept_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        result = system_messages + kept_messages
        return result, None


class SummarizationStrategy(ContextStrategy):
    """Summarization strategy - summarize old messages and keep recent ones"""

    def __init__(self, context_manager=None):
        """
        Initialize summarization strategy
        
        Args:
            context_manager: Reference to ContextManager for summarization
        """
        self.context_manager = context_manager

    def estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages"""
        total = 0
        for msg in messages:
            total += len(msg.content) // 4 + 4
        return total

    async def reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Reduce context by summarizing older messages
        
        Keeps recent messages and creates summary of older ones
        """
        if len(messages) <= config.max_turns:
            return messages, None
        
        # Separate system messages
        system_messages = []
        other_messages = []
        
        for msg in messages:
            if msg.role == "system" and config.preserve_system_message:
                system_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # Keep recent messages, summarize the rest
        keep_count = config.max_turns - len(system_messages)
        if keep_count < 2:
            keep_count = 2  # Keep at least 2 recent messages
        
        messages_to_summarize = other_messages[:-keep_count] if keep_count > 0 else other_messages
        messages_to_keep = other_messages[-keep_count:] if keep_count > 0 else []
        
        # Generate summary
        summary = None
        if messages_to_summarize and self.context_manager:
            summary_text = await self.context_manager.summarize_messages(
                messages_to_summarize,
                config.summarization_model or "gpt-3.5-turbo",
                None  # provider_manager will be passed in full implementation
            )
            summary = summary_text
            
            # Create summary message
            summary_message = Message(
                role="system",
                content=f"[Previous conversation summary]: {summary_text}"
            )
            result = system_messages + [summary_message] + messages_to_keep
        else:
            result = system_messages + messages_to_keep
        
        return result, summary


class AdaptiveSummarizationStrategy(ContextStrategy):
    """Adaptive summarization strategy - intelligent content-aware summarization"""

    def __init__(
        self,
        adaptive_config: AdaptiveSummarizationConfig,
        session_id: str,
        provider_manager=None
    ):
        """
        Initialize adaptive summarization strategy
        
        Args:
            adaptive_config: Adaptive summarization configuration
            session_id: Session identifier
            provider_manager: Provider manager for LLM API calls
        """
        from .adaptive_summarization_manager import AdaptiveSummarizationManager
        
        self.session_id = session_id
        self.manager = AdaptiveSummarizationManager(
            adaptive_config,
            provider_manager
        )

    async def reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Reduce context using adaptive summarization
        
        Args:
            messages: List of messages to reduce
            config: Context configuration
            
        Returns:
            Tuple of (reduced messages, optional summary)
        """
        # Execute adaptive summarization
        result = await self.manager.summarize(
            messages,
            self.session_id
        )
        
        # Extract summary text from preserved content
        summary_parts = []
        if result.preserved_content.get("entities"):
            entity_count = len(result.preserved_content["entities"])
            summary_parts.append(f"{entity_count} entities preserved")
        
        if result.preserved_content.get("code_blocks"):
            code_count = len(result.preserved_content["code_blocks"])
            summary_parts.append(f"{code_count} code blocks preserved")
        
        if result.preserved_content.get("urls"):
            url_count = len(result.preserved_content["urls"])
            summary_parts.append(f"{url_count} URLs preserved")
        
        summary_text = ", ".join(summary_parts) if summary_parts else None
        
        return result.messages, summary_text


class ContextManager:
    """Manage conversation context with reduction strategies"""

    def __init__(self, provider_manager=None):
        """
        Initialize context manager with available strategies
        
        Args:
            provider_manager: Provider manager for LLM API calls
        """
        self.provider_manager = provider_manager
        self.strategies = {
            "truncation": TruncationStrategy(),
            "sliding_window": SlidingWindowStrategy(),
            "summarization": SummarizationStrategy(self),
        }
        
        # Adaptive summarization managers per session
        self._adaptive_managers = {}

    def estimate_tokens(self, messages: List[Message]) -> int:
        """
        Estimate total tokens in message list
        
        Args:
            messages: List of messages
            
        Returns:
            Estimated token count
        """
        total = 0
        for msg in messages:
            # Rough estimation: 1 token ≈ 4 characters
            total += len(msg.content) // 4
            # Add overhead for role and structure
            total += 4
        return total

    async def should_reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> bool:
        """
        Check if context should be reduced
        
        Args:
            messages: Current message list
            config: Context configuration
            
        Returns:
            True if reduction is needed
        """
        # Check turn limit
        if len(messages) > config.max_turns:
            return True
        
        # Check token limit
        estimated_tokens = self.estimate_tokens(messages)
        if estimated_tokens > config.max_tokens:
            return True
        
        return False

    async def apply_strategy(
        self,
        messages: List[Message],
        config: ContextConfig,
        session_id: Optional[str] = None,
        adaptive_config: Optional[AdaptiveSummarizationConfig] = None
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Apply context reduction strategy
        
        Args:
            messages: Messages to potentially reduce
            config: Context configuration
            session_id: Session identifier (required for adaptive summarization)
            adaptive_config: Adaptive summarization configuration
            
        Returns:
            Tuple of (reduced messages, optional summary)
            
        Raises:
            ValueError: If reduction mode is not supported
        """
        # Check if reduction is needed
        if not await self.should_reduce(messages, config):
            return messages, None
        
        # Check for adaptive summarization
        if config.reduction_mode == "adaptive_summarization":
            if not adaptive_config or not adaptive_config.enabled:
                # Fall back to simple summarization
                config.reduction_mode = "summarization"
            elif not session_id:
                raise ValueError("session_id required for adaptive summarization")
            else:
                # Use adaptive summarization
                strategy = self._get_adaptive_strategy(
                    session_id,
                    adaptive_config
                )
                return await strategy.reduce(messages, config)
        
        # Get standard strategy
        strategy = self.strategies.get(config.reduction_mode)
        if strategy is None:
            raise ValueError(f"Unsupported reduction mode: {config.reduction_mode}")
        
        # Apply strategy
        return await strategy.reduce(messages, config)

    async def summarize_messages(
        self,
        messages: List[Message],
        summarization_model: str,
        provider_manager=None
    ) -> str:
        """
        Summarize messages using an LLM
        
        Args:
            messages: Messages to summarize
            summarization_model: Model to use for summarization
            provider_manager: Provider manager for making API calls
            
        Returns:
            Summary text
            
        Note:
            This is a placeholder. Full implementation requires provider_manager
            to make actual API calls to the summarization model.
        """
        # Build conversation text
        conversation_text = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in messages
        ])
        
        # For now, return a simple summary
        # In full implementation, this would call the LLM via provider_manager
        summary = f"Summary of {len(messages)} messages: {conversation_text[:200]}..."
        
        return summary

    def register_strategy(self, name: str, strategy: ContextStrategy) -> None:
        """
        Register a custom context reduction strategy
        
        Args:
            name: Strategy name
            strategy: Strategy implementation
        """
        self.strategies[name] = strategy
    
    def _get_adaptive_strategy(
        self,
        session_id: str,
        adaptive_config: AdaptiveSummarizationConfig
    ) -> AdaptiveSummarizationStrategy:
        """
        Get or create adaptive summarization strategy for a session
        
        Args:
            session_id: Session identifier
            adaptive_config: Adaptive summarization configuration
            
        Returns:
            Adaptive summarization strategy
        """
        # Check if strategy already exists for this session
        if session_id not in self._adaptive_managers:
            self._adaptive_managers[session_id] = AdaptiveSummarizationStrategy(
                adaptive_config,
                session_id,
                self.provider_manager
            )
        
        return self._adaptive_managers[session_id]
    
    def clear_adaptive_session(self, session_id: str) -> None:
        """
        Clear adaptive summarization data for a session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._adaptive_managers:
            # Clear manager state
            self._adaptive_managers[session_id].manager.clear_session(session_id)
            # Remove manager
            del self._adaptive_managers[session_id]

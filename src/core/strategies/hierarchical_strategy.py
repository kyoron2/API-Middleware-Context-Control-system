"""Hierarchical summarization strategy implementation"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from ...models.openai import Message
from ...models.adaptive_summarization import (
    HierarchicalConfig,
    LayerConfig,
    LayerAction,
    ContentAnalysis,
)
from ..content_analyzers import ContentAnalyzers


@dataclass
class MessageLayer:
    """Message with assigned layer information"""
    message: Message
    layer_name: str
    layer_priority: int
    action: LayerAction
    analysis: ContentAnalysis


class HierarchicalStrategy:
    """
    Hierarchical summarization strategy
    
    Classifies messages into layers (critical/important/normal) based on content types
    and applies different actions (preserve/detailed_summary/brief_summary/discard)
    """
    
    def __init__(self, config: HierarchicalConfig, analyzers: ContentAnalyzers):
        """
        Initialize hierarchical strategy
        
        Args:
            config: Hierarchical configuration
            analyzers: Content analyzers for message analysis
        """
        self.config = config
        self.analyzers = analyzers
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate hierarchical configuration"""
        if not self.config.layers:
            raise ValueError("Hierarchical config must have at least one layer")
        
        # Check for duplicate priorities
        priorities = [layer.priority for layer in self.config.layers.values()]
        if len(priorities) != len(set(priorities)):
            raise ValueError("Layer priorities must be unique")
    
    def _classify_message(self, message: Message, analysis: ContentAnalysis) -> MessageLayer:
        """
        Classify a message into a layer based on content analysis
        
        Args:
            message: Message to classify
            analysis: Content analysis result
            
        Returns:
            MessageLayer with assigned layer information
        """
        # Score each layer based on content types
        layer_scores: Dict[str, int] = {}
        
        for layer_name, layer_config in self.config.layers.items():
            score = 0
            
            # Check each content type in layer configuration
            for content_type in layer_config.content_types:
                if content_type == "system_messages" and message.role == "system":
                    score += 100
                elif content_type == "entities" and analysis.entities:
                    score += len(analysis.entities) * 10
                elif content_type == "code_blocks" and analysis.code_blocks:
                    score += len(analysis.code_blocks) * 15
                elif content_type == "urls" and analysis.urls:
                    score += len(analysis.urls) * 5
                elif content_type == "important_markers" and analysis.has_important_marker:
                    score += 50
                elif content_type == "questions" and analysis.has_question:
                    score += 20
                elif content_type == "answers" and analysis.has_answer:
                    score += 20
                elif content_type == "custom_rules" and analysis.rule_matches:
                    # Check for preserve rules
                    preserve_matches = [
                        m for m in analysis.rule_matches
                        if m.action == "preserve"
                    ]
                    score += len(preserve_matches) * 30
            
            layer_scores[layer_name] = score
        
        # Select layer with highest score
        # If tie, use layer with highest priority
        best_layer_name = max(
            layer_scores.keys(),
            key=lambda name: (
                layer_scores[name],
                self.config.layers[name].priority
            )
        )
        
        best_layer = self.config.layers[best_layer_name]
        
        return MessageLayer(
            message=message,
            layer_name=best_layer_name,
            layer_priority=best_layer.priority,
            action=best_layer.action,
            analysis=analysis
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _truncate_message(
        self,
        message: Message,
        max_tokens: Optional[int]
    ) -> Message:
        """
        Truncate message content to max tokens
        
        Args:
            message: Message to truncate
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated message
        """
        if max_tokens is None:
            return message
        
        current_tokens = self._estimate_tokens(message.content)
        if current_tokens <= max_tokens:
            return message
        
        # Truncate content
        max_chars = max_tokens * 4
        truncated_content = message.content[:max_chars] + "... [truncated]"
        
        return Message(
            role=message.role,
            content=truncated_content
        )
    
    def _create_preserved_message(
        self,
        message_layer: MessageLayer
    ) -> Message:
        """
        Create preserved message (complete content)
        
        Args:
            message_layer: Message layer information
            
        Returns:
            Preserved message
        """
        layer_config = self.config.layers[message_layer.layer_name]
        
        # Apply token limit if configured
        return self._truncate_message(
            message_layer.message,
            layer_config.max_tokens_per_message
        )
    
    def _create_detailed_summary_message(
        self,
        message_layer: MessageLayer
    ) -> Message:
        """
        Create detailed summary message
        
        Args:
            message_layer: Message layer information
            
        Returns:
            Detailed summary message
        """
        analysis = message_layer.analysis
        message = message_layer.message
        
        # Build detailed summary with preserved content
        summary_parts = []
        
        # Add role prefix
        summary_parts.append(f"[{message.role}]")
        
        # Add entities if present
        if analysis.entities:
            entity_texts = [e.text for e in analysis.entities[:5]]  # Top 5
            summary_parts.append(f"Entities: {', '.join(entity_texts)}")
        
        # Add code blocks if present
        if analysis.code_blocks:
            code_info = []
            for cb in analysis.code_blocks[:3]:  # Top 3
                lang = cb.language or "code"
                lines = cb.content.count('\n') + 1
                code_info.append(f"{lang}({lines} lines)")
            summary_parts.append(f"Code: {', '.join(code_info)}")
        
        # Add URLs if present
        if analysis.urls:
            url_count = len(analysis.urls)
            summary_parts.append(f"URLs: {url_count} link(s)")
        
        # Add content preview (first 200 chars)
        content_preview = message.content[:200]
        if len(message.content) > 200:
            content_preview += "..."
        summary_parts.append(f"Content: {content_preview}")
        
        summary_content = " | ".join(summary_parts)
        
        # Apply token limit
        layer_config = self.config.layers[message_layer.layer_name]
        summary_message = Message(
            role="system",
            content=f"[Detailed Summary] {summary_content}"
        )
        
        return self._truncate_message(
            summary_message,
            layer_config.max_tokens_per_message
        )
    
    def _create_brief_summary_message(
        self,
        message_layer: MessageLayer
    ) -> Message:
        """
        Create brief summary message
        
        Args:
            message_layer: Message layer information
            
        Returns:
            Brief summary message
        """
        message = message_layer.message
        analysis = message_layer.analysis
        
        # Build brief summary
        summary_parts = [f"[{message.role}]"]
        
        # Add key indicators
        indicators = []
        if analysis.entities:
            indicators.append(f"{len(analysis.entities)} entities")
        if analysis.code_blocks:
            indicators.append(f"{len(analysis.code_blocks)} code blocks")
        if analysis.urls:
            indicators.append(f"{len(analysis.urls)} URLs")
        
        if indicators:
            summary_parts.append(", ".join(indicators))
        
        # Add very short content preview (50 chars)
        content_preview = message.content[:50]
        if len(message.content) > 50:
            content_preview += "..."
        summary_parts.append(content_preview)
        
        summary_content = " | ".join(summary_parts)
        
        # Apply token limit
        layer_config = self.config.layers[message_layer.layer_name]
        summary_message = Message(
            role="system",
            content=f"[Brief Summary] {summary_content}"
        )
        
        return self._truncate_message(
            summary_message,
            layer_config.max_tokens_per_message
        )
    
    async def apply(
        self,
        messages: List[Message]
    ) -> List[Message]:
        """
        Apply hierarchical summarization strategy
        
        Args:
            messages: Messages to process
            
        Returns:
            Processed messages with hierarchical summarization applied
        """
        if not messages:
            return []
        
        # Step 1: Analyze all messages
        message_layers: List[MessageLayer] = []
        
        for message in messages:
            # Analyze message content
            analysis = self.analyzers.analyze(message.content)
            
            # Classify into layer
            message_layer = self._classify_message(message, analysis)
            message_layers.append(message_layer)
        
        # Step 2: Process each message according to its layer action
        result_messages: List[Message] = []
        
        for message_layer in message_layers:
            if message_layer.action == LayerAction.PRESERVE:
                # Preserve complete message
                result_messages.append(
                    self._create_preserved_message(message_layer)
                )
            
            elif message_layer.action == LayerAction.DETAILED_SUMMARY:
                # Create detailed summary
                result_messages.append(
                    self._create_detailed_summary_message(message_layer)
                )
            
            elif message_layer.action == LayerAction.BRIEF_SUMMARY:
                # Create brief summary
                result_messages.append(
                    self._create_brief_summary_message(message_layer)
                )
            
            elif message_layer.action == LayerAction.DISCARD:
                # Discard message (don't add to result)
                pass
        
        return result_messages
    
    def get_layer_statistics(
        self,
        messages: List[Message]
    ) -> Dict[str, int]:
        """
        Get statistics about message layer distribution
        
        Args:
            messages: Messages to analyze
            
        Returns:
            Dictionary mapping layer names to message counts
        """
        layer_counts: Dict[str, int] = {
            layer_name: 0
            for layer_name in self.config.layers.keys()
        }
        
        for message in messages:
            analysis = self.analyzers.analyze(message.content)
            message_layer = self._classify_message(message, analysis)
            layer_counts[message_layer.layer_name] += 1
        
        return layer_counts

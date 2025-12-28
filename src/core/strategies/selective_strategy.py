"""Selective summarization strategy implementation"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from ...models.openai import Message
from ...models.adaptive_summarization import SelectiveConfig, ContentAnalysis
from ..content_analyzers import ContentAnalyzers
from ..importance_scorer import ImportanceScorer


class SelectionAction(str, Enum):
    """Action to take for a message based on importance score"""
    PRESERVE = "preserve"      # Keep complete message
    SUMMARIZE = "summarize"    # Create summary
    DISCARD = "discard"        # Remove message


@dataclass
class ScoredMessage:
    """Message with importance score and selection action"""
    message: Message
    score: float
    action: SelectionAction
    analysis: ContentAnalysis


class SelectiveStrategy:
    """
    Selective summarization strategy
    
    Uses importance scoring to decide which messages to preserve,
    summarize, or discard based on configurable thresholds.
    """
    
    def __init__(
        self,
        config: SelectiveConfig,
        scorer: ImportanceScorer,
        analyzers: ContentAnalyzers
    ):
        """
        Initialize selective strategy
        
        Args:
            config: Selective configuration
            scorer: Importance scorer
            analyzers: Content analyzers
        """
        self.config = config
        self.scorer = scorer
        self.analyzers = analyzers
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate selective configuration"""
        # Check threshold ordering
        if not (self.config.discard_threshold 
                <= self.config.summarize_threshold 
                <= self.config.preserve_threshold):
            raise ValueError(
                "Thresholds must be ordered: "
                "discard <= summarize <= preserve"
            )
    
    def _determine_action(self, score: float) -> SelectionAction:
        """
        Determine action based on importance score
        
        Args:
            score: Importance score
            
        Returns:
            Selection action
        """
        if score >= self.config.preserve_threshold:
            return SelectionAction.PRESERVE
        elif score >= self.config.summarize_threshold:
            return SelectionAction.SUMMARIZE
        elif score >= self.config.discard_threshold:
            return SelectionAction.SUMMARIZE  # Low priority summary
        else:
            return SelectionAction.DISCARD
    
    def _score_messages(
        self,
        messages: List[Message]
    ) -> List[ScoredMessage]:
        """
        Score all messages and determine actions
        
        Args:
            messages: Messages to score
            
        Returns:
            List of scored messages with actions
        """
        scored_messages: List[ScoredMessage] = []
        
        for message in messages:
            # Analyze message content
            analysis = self.analyzers.analyze(message.content)
            
            # Calculate importance score
            score = self.scorer.score_message(message, analysis)
            
            # Determine action
            action = self._determine_action(score)
            
            scored_messages.append(ScoredMessage(
                message=message,
                score=score,
                action=action,
                analysis=analysis
            ))
        
        return scored_messages
    
    def _create_summary_message(
        self,
        scored_message: ScoredMessage
    ) -> Message:
        """
        Create summary message for a scored message
        
        Args:
            scored_message: Scored message to summarize
            
        Returns:
            Summary message
        """
        message = scored_message.message
        analysis = scored_message.analysis
        score = scored_message.score
        
        # Build summary with key information
        summary_parts = []
        
        # Add role and score
        summary_parts.append(f"[{message.role}, score={score:.1f}]")
        
        # Add key content indicators
        indicators = []
        if analysis.entities:
            entity_texts = [e.text for e in analysis.entities[:3]]
            indicators.append(f"Entities: {', '.join(entity_texts)}")
        
        if analysis.code_blocks:
            code_count = len(analysis.code_blocks)
            indicators.append(f"Code: {code_count} block(s)")
        
        if analysis.urls:
            url_count = len(analysis.urls)
            indicators.append(f"URLs: {url_count} link(s)")
        
        if indicators:
            summary_parts.append(" | ".join(indicators))
        
        # Add content preview based on score
        if score >= self.config.summarize_threshold:
            # Higher score - longer preview
            preview_length = 150
        else:
            # Lower score - shorter preview
            preview_length = 50
        
        content_preview = message.content[:preview_length]
        if len(message.content) > preview_length:
            content_preview += "..."
        
        summary_parts.append(f"Content: {content_preview}")
        
        summary_content = " | ".join(summary_parts)
        
        return Message(
            role="system",
            content=f"[Selective Summary] {summary_content}"
        )
    
    async def apply(
        self,
        messages: List[Message]
    ) -> List[Message]:
        """
        Apply selective summarization strategy
        
        Args:
            messages: Messages to process
            
        Returns:
            Processed messages with selective summarization applied
        """
        if not messages:
            return []
        
        # Step 1: Score all messages
        scored_messages = self._score_messages(messages)
        
        # Step 2: Process each message according to its action
        result_messages: List[Message] = []
        
        for scored_msg in scored_messages:
            if scored_msg.action == SelectionAction.PRESERVE:
                # Preserve complete message
                result_messages.append(scored_msg.message)
            
            elif scored_msg.action == SelectionAction.SUMMARIZE:
                # Create summary
                summary_msg = self._create_summary_message(scored_msg)
                result_messages.append(summary_msg)
            
            elif scored_msg.action == SelectionAction.DISCARD:
                # Discard message (don't add to result)
                pass
        
        return result_messages
    
    def get_score_distribution(
        self,
        messages: List[Message]
    ) -> Dict[str, int]:
        """
        Get distribution of messages across score ranges
        
        Args:
            messages: Messages to analyze
            
        Returns:
            Dictionary mapping actions to message counts
        """
        scored_messages = self._score_messages(messages)
        
        distribution = {
            "preserve": 0,
            "summarize": 0,
            "discard": 0
        }
        
        for scored_msg in scored_messages:
            distribution[scored_msg.action.value] += 1
        
        return distribution
    
    def get_top_messages(
        self,
        messages: List[Message],
        top_k: int = 5
    ) -> List[Tuple[Message, float]]:
        """
        Get top K most important messages
        
        Args:
            messages: Messages to analyze
            top_k: Number of top messages to return
            
        Returns:
            List of (message, score) tuples sorted by score
        """
        scored_messages = self._score_messages(messages)
        
        # Sort by score descending
        sorted_messages = sorted(
            scored_messages,
            key=lambda sm: sm.score,
            reverse=True
        )
        
        # Return top K
        return [
            (sm.message, sm.score)
            for sm in sorted_messages[:top_k]
        ]
    
    def get_score_statistics(
        self,
        messages: List[Message]
    ) -> Dict[str, float]:
        """
        Get statistical summary of importance scores
        
        Args:
            messages: Messages to analyze
            
        Returns:
            Dictionary with score statistics
        """
        if not messages:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0
            }
        
        scored_messages = self._score_messages(messages)
        scores = [sm.score for sm in scored_messages]
        
        scores_sorted = sorted(scores)
        n = len(scores)
        
        return {
            "min": min(scores),
            "max": max(scores),
            "mean": sum(scores) / n,
            "median": scores_sorted[n // 2] if n % 2 == 1 
                     else (scores_sorted[n // 2 - 1] + scores_sorted[n // 2]) / 2
        }

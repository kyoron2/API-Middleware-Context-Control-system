"""
Importance Scorer for Adaptive Summarization

This module calculates importance scores for messages based on their content.
Higher scores indicate more important messages that should be preserved.
"""

from src.models.adaptive_summarization import (
    ScoringConfig, ContentAnalysis
)
from src.models.session import Message


class ImportanceScorer:
    """Calculate importance scores for messages"""
    
    def __init__(self, config: ScoringConfig):
        self.config = config
    
    def score_message(
        self, 
        message: Message, 
        analysis: ContentAnalysis
    ) -> float:
        """
        Calculate importance score for a message.
        
        Args:
            message: The message to score
            analysis: Content analysis results for the message
            
        Returns:
            Importance score (higher = more important)
        """
        score = 0.0
        
        # Base score from content analysis
        if analysis.has_entities:
            score += self.config.has_entities * len(analysis.entities)
        
        if analysis.has_code:
            score += self.config.has_code * len(analysis.code_blocks)
        
        if analysis.has_urls:
            score += self.config.has_urls * len(analysis.urls)
        
        if analysis.has_important_marker:
            score += self.config.marked_important
        
        if analysis.is_question:
            score += self.config.is_question
        
        if analysis.is_answer:
            score += self.config.is_answer
        
        # Length bonus (longer messages tend to be more substantial)
        content_length = len(message.content) if message.content else 0
        score += content_length * self.config.length_bonus
        
        # Role-based adjustments
        if message.role == "system":
            # System messages are always important
            score += 50.0
        elif message.role == "user":
            # User messages slightly more important than assistant
            score += 2.0
        
        # Normalize score to configured range
        score = max(self.config.min_score, min(score, self.config.max_score))
        
        return score
    
    def score_messages(
        self, 
        messages: list[Message], 
        analyses: list[ContentAnalysis]
    ) -> list[float]:
        """
        Score multiple messages at once.
        
        Args:
            messages: List of messages to score
            analyses: List of content analyses (must match messages length)
            
        Returns:
            List of importance scores
        """
        if len(messages) != len(analyses):
            raise ValueError(
                f"Messages and analyses length mismatch: "
                f"{len(messages)} != {len(analyses)}"
            )
        
        return [
            self.score_message(msg, analysis)
            for msg, analysis in zip(messages, analyses)
        ]
    
    def get_score_breakdown(
        self, 
        message: Message, 
        analysis: ContentAnalysis
    ) -> dict[str, float]:
        """
        Get detailed breakdown of score components.
        Useful for debugging and understanding scoring decisions.
        
        Args:
            message: The message to score
            analysis: Content analysis results
            
        Returns:
            Dictionary with score component breakdown
        """
        breakdown = {
            "entities": 0.0,
            "code_blocks": 0.0,
            "urls": 0.0,
            "important_marker": 0.0,
            "is_question": 0.0,
            "is_answer": 0.0,
            "length_bonus": 0.0,
            "role_bonus": 0.0,
            "total": 0.0
        }
        
        if analysis.has_entities:
            breakdown["entities"] = self.config.has_entities * len(analysis.entities)
        
        if analysis.has_code:
            breakdown["code_blocks"] = self.config.has_code * len(analysis.code_blocks)
        
        if analysis.has_urls:
            breakdown["urls"] = self.config.has_urls * len(analysis.urls)
        
        if analysis.has_important_marker:
            breakdown["important_marker"] = self.config.marked_important
        
        if analysis.is_question:
            breakdown["is_question"] = self.config.is_question
        
        if analysis.is_answer:
            breakdown["is_answer"] = self.config.is_answer
        
        content_length = len(message.content) if message.content else 0
        breakdown["length_bonus"] = content_length * self.config.length_bonus
        
        if message.role == "system":
            breakdown["role_bonus"] = 50.0
        elif message.role == "user":
            breakdown["role_bonus"] = 2.0
        
        # Calculate total
        total = sum(breakdown.values())
        breakdown["total"] = max(
            self.config.min_score, 
            min(total, self.config.max_score)
        )
        
        return breakdown
    
    def classify_by_score(
        self, 
        score: float, 
        preserve_threshold: float,
        summarize_threshold: float,
        discard_threshold: float
    ) -> str:
        """
        Classify message action based on score and thresholds.
        
        Args:
            score: Importance score
            preserve_threshold: Threshold for preservation
            summarize_threshold: Threshold for summarization
            discard_threshold: Threshold for discarding
            
        Returns:
            Action: "preserve", "summarize", or "discard"
        """
        if score >= preserve_threshold:
            return "preserve"
        elif score >= summarize_threshold:
            return "summarize"
        elif score >= discard_threshold:
            return "summarize"  # Still summarize, just more briefly
        else:
            return "discard"
    
    def get_top_k_messages(
        self,
        messages: list[Message],
        scores: list[float],
        k: int
    ) -> list[tuple[Message, float]]:
        """
        Get top K most important messages.
        
        Args:
            messages: List of messages
            scores: List of scores (must match messages length)
            k: Number of top messages to return
            
        Returns:
            List of (message, score) tuples, sorted by score descending
        """
        if len(messages) != len(scores):
            raise ValueError(
                f"Messages and scores length mismatch: "
                f"{len(messages)} != {len(scores)}"
            )
        
        # Combine messages with scores
        message_scores = list(zip(messages, scores))
        
        # Sort by score descending
        message_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K
        return message_scores[:k]
    
    def calculate_average_score(self, scores: list[float]) -> float:
        """Calculate average score from a list of scores"""
        if not scores:
            return 0.0
        return sum(scores) / len(scores)
    
    def calculate_score_percentile(
        self, 
        score: float, 
        all_scores: list[float]
    ) -> float:
        """
        Calculate what percentile a score falls into.
        
        Args:
            score: The score to check
            all_scores: All scores for comparison
            
        Returns:
            Percentile (0.0 to 1.0)
        """
        if not all_scores:
            return 0.0
        
        # Count how many scores are less than or equal to this score
        count_below = sum(1 for s in all_scores if s <= score)
        
        return count_below / len(all_scores)

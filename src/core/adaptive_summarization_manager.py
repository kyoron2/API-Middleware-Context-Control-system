"""Adaptive Summarization Manager - Coordinates all summarization strategies"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.openai import Message
from ..models.adaptive_summarization import (
    AdaptiveSummarizationConfig,
    SummarizationResult,
    SummarizationStatistics,
    SummarizationStrategy,
    ContentAnalysis,
)
from .content_analyzers import ContentAnalyzers
from .importance_scorer import ImportanceScorer
from .strategies.hierarchical_strategy import HierarchicalStrategy
from .strategies.incremental_strategy import IncrementalStrategy
from .strategies.selective_strategy import SelectiveStrategy


class AdaptiveSummarizationManager:
    """
    Adaptive Summarization Manager
    
    Coordinates the entire adaptive summarization process:
    - Strategy selection and execution
    - Content analysis and preservation
    - Quality control and fallback
    - Statistics generation
    """
    
    def __init__(
        self,
        config: AdaptiveSummarizationConfig,
        provider_manager=None
    ):
        """
        Initialize adaptive summarization manager
        
        Args:
            config: Adaptive summarization configuration
            provider_manager: Provider manager for LLM API calls
        """
        self.config = config
        self.provider_manager = provider_manager
        
        # Initialize content analyzers
        self.analyzers = ContentAnalyzers(config.analyzers_config)
        
        # Initialize importance scorer
        self.scorer = ImportanceScorer(config.scoring_config)
        
        # Initialize strategies
        self._init_strategies()
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        if not self.config.enabled:
            return
        
        # Validate strategy name
        valid_strategies = [s.value for s in SummarizationStrategy]
        if self.config.strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy: {self.config.strategy}. "
                f"Must be one of: {valid_strategies}"
            )
        
        # Validate strategy-specific config
        if self.config.strategy == SummarizationStrategy.HIERARCHICAL:
            if not self.config.hierarchical_config:
                raise ValueError("Hierarchical strategy requires hierarchical_config")
        
        elif self.config.strategy == SummarizationStrategy.INCREMENTAL:
            if not self.config.incremental_config:
                raise ValueError("Incremental strategy requires incremental_config")
        
        elif self.config.strategy == SummarizationStrategy.SELECTIVE:
            if not self.config.selective_config:
                raise ValueError("Selective strategy requires selective_config")
        
        # Validate quality control settings
        if self.config.target_tokens and self.config.target_tokens < 100:
            raise ValueError("target_tokens must be at least 100")
        
        if self.config.min_summary_length > self.config.max_summary_length:
            raise ValueError("min_summary_length must be <= max_summary_length")
    
    def _init_strategies(self) -> None:
        """Initialize all strategies"""
        self.strategies = {}
        
        # Hierarchical strategy
        if self.config.hierarchical_config:
            self.strategies[SummarizationStrategy.HIERARCHICAL] = HierarchicalStrategy(
                self.config.hierarchical_config,
                self.analyzers
            )
        
        # Incremental strategy
        if self.config.incremental_config:
            self.strategies[SummarizationStrategy.INCREMENTAL] = IncrementalStrategy(
                self.config.incremental_config
            )
        
        # Selective strategy
        if self.config.selective_config:
            self.strategies[SummarizationStrategy.SELECTIVE] = SelectiveStrategy(
                self.config.selective_config,
                self.scorer,
                self.analyzers
            )
    
    def _estimate_tokens(self, messages: List[Message]) -> int:
        """Estimate total tokens in messages"""
        total = 0
        for msg in messages:
            total += len(msg.content) // 4 + 4
        return total
    
    def _apply_content_preservation(
        self,
        messages: List[Message]
    ) -> Dict[str, Any]:
        """
        Apply content preservation rules
        
        Args:
            messages: Messages to analyze
            
        Returns:
            Dictionary with preserved content
        """
        preserved_content = {
            "entities": [],
            "code_blocks": [],
            "urls": [],
            "custom_matches": []
        }
        
        for message in messages:
            analysis = self.analyzers.analyze(message.content)
            
            # Preserve entities
            if self.config.preserve_entities and analysis.entities:
                preserved_content["entities"].extend([
                    {
                        "text": e.text,
                        "type": e.type.value,
                        "message_role": message.role
                    }
                    for e in analysis.entities
                ])
            
            # Preserve code blocks
            if self.config.preserve_code and analysis.code_blocks:
                preserved_content["code_blocks"].extend([
                    {
                        "language": cb.language,
                        "lines": cb.content.count('\n') + 1,
                        "message_role": message.role
                    }
                    for cb in analysis.code_blocks
                ])
            
            # Preserve URLs
            if self.config.preserve_urls and analysis.urls:
                preserved_content["urls"].extend(analysis.urls)
            
            # Preserve custom rule matches
            if analysis.rule_matches:
                preserved_content["custom_matches"].extend([
                    {
                        "text": m.matched_text,
                        "rule_type": m.rule_type.value,
                        "action": m.action.value
                    }
                    for m in analysis.rule_matches
                ])
        
        return preserved_content
    
    def _check_quality(
        self,
        original_messages: List[Message],
        summarized_messages: List[Message]
    ) -> bool:
        """
        Check if summarization meets quality requirements
        
        Args:
            original_messages: Original messages
            summarized_messages: Summarized messages
            
        Returns:
            True if quality is acceptable
        """
        # Check minimum length
        total_length = sum(len(msg.content) for msg in summarized_messages)
        if total_length < self.config.min_summary_length:
            return False
        
        # Check maximum length
        if total_length > self.config.max_summary_length:
            return False
        
        # Check token target
        if self.config.target_tokens:
            estimated_tokens = self._estimate_tokens(summarized_messages)
            if estimated_tokens > self.config.target_tokens:
                return False
        
        # Check compression ratio (should reduce size)
        original_tokens = self._estimate_tokens(original_messages)
        summarized_tokens = self._estimate_tokens(summarized_messages)
        if summarized_tokens >= original_tokens:
            return False
        
        return True
    
    def _create_fallback_summary(
        self,
        messages: List[Message]
    ) -> List[Message]:
        """
        Create fallback summary using simple truncation
        
        Args:
            messages: Messages to summarize
            
        Returns:
            Truncated messages
        """
        # Keep system messages
        system_messages = [msg for msg in messages if msg.role == "system"]
        other_messages = [msg for msg in messages if msg.role != "system"]
        
        # Keep last 5 messages
        kept_messages = other_messages[-5:] if len(other_messages) > 5 else other_messages
        
        return system_messages + kept_messages
    
    async def _execute_with_timeout(
        self,
        strategy,
        messages: List[Message],
        session_id: str
    ) -> List[Message]:
        """
        Execute strategy with timeout
        
        Args:
            strategy: Strategy to execute
            messages: Messages to process
            session_id: Session identifier
            
        Returns:
            Processed messages
        """
        if not self.config.async_execution:
            # Synchronous execution
            if hasattr(strategy, 'apply'):
                if strategy.__class__.__name__ == 'IncrementalStrategy':
                    return await strategy.apply(messages, session_id, self.provider_manager)
                else:
                    return await strategy.apply(messages)
            return messages
        
        # Asynchronous execution with timeout
        try:
            if strategy.__class__.__name__ == 'IncrementalStrategy':
                result = await asyncio.wait_for(
                    strategy.apply(messages, session_id, self.provider_manager),
                    timeout=self.config.timeout_seconds
                )
            else:
                result = await asyncio.wait_for(
                    strategy.apply(messages),
                    timeout=self.config.timeout_seconds
                )
            return result
        except asyncio.TimeoutError:
            # Timeout - use fallback
            return self._create_fallback_summary(messages)
    
    async def summarize(
        self,
        messages: List[Message],
        session_id: str,
        strategy_override: Optional[str] = None
    ) -> SummarizationResult:
        """
        Execute adaptive summarization
        
        Args:
            messages: Messages to summarize
            session_id: Session identifier
            strategy_override: Optional strategy override
            
        Returns:
            Summarization result with processed messages and statistics
        """
        start_time = time.time()
        
        # Check if enabled
        if not self.config.enabled:
            return SummarizationResult(
                messages=messages,
                preserved_content={},
                statistics=SummarizationStatistics(
                    original_tokens=self._estimate_tokens(messages),
                    summarized_tokens=self._estimate_tokens(messages),
                    compression_ratio=1.0,
                    entities_preserved=0,
                    code_blocks_preserved=0,
                    urls_preserved=0,
                    execution_time_ms=0.0
                )
            )
        
        # Determine strategy
        strategy_name = strategy_override or self.config.strategy
        strategy = self.strategies.get(strategy_name)
        
        if strategy is None:
            raise ValueError(f"Strategy not initialized: {strategy_name}")
        
        # Calculate original tokens
        original_tokens = self._estimate_tokens(messages)
        
        try:
            # Execute strategy with timeout
            summarized_messages = await self._execute_with_timeout(
                strategy,
                messages,
                session_id
            )
            
            # Check quality
            if not self._check_quality(messages, summarized_messages):
                # Quality check failed - use fallback
                summarized_messages = self._create_fallback_summary(messages)
            
        except Exception as e:
            # Error occurred - use fallback
            print(f"Summarization error: {e}")
            summarized_messages = self._create_fallback_summary(messages)
        
        # Apply content preservation
        preserved_content = self._apply_content_preservation(messages)
        
        # Calculate statistics
        summarized_tokens = self._estimate_tokens(summarized_messages)
        compression_ratio = summarized_tokens / original_tokens if original_tokens > 0 else 1.0
        execution_time_ms = (time.time() - start_time) * 1000
        
        statistics = SummarizationStatistics(
            original_tokens=original_tokens,
            summarized_tokens=summarized_tokens,
            compression_ratio=compression_ratio,
            entities_preserved=len(preserved_content.get("entities", [])),
            code_blocks_preserved=len(preserved_content.get("code_blocks", [])),
            urls_preserved=len(preserved_content.get("urls", [])),
            execution_time_ms=execution_time_ms
        )
        
        return SummarizationResult(
            messages=summarized_messages,
            preserved_content=preserved_content,
            statistics=statistics
        )
    
    def get_strategy_info(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a strategy
        
        Args:
            strategy_name: Strategy name (uses configured strategy if None)
            
        Returns:
            Dictionary with strategy information
        """
        strategy_name = strategy_name or self.config.strategy
        strategy = self.strategies.get(strategy_name)
        
        if strategy is None:
            return {"error": f"Strategy not found: {strategy_name}"}
        
        info = {
            "name": strategy_name,
            "class": strategy.__class__.__name__,
            "enabled": self.config.enabled
        }
        
        # Add strategy-specific info
        if strategy_name == SummarizationStrategy.HIERARCHICAL:
            info["layers"] = list(self.config.hierarchical_config.layers.keys())
        
        elif strategy_name == SummarizationStrategy.INCREMENTAL:
            info["summary_window"] = self.config.incremental_config.summary_window
            info["keep_recent"] = self.config.incremental_config.keep_recent
            info["max_depth"] = self.config.incremental_config.max_summary_depth
        
        elif strategy_name == SummarizationStrategy.SELECTIVE:
            info["preserve_threshold"] = self.config.selective_config.preserve_threshold
            info["summarize_threshold"] = self.config.selective_config.summarize_threshold
            info["discard_threshold"] = self.config.selective_config.discard_threshold
        
        return info
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear session-specific data
        
        Args:
            session_id: Session identifier
        """
        # Clear incremental strategy state
        if SummarizationStrategy.INCREMENTAL in self.strategies:
            strategy = self.strategies[SummarizationStrategy.INCREMENTAL]
            strategy.clear_session(session_id)

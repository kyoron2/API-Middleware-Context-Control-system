"""
Adaptive Summarization Data Models

This module defines all data models for the adaptive summarization feature,
including configuration classes, content analysis results, and summarization outputs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class SummarizationStrategy(str, Enum):
    """Summarization strategy types"""
    HIERARCHICAL = "hierarchical"
    INCREMENTAL = "incremental"
    SELECTIVE = "selective"


class LayerAction(str, Enum):
    """Actions for hierarchical layers"""
    PRESERVE = "preserve"
    DETAILED_SUMMARY = "detailed_summary"
    BRIEF_SUMMARY = "brief_summary"
    DISCARD = "discard"


class RuleType(str, Enum):
    """Custom rule types"""
    REGEX = "regex"
    KEYWORD = "keyword"
    STRUCTURE = "structure"


class RuleAction(str, Enum):
    """Actions for custom rules"""
    PRESERVE = "preserve"
    HIGHLIGHT = "highlight"
    REDACT = "redact"


class EntityType(str, Enum):
    """Entity types for extraction"""
    PERSON = "PERSON"
    ORG = "ORG"
    GPE = "GPE"  # Geo-Political Entity
    PRODUCT = "PRODUCT"
    TECH = "TECH"  # Technology stack
    VERSION = "VERSION"
    CONFIG = "CONFIG"  # Configuration info


# ============================================================================
# Configuration Models
# ============================================================================

@dataclass
class LayerConfig:
    """Configuration for a hierarchical layer"""
    name: str
    priority: int
    content_types: List[str]  # system_messages, entities, code_blocks, etc.
    action: LayerAction
    max_tokens_per_message: Optional[int] = None
    
    def __post_init__(self):
        if isinstance(self.action, str):
            self.action = LayerAction(self.action)


@dataclass
class HierarchicalConfig:
    """Configuration for hierarchical summarization strategy"""
    layers: Dict[str, LayerConfig] = field(default_factory=dict)
    
    @classmethod
    def default(cls) -> "HierarchicalConfig":
        """Create default hierarchical configuration"""
        return cls(layers={
            "critical": LayerConfig(
                name="critical",
                priority=1,
                content_types=["system_messages", "entities", "code_blocks", "urls", "marked_important"],
                action=LayerAction.PRESERVE
            ),
            "important": LayerConfig(
                name="important",
                priority=2,
                content_types=["user_questions", "assistant_answers"],
                action=LayerAction.DETAILED_SUMMARY,
                max_tokens_per_message=200
            ),
            "normal": LayerConfig(
                name="normal",
                priority=3,
                content_types=["confirmations", "chitchat"],
                action=LayerAction.BRIEF_SUMMARY,
                max_tokens_per_message=50
            )
        })


@dataclass
class IncrementalConfig:
    """Configuration for incremental summarization strategy"""
    summary_window: int = 10  # Trigger summary every N turns
    keep_recent: int = 5  # Keep last N turns as full messages
    max_summary_depth: int = 3  # Maximum nesting depth
    summary_prefix: str = "[摘要]"


@dataclass
class SelectiveConfig:
    """Configuration for selective summarization strategy"""
    preserve_threshold: float = 10.0  # Preserve if score >= this
    summarize_threshold: float = 5.0  # Summarize if score >= this
    discard_threshold: float = 2.0  # Discard if score < this
    
    def __post_init__(self):
        # Validate thresholds
        if not (self.discard_threshold <= self.summarize_threshold <= self.preserve_threshold):
            raise ValueError(
                f"Invalid threshold configuration: "
                f"discard ({self.discard_threshold}) <= "
                f"summarize ({self.summarize_threshold}) <= "
                f"preserve ({self.preserve_threshold})"
            )


@dataclass
class ScoringConfig:
    """Configuration for importance scoring"""
    has_entities: float = 10.0
    has_code: float = 15.0
    has_urls: float = 8.0
    marked_important: float = 20.0
    is_question: float = 5.0
    is_answer: float = 5.0
    length_bonus: float = 0.01  # Per character
    
    # Minimum and maximum scores
    min_score: float = 0.0
    max_score: float = 100.0


@dataclass
class AnalyzersConfig:
    """Configuration for content analyzers"""
    # Entity extraction
    entity_extraction_enabled: bool = True
    entity_types: List[EntityType] = field(default_factory=lambda: [
        EntityType.PERSON, EntityType.ORG, EntityType.TECH, 
        EntityType.VERSION, EntityType.CONFIG
    ])
    entity_cache_enabled: bool = True
    
    # Code block detection
    code_detection_enabled: bool = True
    code_min_lines: int = 2
    code_max_lines: int = 50
    preserve_inline_code: bool = True
    
    # URL extraction
    url_extraction_enabled: bool = True
    url_shorten: bool = False
    url_verify_alive: bool = False
    
    def __post_init__(self):
        # Convert string entity types to enum
        self.entity_types = [
            EntityType(t) if isinstance(t, str) else t 
            for t in self.entity_types
        ]


@dataclass
class CustomRule:
    """Custom preservation rule"""
    type: RuleType
    action: RuleAction
    description: str = ""
    
    # For regex rules
    pattern: Optional[str] = None
    
    # For keyword rules
    keywords: Optional[List[str]] = None
    
    # For structure rules
    format: Optional[str] = None  # json, table, etc.
    
    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = RuleType(self.type)
        if isinstance(self.action, str):
            self.action = RuleAction(self.action)
        
        # Validate rule configuration
        if self.type == RuleType.REGEX and not self.pattern:
            raise ValueError("Regex rule must have a pattern")
        if self.type == RuleType.KEYWORD and not self.keywords:
            raise ValueError("Keyword rule must have keywords")
        if self.type == RuleType.STRUCTURE and not self.format:
            raise ValueError("Structure rule must have a format")


@dataclass
class AdaptiveSummarizationConfig:
    """Main configuration for adaptive summarization"""
    enabled: bool = False
    strategy: SummarizationStrategy = SummarizationStrategy.HIERARCHICAL
    
    # Content preservation
    preserve_entities: bool = True
    preserve_code: bool = True
    preserve_urls: bool = True
    
    # Strategy-specific configurations
    hierarchical_config: HierarchicalConfig = field(default_factory=HierarchicalConfig.default)
    incremental_config: IncrementalConfig = field(default_factory=IncrementalConfig)
    selective_config: SelectiveConfig = field(default_factory=SelectiveConfig)
    
    # Analyzers and scoring
    analyzers_config: AnalyzersConfig = field(default_factory=AnalyzersConfig)
    scoring_config: ScoringConfig = field(default_factory=ScoringConfig)
    
    # Custom rules
    custom_rules: List[CustomRule] = field(default_factory=list)
    
    # Performance settings
    async_execution: bool = True
    timeout_seconds: int = 30
    
    # Quality control
    target_tokens: Optional[int] = None
    min_summary_length: int = 50
    max_summary_length: int = 2000
    
    # Summarization model
    summarization_model: Optional[str] = None
    summarization_prompt: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.strategy, str):
            self.strategy = SummarizationStrategy(self.strategy)
        
        # Validate configuration
        if self.min_summary_length > self.max_summary_length:
            raise ValueError(
                f"min_summary_length ({self.min_summary_length}) must be <= "
                f"max_summary_length ({self.max_summary_length})"
            )



# ============================================================================
# Content Analysis Models
# ============================================================================

@dataclass
class Entity:
    """Extracted entity from text"""
    text: str
    type: EntityType
    start: int
    end: int
    confidence: float = 1.0
    
    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = EntityType(self.type)


@dataclass
class CodeBlock:
    """Detected code block"""
    content: str
    language: Optional[str] = None
    start: int = 0
    end: int = 0
    is_inline: bool = False
    
    @property
    def line_count(self) -> int:
        """Count number of lines in code block"""
        return len(self.content.split('\n'))


@dataclass
class RuleMatch:
    """Result of custom rule matching"""
    rule: CustomRule
    matched_text: str
    start: int
    end: int
    
    def apply_action(self) -> str:
        """Apply the rule's action to the matched text"""
        if self.rule.action == RuleAction.PRESERVE:
            return self.matched_text
        elif self.rule.action == RuleAction.HIGHLIGHT:
            return f"[IMPORTANT] {self.matched_text}"
        elif self.rule.action == RuleAction.REDACT:
            return "[REDACTED]"
        return self.matched_text


@dataclass
class ContentAnalysis:
    """Complete analysis of message content"""
    entities: List[Entity] = field(default_factory=list)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    rule_matches: List[RuleMatch] = field(default_factory=list)
    
    # Computed properties
    has_entities: bool = False
    has_code: bool = False
    has_urls: bool = False
    has_important_marker: bool = False
    is_question: bool = False
    is_answer: bool = False
    
    def __post_init__(self):
        # Update computed properties
        self.has_entities = len(self.entities) > 0
        self.has_code = len(self.code_blocks) > 0
        self.has_urls = len(self.urls) > 0


# ============================================================================
# Summarization Result Models
# ============================================================================

@dataclass
class SummarizationStatistics:
    """Statistics about summarization operation"""
    original_tokens: int
    summarized_tokens: int
    compression_ratio: float
    entities_preserved: int = 0
    code_blocks_preserved: int = 0
    urls_preserved: int = 0
    execution_time_ms: float = 0.0
    
    @classmethod
    def calculate(
        cls,
        original_tokens: int,
        summarized_tokens: int,
        preserved_content: Dict[str, Any],
        execution_time_ms: float
    ) -> "SummarizationStatistics":
        """Calculate statistics from summarization results"""
        compression_ratio = (
            1.0 - (summarized_tokens / original_tokens)
            if original_tokens > 0 else 0.0
        )
        
        return cls(
            original_tokens=original_tokens,
            summarized_tokens=summarized_tokens,
            compression_ratio=compression_ratio,
            entities_preserved=len(preserved_content.get("entities", [])),
            code_blocks_preserved=len(preserved_content.get("code_blocks", [])),
            urls_preserved=len(preserved_content.get("urls", [])),
            execution_time_ms=execution_time_ms
        )


@dataclass
class SummarizationResult:
    """Result of summarization operation"""
    messages: List[Any]  # List of Message objects (avoiding circular import)
    preserved_content: Dict[str, Any]
    statistics: SummarizationStatistics
    strategy_used: SummarizationStrategy
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.strategy_used, str):
            self.strategy_used = SummarizationStrategy(self.strategy_used)


# ============================================================================
# Helper Functions
# ============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text length.
    Simple heuristic: ~4 characters per token for English/Chinese mixed text.
    """
    return len(text) // 4


def format_preserved_content(
    entities: List[Entity],
    code_blocks: List[CodeBlock],
    urls: List[str]
) -> str:
    """Format preserved content for inclusion in summary"""
    parts = []
    
    if entities:
        entity_texts = [e.text for e in entities]
        parts.append(f"关键信息：{', '.join(entity_texts)}")
    
    if code_blocks:
        for i, block in enumerate(code_blocks, 1):
            lang = block.language or ""
            parts.append(f"代码块 {i}：\n```{lang}\n{block.content}\n```")
    
    if urls:
        parts.append(f"链接：{', '.join(urls)}")
    
    return "\n\n".join(parts)

"""
Content Analyzers for Adaptive Summarization

This module provides analyzers for extracting key information from messages:
- Entity extraction (people, organizations, tech stacks, versions)
- Code block detection (Markdown and inline code)
- URL extraction
- Custom rule matching
"""

import re
from functools import lru_cache
from typing import List, Optional, Tuple
from src.models.adaptive_summarization import (
    Entity, EntityType, CodeBlock, CustomRule, RuleMatch, 
    RuleType, RuleAction, ContentAnalysis, AnalyzersConfig
)


# ============================================================================
# Entity Extractor
# ============================================================================

class EntityExtractor:
    """Extract entities from text using pattern matching and NLP"""
    
    def __init__(self, config: AnalyzersConfig):
        self.config = config
        self.nlp = None
        
        # Technology patterns for common tech stacks
        self.tech_patterns = [
            # Programming languages with versions
            (r'\b(Python)\s*(\d+\.\d+(?:\.\d+)?)\b', EntityType.TECH, EntityType.VERSION),
            (r'\b(Java)\s*(\d+)\b', EntityType.TECH, EntityType.VERSION),
            (r'\b(Node\.?js)\s*v?(\d+\.\d+(?:\.\d+)?)\b', EntityType.TECH, EntityType.VERSION),
            (r'\b(Go)\s*(\d+\.\d+(?:\.\d+)?)\b', EntityType.TECH, EntityType.VERSION),
            
            # Frameworks and libraries
            (r'\b(FastAPI|Django|Flask|Express|React|Vue|Angular|Spring)\b', EntityType.TECH, None),
            
            # Databases
            (r'\b(PostgreSQL|MySQL|MongoDB|Redis|SQLite|Oracle)\s*(\d+(?:\.\d+)?)?', EntityType.TECH, EntityType.VERSION),
            
            # Version numbers standalone
            (r'\bv?(\d+\.\d+(?:\.\d+)?(?:-[a-z]+)?)\b', EntityType.VERSION, None),
            
            # Configuration values
            (r'\b(?:port|端口)[:：\s]+(\d+)\b', EntityType.CONFIG, None),
            (r'\b(?:timeout|超时)[:：\s]+(\d+)\s*(?:s|秒|seconds?)?', EntityType.CONFIG, None),
        ]
        
        # Try to load spaCy model if available
        if config.entity_extraction_enabled:
            try:
                import spacy
                self.nlp = spacy.load("zh_core_web_sm")
            except (ImportError, OSError):
                # spaCy not installed or model not downloaded
                # Fall back to pattern-based extraction only
                pass
    
    def extract(self, text: str) -> List[Entity]:
        """Extract entities from text"""
        if not self.config.entity_extraction_enabled:
            return []
        
        entities = []
        
        # Use spaCy if available
        if self.nlp:
            entities.extend(self._extract_with_spacy(text))
        
        # Always use pattern-based extraction for tech stacks
        entities.extend(self._extract_with_patterns(text))
        
        # Deduplicate entities
        entities = self._deduplicate_entities(entities)
        
        # Filter by configured entity types
        entities = [
            e for e in entities 
            if e.type in self.config.entity_types
        ]
        
        return entities
    
    def _extract_with_spacy(self, text: str) -> List[Entity]:
        """Extract entities using spaCy NLP"""
        if not self.nlp:
            return []
        
        # Use cache if enabled
        if self.config.entity_cache_enabled:
            return list(self._extract_with_spacy_cached(text))
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            # Map spaCy labels to our EntityType
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                entities.append(Entity(
                    text=ent.text,
                    type=entity_type,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0
                ))
        
        return entities
    
    @lru_cache(maxsize=1000)
    def _extract_with_spacy_cached(self, text: str) -> Tuple[Entity, ...]:
        """Cached version of spaCy extraction"""
        return tuple(self._extract_with_spacy(text))
    
    def _extract_with_patterns(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns"""
        entities = []
        
        for pattern, primary_type, secondary_type in self.tech_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Primary entity (e.g., "Python")
                if match.lastindex >= 1:
                    entities.append(Entity(
                        text=match.group(1) if match.lastindex >= 1 else match.group(0),
                        type=primary_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9
                    ))
                
                # Secondary entity (e.g., version "3.11")
                if secondary_type and match.lastindex >= 2 and match.group(2):
                    entities.append(Entity(
                        text=match.group(2),
                        type=secondary_type,
                        start=match.start(2),
                        end=match.end(2),
                        confidence=0.9
                    ))
        
        return entities
    
    def _map_spacy_label(self, label: str) -> Optional[EntityType]:
        """Map spaCy entity label to our EntityType"""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORG,
            "GPE": EntityType.GPE,
            "PRODUCT": EntityType.PRODUCT,
        }
        return mapping.get(label)
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities based on text and position"""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.text.lower(), entity.start, entity.end)
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique


# ============================================================================
# Code Block Detector
# ============================================================================

class CodeBlockDetector:
    """Detect code blocks in Markdown text"""
    
    def __init__(self, config: AnalyzersConfig):
        self.config = config
        
        # Markdown code block pattern: ```language\ncode\n```
        self.code_block_pattern = r'```([\w]*)\n(.*?)\n```'
        
        # Inline code pattern: `code`
        self.inline_code_pattern = r'`([^`]+)`'
    
    def detect(self, text: str) -> List[CodeBlock]:
        """Detect all code blocks in text"""
        if not self.config.code_detection_enabled:
            return []
        
        code_blocks = []
        
        # Detect Markdown code blocks
        code_blocks.extend(self._detect_markdown_blocks(text))
        
        # Detect inline code if enabled
        if self.config.preserve_inline_code:
            code_blocks.extend(self._detect_inline_code(text))
        
        return code_blocks
    
    def _detect_markdown_blocks(self, text: str) -> List[CodeBlock]:
        """Detect Markdown code blocks (```...```)"""
        blocks = []
        
        for match in re.finditer(self.code_block_pattern, text, re.DOTALL):
            language = match.group(1) or None
            content = match.group(2)
            
            # Check line count
            line_count = len(content.split('\n'))
            if line_count < self.config.code_min_lines:
                continue
            
            # Truncate if too long
            if line_count > self.config.code_max_lines:
                lines = content.split('\n')[:self.config.code_max_lines]
                content = '\n'.join(lines) + '\n... [TRUNCATED]'
            
            blocks.append(CodeBlock(
                content=content,
                language=language,
                start=match.start(),
                end=match.end(),
                is_inline=False
            ))
        
        return blocks
    
    def _detect_inline_code(self, text: str) -> List[CodeBlock]:
        """Detect inline code (`...`)"""
        blocks = []
        
        for match in re.finditer(self.inline_code_pattern, text):
            content = match.group(1)
            
            blocks.append(CodeBlock(
                content=content,
                language=None,
                start=match.start(),
                end=match.end(),
                is_inline=True
            ))
        
        return blocks


# ============================================================================
# URL Extractor
# ============================================================================

class URLExtractor:
    """Extract URLs from text"""
    
    def __init__(self, config: AnalyzersConfig):
        self.config = config
        
        # URL pattern (HTTP/HTTPS)
        self.url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    
    def extract(self, text: str) -> List[str]:
        """Extract all URLs from text"""
        if not self.config.url_extraction_enabled:
            return []
        
        urls = re.findall(self.url_pattern, text)
        
        # Deduplicate
        urls = list(dict.fromkeys(urls))
        
        # Verify if enabled
        if self.config.url_verify_alive:
            urls = self._verify_urls(urls)
        
        # Shorten if enabled
        if self.config.url_shorten:
            urls = [self._shorten_url(url) for url in urls]
        
        return urls
    
    def _verify_urls(self, urls: List[str]) -> List[str]:
        """Verify that URLs are accessible (placeholder)"""
        # TODO: Implement actual URL verification
        # For now, just return all URLs
        return urls
    
    def _shorten_url(self, url: str, max_length: int = 50) -> str:
        """Shorten URL for display"""
        if len(url) <= max_length:
            return url
        
        # Keep protocol and domain, truncate path
        parts = url.split('/', 3)
        if len(parts) >= 4:
            return f"{parts[0]}//{parts[2]}/.../{parts[3][-20:]}"
        return url[:max_length] + "..."


# ============================================================================
# Custom Rule Matcher
# ============================================================================

class CustomRuleMatcher:
    """Match custom preservation rules"""
    
    def __init__(self, rules: List[CustomRule]):
        self.rules = rules
        
        # Compile regex patterns
        self.compiled_patterns = {}
        for rule in rules:
            if rule.type == RuleType.REGEX and rule.pattern:
                try:
                    self.compiled_patterns[id(rule)] = re.compile(rule.pattern)
                except re.error as e:
                    # Invalid regex, skip this rule
                    print(f"Warning: Invalid regex pattern '{rule.pattern}': {e}")
    
    def match(self, text: str) -> List[RuleMatch]:
        """Match all rules against text"""
        matches = []
        
        for rule in self.rules:
            if rule.type == RuleType.REGEX:
                matches.extend(self._match_regex(text, rule))
            elif rule.type == RuleType.KEYWORD:
                matches.extend(self._match_keywords(text, rule))
            elif rule.type == RuleType.STRUCTURE:
                matches.extend(self._match_structure(text, rule))
        
        return matches
    
    def _match_regex(self, text: str, rule: CustomRule) -> List[RuleMatch]:
        """Match regex pattern"""
        pattern = self.compiled_patterns.get(id(rule))
        if not pattern:
            return []
        
        matches = []
        for match in pattern.finditer(text):
            matches.append(RuleMatch(
                rule=rule,
                matched_text=match.group(0),
                start=match.start(),
                end=match.end()
            ))
        
        return matches
    
    def _match_keywords(self, text: str, rule: CustomRule) -> List[RuleMatch]:
        """Match keywords"""
        if not rule.keywords:
            return []
        
        matches = []
        text_lower = text.lower()
        
        for keyword in rule.keywords:
            keyword_lower = keyword.lower()
            start = 0
            while True:
                pos = text_lower.find(keyword_lower, start)
                if pos == -1:
                    break
                
                matches.append(RuleMatch(
                    rule=rule,
                    matched_text=text[pos:pos+len(keyword)],
                    start=pos,
                    end=pos+len(keyword)
                ))
                start = pos + len(keyword)
        
        return matches
    
    def _match_structure(self, text: str, rule: CustomRule) -> List[RuleMatch]:
        """Match structured content (JSON, tables, etc.)"""
        # TODO: Implement structure matching
        # For now, return empty list
        return []


# ============================================================================
# Content Analyzers Coordinator
# ============================================================================

class ContentAnalyzers:
    """Coordinate all content analyzers"""
    
    def __init__(self, config: AnalyzersConfig, custom_rules: List[CustomRule]):
        self.config = config
        self.entity_extractor = EntityExtractor(config)
        self.code_detector = CodeBlockDetector(config)
        self.url_extractor = URLExtractor(config)
        self.rule_matcher = CustomRuleMatcher(custom_rules)
    
    def analyze(self, text: str) -> ContentAnalysis:
        """Perform complete content analysis"""
        # Extract all content types
        entities = self.entity_extractor.extract(text)
        code_blocks = self.code_detector.detect(text)
        urls = self.url_extractor.extract(text)
        rule_matches = self.rule_matcher.match(text)
        
        # Detect content characteristics
        has_important_marker = self._detect_important_marker(text)
        is_question = self._detect_question(text)
        is_answer = self._detect_answer(text)
        
        return ContentAnalysis(
            entities=entities,
            code_blocks=code_blocks,
            urls=urls,
            rule_matches=rule_matches,
            has_entities=len(entities) > 0,
            has_code=len(code_blocks) > 0,
            has_urls=len(urls) > 0,
            has_important_marker=has_important_marker,
            is_question=is_question,
            is_answer=is_answer
        )
    
    def _detect_important_marker(self, text: str) -> bool:
        """Detect if text is marked as important"""
        markers = [
            r'\[重要\]',
            r'\[IMPORTANT\]',
            r'\[!!\]',
            r'⚠️',
            r'❗'
        ]
        
        for marker in markers:
            if re.search(marker, text, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_question(self, text: str) -> bool:
        """Detect if text is a question"""
        # Check for question marks
        if '?' in text or '？' in text:
            return True
        
        # Check for question words
        question_words = [
            r'\b(what|how|why|when|where|who|which|whose|whom)\b',
            r'\b(什么|怎么|为什么|何时|哪里|谁|哪个)\b'
        ]
        
        for pattern in question_words:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_answer(self, text: str) -> bool:
        """Detect if text is an answer"""
        # Simple heuristic: longer text from assistant is likely an answer
        # This should be refined based on role in actual usage
        return len(text) > 50

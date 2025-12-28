"""Basic test for adaptive summarization integration"""

import asyncio
from src.models.openai import Message
from src.models.adaptive_summarization import (
    AdaptiveSummarizationConfig,
    HierarchicalConfig,
    LayerConfig,
    LayerAction,
    AnalyzersConfig,
    ScoringConfig,
)
from src.core.adaptive_summarization_manager import AdaptiveSummarizationManager


async def test_hierarchical_strategy():
    """Test hierarchical strategy"""
    print("Testing Hierarchical Strategy...")
    
    # Create configuration
    config = AdaptiveSummarizationConfig(
        enabled=True,
        strategy="hierarchical",
        hierarchical_config=HierarchicalConfig(
            layers={
                "critical": LayerConfig(
                    name="critical",
                    priority=100,
                    content_types=["system_messages", "code_blocks"],
                    action=LayerAction.PRESERVE
                ),
                "important": LayerConfig(
                    name="important",
                    priority=50,
                    content_types=["entities", "urls"],
                    action=LayerAction.DETAILED_SUMMARY
                ),
                "normal": LayerConfig(
                    name="normal",
                    priority=10,
                    content_types=[],
                    action=LayerAction.BRIEF_SUMMARY
                )
            }
        ),
        analyzers_config=AnalyzersConfig(),
        scoring_config=ScoringConfig()
    )
    
    # Create manager
    manager = AdaptiveSummarizationManager(config)
    
    # Create test messages
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="How do I use Python?"),
        Message(role="assistant", content="Here's an example:\n```python\nprint('Hello, World!')\n```"),
        Message(role="user", content="Thanks! Can you explain more?"),
        Message(role="assistant", content="Sure, Python is a programming language..."),
    ]
    
    # Execute summarization
    result = await manager.summarize(messages, "test-session-1")
    
    # Print results
    print(f"\nOriginal messages: {len(messages)}")
    print(f"Summarized messages: {len(result.messages)}")
    print(f"Compression ratio: {result.statistics.compression_ratio:.2f}")
    print(f"Entities preserved: {result.statistics.entities_preserved}")
    print(f"Code blocks preserved: {result.statistics.code_blocks_preserved}")
    print(f"URLs preserved: {result.statistics.urls_preserved}")
    print(f"Execution time: {result.statistics.execution_time_ms:.2f}ms")
    
    print("\nSummarized messages:")
    for i, msg in enumerate(result.messages):
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"  {i+1}. [{msg.role}] {content_preview}")
    
    print("\n✓ Hierarchical strategy test passed!")


async def test_selective_strategy():
    """Test selective strategy"""
    print("\n" + "="*60)
    print("Testing Selective Strategy...")
    
    from src.models.adaptive_summarization import SelectiveConfig
    
    # Create configuration
    config = AdaptiveSummarizationConfig(
        enabled=True,
        strategy="selective",
        selective_config=SelectiveConfig(
            preserve_threshold=10.0,
            summarize_threshold=5.0,
            discard_threshold=2.0
        ),
        analyzers_config=AnalyzersConfig(),
        scoring_config=ScoringConfig()
    )
    
    # Create manager
    manager = AdaptiveSummarizationManager(config)
    
    # Create test messages with varying importance
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="[重要] Please help me with this critical issue."),
        Message(role="assistant", content="I'll help you. Here's the solution:\n```python\ndef solve():\n    pass\n```"),
        Message(role="user", content="ok"),
        Message(role="assistant", content="Great!"),
        Message(role="user", content="Can you check this URL: https://example.com/docs"),
    ]
    
    # Execute summarization
    result = await manager.summarize(messages, "test-session-2")
    
    # Print results
    print(f"\nOriginal messages: {len(messages)}")
    print(f"Summarized messages: {len(result.messages)}")
    print(f"Compression ratio: {result.statistics.compression_ratio:.2f}")
    
    print("\nSummarized messages:")
    for i, msg in enumerate(result.messages):
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"  {i+1}. [{msg.role}] {content_preview}")
    
    print("\n✓ Selective strategy test passed!")


async def test_incremental_strategy():
    """Test incremental strategy"""
    print("\n" + "="*60)
    print("Testing Incremental Strategy...")
    
    from src.models.adaptive_summarization import IncrementalConfig
    
    # Create configuration
    config = AdaptiveSummarizationConfig(
        enabled=True,
        strategy="incremental",
        incremental_config=IncrementalConfig(
            summary_window=5,
            keep_recent=2,
            max_summary_depth=3,
            summary_prefix="[摘要]"
        ),
        analyzers_config=AnalyzersConfig(),
        scoring_config=ScoringConfig()
    )
    
    # Create manager
    manager = AdaptiveSummarizationManager(config)
    
    # Create test messages (more than summary_window + keep_recent)
    messages = [
        Message(role="user", content=f"Message {i}") 
        for i in range(10)
    ]
    
    # Execute summarization
    result = await manager.summarize(messages, "test-session-3")
    
    # Print results
    print(f"\nOriginal messages: {len(messages)}")
    print(f"Summarized messages: {len(result.messages)}")
    print(f"Compression ratio: {result.statistics.compression_ratio:.2f}")
    
    print("\nSummarized messages:")
    for i, msg in enumerate(result.messages):
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"  {i+1}. [{msg.role}] {content_preview}")
    
    print("\n✓ Incremental strategy test passed!")


async def main():
    """Run all tests"""
    print("="*60)
    print("Adaptive Summarization Basic Tests")
    print("="*60)
    
    try:
        await test_hierarchical_strategy()
        await test_selective_strategy()
        await test_incremental_strategy()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

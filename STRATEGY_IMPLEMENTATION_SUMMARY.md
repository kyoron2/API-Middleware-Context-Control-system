# 自适应摘要策略实现总结

## 已完成任务

### Task 5: 层次化摘要策略 (Hierarchical Strategy)
**文件**: `src/core/strategies/hierarchical_strategy.py`

**核心功能**:
- 根据内容类型将消息分类到不同层次（关键/重要/一般）
- 支持四种处理动作：
  - `PRESERVE`: 完整保留消息
  - `DETAILED_SUMMARY`: 创建详细摘要（包含实体、代码块、URL信息）
  - `BRIEF_SUMMARY`: 创建简要摘要
  - `DISCARD`: 丢弃消息

**分类逻辑**:
- 系统消息：+100分
- 实体：每个+10分
- 代码块：每个+15分
- URL：每个+5分
- 重要标记：+50分
- 问题/答案：+20分
- 自定义保留规则：每个+30分

**特性**:
- 支持每层配置最大token限制
- 自动截断超长消息
- 提供层次统计功能

---

### Task 6: 增量摘要策略 (Incremental Strategy)
**文件**: `src/core/strategies/incremental_strategy.py`

**核心功能**:
- 维护会话级别的摘要状态
- 在历史摘要基础上累积新消息
- 保留最近N条完整消息
- 达到最大深度时自动重置

**状态管理**:
- 跟踪摘要深度（防止无限嵌套）
- 记录已摘要的消息数量
- 支持会话隔离

**触发条件**:
- 首次：消息数 > summary_window + keep_recent
- 后续：新消息数 >= summary_window

**配置参数**:
- `summary_window`: 每N轮触发摘要（默认10）
- `keep_recent`: 保留最近N轮完整对话（默认5）
- `max_summary_depth`: 最多N层嵌套摘要（默认3）
- `summary_prefix`: 摘要前缀（默认"[摘要]"）

---

### Task 7: 选择性摘要策略 (Selective Strategy)
**文件**: `src/core/strategies/selective_strategy.py`

**核心功能**:
- 基于重要性评分决定消息处理方式
- 使用ImportanceScorer计算每条消息的分数
- 根据阈值自动分类

**阈值逻辑**:
- `score >= preserve_threshold`: 完整保留
- `summarize_threshold <= score < preserve_threshold`: 创建摘要
- `discard_threshold <= score < summarize_threshold`: 低优先级摘要
- `score < discard_threshold`: 丢弃

**摘要内容**:
- 高分消息：150字符预览 + 详细元数据
- 低分消息：50字符预览 + 基本元数据

**实用工具**:
- `get_score_distribution()`: 获取消息分布统计
- `get_top_messages()`: 获取Top-K重要消息
- `get_score_statistics()`: 获取评分统计（min/max/mean/median）

---

## 技术实现细节

### 1. 消息分析流程
所有策略都使用 `ContentAnalyzers` 进行内容分析：
```python
analysis = self.analyzers.analyze(message.content)
# 返回: ContentAnalysis(entities, code_blocks, urls, rule_matches, ...)
```

### 2. Token估算
使用简单估算：1 token ≈ 4 characters
```python
def _estimate_tokens(self, text: str) -> int:
    return len(text) // 4
```

### 3. 异步支持
所有策略的 `apply()` 方法都是异步的：
```python
async def apply(self, messages: List[Message]) -> List[Message]:
    # 处理逻辑
```

### 4. 配置验证
每个策略在初始化时验证配置：
- HierarchicalStrategy: 检查层次配置和优先级唯一性
- IncrementalStrategy: 无需特殊验证
- SelectiveStrategy: 验证阈值顺序（discard <= summarize <= preserve）

---

## 集成要点

### 下一步工作 (Task 9)
需要创建 `AdaptiveSummarizationManager` 来协调这三个策略：

```python
class AdaptiveSummarizationManager:
    def __init__(self, config: AdaptiveSummarizationConfig):
        self.config = config
        self.analyzers = ContentAnalyzers(config.analyzers_config)
        self.scorer = ImportanceScorer(config.scoring_config)
        
        # 初始化策略
        self.strategies = {
            "hierarchical": HierarchicalStrategy(
                config.hierarchical_config, 
                self.analyzers
            ),
            "incremental": IncrementalStrategy(
                config.incremental_config
            ),
            "selective": SelectiveStrategy(
                config.selective_config,
                self.scorer,
                self.analyzers
            )
        }
    
    async def summarize(
        self,
        messages: List[Message],
        strategy: str,
        session_id: str
    ) -> SummarizationResult:
        # 选择并应用策略
        # 应用内容保留规则
        # 生成统计信息
        pass
```

### 集成到 ContextManager (Task 10)
在 `src/core/context_manager.py` 中添加新策略：

```python
class AdaptiveSummarizationStrategy(ContextStrategy):
    def __init__(self, manager: AdaptiveSummarizationManager):
        self.manager = manager
    
    async def reduce(
        self,
        messages: List[Message],
        config: ContextConfig
    ) -> Tuple[List[Message], Optional[str]]:
        result = await self.manager.summarize(
            messages,
            config.adaptive_summarization.strategy,
            session_id
        )
        return result.messages, result.summary
```

---

## 测试建议

### 单元测试
1. 测试消息分类逻辑（HierarchicalStrategy）
2. 测试状态管理（IncrementalStrategy）
3. 测试阈值逻辑（SelectiveStrategy）

### 集成测试
1. 创建包含各种内容的测试消息
2. 验证每个策略的输出
3. 检查压缩率和信息保留

### 示例测试用例
```python
# 测试层次化策略
messages = [
    Message(role="system", content="System prompt"),
    Message(role="user", content="How to use Python?"),
    Message(role="assistant", content="```python\nprint('hello')\n```"),
]

strategy = HierarchicalStrategy(config, analyzers)
result = await strategy.apply(messages)

# 验证系统消息被保留
assert any(msg.role == "system" for msg in result)
# 验证代码块被识别
assert "Code:" in result[2].content or result[2].content.startswith("```")
```

---

## 性能考虑

1. **内容分析缓存**: ContentAnalyzers 已实现 LRU 缓存
2. **批量处理**: 所有策略支持批量处理消息
3. **异步执行**: 使用 async/await 避免阻塞
4. **内存管理**: IncrementalStrategy 使用字典存储会话状态，需要定期清理

---

## 配置示例

```yaml
context:
  reduction_mode: adaptive_summarization
  adaptive_summarization:
    enabled: true
    strategy: hierarchical  # or incremental, selective
    
    # 内容保留
    preserve_entities: true
    preserve_code: true
    preserve_urls: true
    
    # 层次化配置
    hierarchical_config:
      layers:
        critical:
          priority: 100
          content_types: [system_messages, code_blocks, important_markers]
          action: preserve
        important:
          priority: 50
          content_types: [entities, urls, questions]
          action: detailed_summary
        normal:
          priority: 10
          content_types: []
          action: brief_summary
    
    # 增量配置
    incremental_config:
      summary_window: 10
      keep_recent: 5
      max_summary_depth: 3
    
    # 选择性配置
    selective_config:
      preserve_threshold: 10.0
      summarize_threshold: 5.0
      discard_threshold: 2.0
```

---

## 总结

已成功实现三种自适应摘要策略，每种策略都有独特的优势：

- **Hierarchical**: 适合需要精确控制不同内容类型处理方式的场景
- **Incremental**: 适合长对话，保持历史连贯性
- **Selective**: 适合需要自动识别重要内容的场景

所有代码已通过语法检查，无错误。下一步需要实现 AdaptiveSummarizationManager 来协调这些策略。

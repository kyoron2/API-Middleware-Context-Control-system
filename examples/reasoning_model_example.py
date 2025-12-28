"""
示例：使用思考模型（DeepSeek-R1、OpenAI o1 等）

这个示例展示如何处理思考模型的流式输出，
包括思考过程（reasoning_content）和最终答案（content）
"""

import asyncio
import httpx
import json
from typing import Optional


class ReasoningModelClient:
    """思考模型客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def chat_with_reasoning(
        self,
        model: str,
        message: str,
        show_reasoning: bool = True
    ):
        """
        与思考模型对话
        
        Args:
            model: 模型名称（如 "deepseek/deepseek-reasoner"）
            message: 用户消息
            show_reasoning: 是否显示思考过程
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": True,
            "temperature": 0.7
        }
        
        print(f"🤔 向 {model} 提问: {message}\n")
        print("=" * 60)
        
        reasoning_content = ""
        answer_content = ""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"❌ 错误: {response.status_code}")
                    print(await response.aread())
                    return
                
                # 显示思考过程（如果启用）
                if show_reasoning:
                    print("💭 思考过程:")
                    print("-" * 60)
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        if data.strip() == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            
                            if not chunk.get("choices"):
                                continue
                            
                            delta = chunk["choices"][0].get("delta", {})
                            
                            # 处理思考内容
                            if delta.get("reasoning_content"):
                                reasoning_text = delta["reasoning_content"]
                                reasoning_content += reasoning_text
                                if show_reasoning:
                                    print(f"\033[90m{reasoning_text}\033[0m", end="", flush=True)
                            
                            # 处理 thinking 字段（OpenAI o1 风格）
                            if delta.get("thinking"):
                                thinking_text = delta["thinking"]
                                reasoning_content += thinking_text
                                if show_reasoning:
                                    print(f"\033[90m{thinking_text}\033[0m", end="", flush=True)
                            
                            # 处理最终答案
                            if delta.get("content"):
                                answer_text = delta["content"]
                                answer_content += answer_text
                                
                                # 如果是第一次输出答案，先换行
                                if not answer_content[:-len(answer_text)] and show_reasoning:
                                    print("\n" + "-" * 60)
                                    print("✅ 最终答案:")
                                    print("-" * 60)
                                
                                print(answer_text, end="", flush=True)
                        
                        except json.JSONDecodeError as e:
                            print(f"\n⚠️  解析错误: {e}")
                            continue
        
        print("\n" + "=" * 60)
        print(f"\n📊 统计:")
        print(f"  思考内容长度: {len(reasoning_content)} 字符")
        print(f"  答案内容长度: {len(answer_content)} 字符")
        print(f"  总长度: {len(reasoning_content) + len(answer_content)} 字符")


async def example_1_show_reasoning():
    """示例 1: 显示思考过程"""
    print("\n" + "=" * 60)
    print("示例 1: 显示思考过程")
    print("=" * 60 + "\n")
    
    client = ReasoningModelClient()
    await client.chat_with_reasoning(
        model="deepseek/deepseek-reasoner",
        message="计算 123 * 456 的结果",
        show_reasoning=True
    )


async def example_2_hide_reasoning():
    """示例 2: 只显示最终答案"""
    print("\n" + "=" * 60)
    print("示例 2: 只显示最终答案")
    print("=" * 60 + "\n")
    
    client = ReasoningModelClient()
    await client.chat_with_reasoning(
        model="deepseek/deepseek-reasoner",
        message="什么是量子计算？",
        show_reasoning=False
    )


async def example_3_complex_reasoning():
    """示例 3: 复杂推理问题"""
    print("\n" + "=" * 60)
    print("示例 3: 复杂推理问题")
    print("=" * 60 + "\n")
    
    client = ReasoningModelClient()
    await client.chat_with_reasoning(
        model="deepseek/deepseek-reasoner",
        message="如果一个房间里有 3 只猫，每只猫抓到 2 只老鼠，但有 1 只老鼠逃跑了，房间里还有多少只老鼠？",
        show_reasoning=True
    )


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("思考模型流式传输示例")
    print("=" * 60)
    
    try:
        # 运行示例
        await example_1_show_reasoning()
        
        # 等待用户确认
        input("\n按 Enter 继续下一个示例...")
        
        await example_2_hide_reasoning()
        
        input("\n按 Enter 继续下一个示例...")
        
        await example_3_complex_reasoning()
        
        print("\n✅ 所有示例完成！")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         思考模型流式传输示例                              ║
    ║                                                          ║
    ║  本示例展示如何使用 API 中间件处理思考模型的输出          ║
    ║  支持的模型：                                            ║
    ║    - DeepSeek-R1 (reasoning_content)                    ║
    ║    - OpenAI o1 (thinking)                               ║
    ║    - 其他思考模型                                        ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())

"""Test streaming functionality"""

import asyncio
import httpx
import json


async def test_streaming():
    """Test streaming chat completion"""
    
    url = "http://localhost:8000/v1/chat/completions"
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "user", "content": "请用一句话介绍Python编程语言"}
        ],
        "stream": True,
        "temperature": 0.7
    }
    
    print("Testing streaming response...")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print("-" * 50)
            
            full_content = ""
            chunk_count = 0
            
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data.strip() == "[DONE]":
                        print("\n[DONE]")
                        break
                    
                    try:
                        chunk = json.loads(data)
                        chunk_count += 1
                        
                        # Extract content from delta
                        if chunk.get("choices"):
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                print(content, end="", flush=True)
                                full_content += content
                    
                    except json.JSONDecodeError as e:
                        print(f"\nError parsing chunk: {e}")
                        print(f"Data: {data}")
            
            print("\n" + "-" * 50)
            print(f"Total chunks: {chunk_count}")
            print(f"Full content length: {len(full_content)}")
            print(f"Full content: {full_content}")


async def test_non_streaming():
    """Test non-streaming chat completion for comparison"""
    
    url = "http://localhost:8000/v1/chat/completions"
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "user", "content": "请用一句话介绍Python编程语言"}
        ],
        "stream": False,
        "temperature": 0.7
    }
    
    print("\nTesting non-streaming response...")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"Error: {response.text}")


async def main():
    """Run all tests"""
    try:
        # Test streaming
        await test_streaming()
        
        # Test non-streaming
        await test_non_streaming()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

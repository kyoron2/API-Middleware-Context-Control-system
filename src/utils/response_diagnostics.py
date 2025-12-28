"""Response diagnostics utilities for analyzing LLM responses"""

from typing import Dict, Any, List, Tuple, Optional
from enum import Enum


class ResponseType(Enum):
    """响应类型枚举"""
    TEXT_ONLY = "text_only"              # 仅包含文本内容
    TOOL_CALLS_ONLY = "tool_calls_only"  # 仅包含工具调用
    MIXED = "mixed"                       # 同时包含文本和工具调用
    EMPTY = "empty"                       # 空响应或缺失关键字段


class ResponseDiagnostics:
    """响应诊断工具类"""
    
    @staticmethod
    def classify_response(response_data: Dict[str, Any]) -> ResponseType:
        """
        分类响应类型
        
        Args:
            response_data: 原始响应数据字典
            
        Returns:
            ResponseType 枚举值
        """
        # 检查响应结构的基本完整性
        if not isinstance(response_data, dict):
            return ResponseType.EMPTY
        
        choices = response_data.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            return ResponseType.EMPTY
        
        # 获取第一个 choice 的 message
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ResponseType.EMPTY
        
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return ResponseType.EMPTY
        
        # 检查 content 和 tool_calls
        content = message.get("content")
        tool_calls = message.get("tool_calls")
        
        # 判断 content 是否有效（非空字符串）
        has_content = bool(content and isinstance(content, str) and content.strip())
        
        # 判断 tool_calls 是否有效（非空数组）
        has_tool_calls = bool(
            tool_calls and 
            isinstance(tool_calls, list) and 
            len(tool_calls) > 0
        )
        
        # 根据内容分类
        if has_content and has_tool_calls:
            return ResponseType.MIXED
        elif has_content:
            return ResponseType.TEXT_ONLY
        elif has_tool_calls:
            return ResponseType.TOOL_CALLS_ONLY
        else:
            return ResponseType.EMPTY
    
    @staticmethod
    def validate_response_structure(
        response_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        验证响应结构完整性
        
        Args:
            response_data: 原始响应数据字典
            
        Returns:
            (is_valid, missing_fields) 元组
        """
        missing_fields = []
        
        # 检查基本类型
        if not isinstance(response_data, dict):
            return False, ["response_data (not a dict)"]
        
        # 检查必需的顶层字段
        required_top_fields = ["id", "object", "created", "model", "choices"]
        for field in required_top_fields:
            if field not in response_data:
                missing_fields.append(field)
        
        # 检查 choices 数组
        choices = response_data.get("choices")
        if not choices:
            missing_fields.append("choices")
        elif not isinstance(choices, list):
            missing_fields.append("choices (not a list)")
        elif len(choices) == 0:
            missing_fields.append("choices (empty list)")
        else:
            # 检查第一个 choice 的结构
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                missing_fields.append("choices[0] (not a dict)")
            else:
                # 检查 choice 的必需字段
                if "index" not in first_choice:
                    missing_fields.append("choices[0].index")
                if "message" not in first_choice:
                    missing_fields.append("choices[0].message")
                else:
                    # 检查 message 结构
                    message = first_choice["message"]
                    if not isinstance(message, dict):
                        missing_fields.append("choices[0].message (not a dict)")
                    else:
                        if "role" not in message:
                            missing_fields.append("choices[0].message.role")
                        
                        # content 和 tool_calls 至少要有一个
                        has_content = "content" in message and message["content"]
                        has_tool_calls = "tool_calls" in message and message["tool_calls"]
                        
                        if not has_content and not has_tool_calls:
                            missing_fields.append("choices[0].message.content or tool_calls")
        
        # 检查 usage 字段（虽然不是严格必需，但通常应该存在）
        if "usage" not in response_data:
            missing_fields.append("usage (optional but recommended)")
        
        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields
    
    @staticmethod
    def extract_response_content(
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提取响应关键内容用于日志记录
        
        Args:
            response_data: 原始响应数据字典
            
        Returns:
            包含 content, tool_calls, role 等关键字段的字典
        """
        extracted = {
            "has_choices": False,
            "choices_count": 0,
            "message": None,
            "content": None,
            "tool_calls": None,
            "role": None,
            "finish_reason": None,
        }
        
        if not isinstance(response_data, dict):
            return extracted
        
        choices = response_data.get("choices")
        if not choices or not isinstance(choices, list):
            return extracted
        
        extracted["has_choices"] = True
        extracted["choices_count"] = len(choices)
        
        if len(choices) == 0:
            return extracted
        
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return extracted
        
        # 提取 finish_reason
        extracted["finish_reason"] = first_choice.get("finish_reason")
        
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return extracted
        
        extracted["message"] = message
        extracted["role"] = message.get("role")
        extracted["content"] = message.get("content")
        extracted["tool_calls"] = message.get("tool_calls")
        
        return extracted
    
    @staticmethod
    def truncate_for_logging(
        content: str,
        max_length: int = 2000
    ) -> str:
        """
        截断内容用于日志记录
        
        Args:
            content: 原始内容
            max_length: 最大长度
            
        Returns:
            截断后的内容（如果需要会添加 [TRUNCATED] 标记）
        """
        if not isinstance(content, str):
            return str(content)
        
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + " [TRUNCATED]"

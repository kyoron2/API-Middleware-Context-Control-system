"""Session and context management data models"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .openai import Message


class ContextConfig(BaseModel):
    """Configuration for context management"""
    max_turns: int = Field(default=10, ge=1)
    max_tokens: int = Field(default=4000, ge=100)
    reduction_mode: str = Field(default="truncation")  # "truncation", "summarization", "sliding_window"
    summarization_model: Optional[str] = None
    preserve_system_message: bool = True
    memory_zone_enabled: bool = True

    class Config:
        validate_assignment = True


class SessionState(BaseModel):
    """Session state data"""
    active_messages: List[Message] = Field(default_factory=list)
    memory_zone: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "active_messages": [msg.model_dump() for msg in self.active_messages],
            "memory_zone": self.memory_zone,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Create from dictionary"""
        return cls(
            active_messages=[Message(**msg) for msg in data.get("active_messages", [])],
            memory_zone=data.get("memory_zone", []),
            metadata=data.get("metadata", {})
        )


class Session(BaseModel):
    """Session model"""
    session_id: str
    user_id: str
    conversation_history: List[Message] = Field(default_factory=list)
    memory_zone: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    total_tokens_used: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_history": [msg.model_dump() for msg in self.conversation_history],
            "memory_zone": self.memory_zone,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_tokens_used": self.total_tokens_used
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            conversation_history=[Message(**msg) for msg in data.get("conversation_history", [])],
            memory_zone=data.get("memory_zone", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            total_tokens_used=data.get("total_tokens_used", 0)
        )

    class Config:
        validate_assignment = True


class ConversationHistory(BaseModel):
    """Conversation history with token tracking"""
    messages: List[Message] = Field(default_factory=list)
    total_tokens: int = 0

    def add_message(self, message: Message) -> None:
        """Add a message to history"""
        self.messages.append(message)
        # Rough token estimation: 1 token ≈ 4 characters
        self.total_tokens += len(message.content) // 4

    def get_recent(self, n: int) -> List[Message]:
        """Get the n most recent messages"""
        return self.messages[-n:] if n > 0 else []

    def estimate_tokens(self) -> int:
        """Estimate total tokens in conversation"""
        total = 0
        for msg in self.messages:
            # Rough estimation: 1 token ≈ 4 characters
            total += len(msg.content) // 4
        return total

    class Config:
        validate_assignment = True

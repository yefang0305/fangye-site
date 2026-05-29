"""Abstract base for platform-specific private-message readers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    account_id: int
    account_name: str
    conversation_id: str
    user_name: str
    user_avatar_url: str
    preview: str
    timestamp_str: str
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def key(self) -> str:
        return f"{self.account_id}_{self.conversation_id}"


@dataclass
class ChatMessage:
    sender: str
    text: str
    timestamp_str: str = ""


class MessageReader(ABC):
    platform: str = ""

    @abstractmethod
    def fetch_unread_strangers(
        self,
        account_id: int,
        account_name: str,
        profile_path: str,
    ) -> list[Message]:
        """Open a browser profile and scrape unread stranger messages.

        Implementations should handle platform/page errors internally and
        return an empty list when a fetch cannot be completed.
        """

    @abstractmethod
    def reply(self, profile_path: str, conversation_id: str, text: str) -> tuple[bool, str]:
        """Send a manual reply.

        Returns (success, error_msg). error_msg is an empty string on success.
        """

    @abstractmethod
    def fetch_conversation_messages(self, profile_path: str, conversation_id: str) -> list[ChatMessage]:
        """Read the visible history of one conversation."""

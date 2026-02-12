from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict

from data_pipeline.messaging.schema import EtlMessage


class MessageBroker(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: EtlMessage) -> None:
        raise NotImplementedError


class InMemoryMessageBroker(MessageBroker):
    def __init__(self) -> None:
        self.published: dict[str, list[EtlMessage]] = defaultdict(list)

    async def publish(self, topic: str, message: EtlMessage) -> None:
        self.published[topic].append(message)


from typing import Any, Protocol


class Queue(Protocol):
    async def publish(self, payload: dict[str, Any]) -> None: ...


class InlineQueue:
    async def publish(self, payload: dict[str, Any]) -> None:
        return None


class KafkaQueue:
    def __init__(self, bootstrap_servers: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic

    async def publish(self, payload: dict[str, Any]) -> None:
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:
            raise RuntimeError("Install agentsure[kafka] to use QUEUE_MODE=kafka") from exc
        import json
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await producer.start()
        try:
            await producer.send_and_wait(self.topic, json.dumps(payload).encode())
        finally:
            await producer.stop()

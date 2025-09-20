"""
Message Bus for KMS-Google-ADK
Handles inter-agent communication and message routing.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timezone
import asyncio
import logging
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict, deque


class MessageType(Enum):
    """Types of messages in the system."""
    COMMAND = "command"
    EVENT = "event"
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Message:
    """Represents a message in the system."""
    id: str
    type: MessageType
    priority: MessagePriority
    source: str
    target: Optional[str]
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[int] = None  # Time to live in seconds


@dataclass
class Subscription:
    """Represents a message subscription."""
    subscriber_id: str
    topic_pattern: str
    callback: Callable[[Message], None]
    priority: MessagePriority = MessagePriority.NORMAL


class MessageBus:
    """
    Central message bus for inter-agent communication.
    
    Features:
    - Topic-based message routing
    - Priority-based message processing
    - Message persistence and replay
    - Dead letter queue for failed messages
    - Circuit breaker pattern for fault tolerance
    """
    
    def __init__(self, max_queue_size: int = 10000):
        """
        Initialize the message bus.
        
        Args:
            max_queue_size: Maximum size of message queues
        """
        self.max_queue_size = max_queue_size
        self.logger = logging.getLogger(__name__)
        
        # Message queues by priority
        self.queues = {
            priority: deque(maxlen=max_queue_size)
            for priority in MessagePriority
        }
        
        # Subscriptions
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        
        # Message history for replay
        self.message_history: deque = deque(maxlen=1000)
        
        # Dead letter queue
        self.dead_letter_queue: deque = deque(maxlen=1000)
        
        # Circuit breakers for agents
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Processing state
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "subscriptions_active": 0
        }
        
        self.logger.info("Message Bus initialized")
    
    async def start(self):
        """Start the message bus processing."""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.processing_task = asyncio.create_task(self._process_messages())
        self.logger.info("Message Bus started")
    
    async def stop(self):
        """Stop the message bus processing."""
        self.is_processing = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Message Bus stopped")
    
    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.EVENT,
        priority: MessagePriority = MessagePriority.NORMAL,
        source: str = "system",
        target: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> str:
        """
        Publish a message to the bus.
        
        Args:
            topic: Message topic
            payload: Message payload
            message_type: Type of message
            priority: Message priority
            source: Source agent/service
            target: Target agent/service (None for broadcast)
            correlation_id: Correlation ID for request/response
            reply_to: Reply-to address
            ttl: Time to live in seconds
            
        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        
        message = Message(
            id=message_id,
            type=message_type,
            priority=priority,
            source=source,
            target=target,
            topic=topic,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            reply_to=reply_to,
            ttl=ttl
        )
        
        # Add to appropriate queue
        self.queues[priority].append(message)
        
        # Add to history
        self.message_history.append(message)
        
        self.stats["messages_sent"] += 1
        
        self.logger.debug(f"Published message {message_id} to topic {topic}")
        
        return message_id
    
    async def subscribe(
        self,
        subscriber_id: str,
        topic_pattern: str,
        callback: Callable[[Message], None],
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """
        Subscribe to messages matching a topic pattern.
        
        Args:
            subscriber_id: Unique subscriber identifier
            topic_pattern: Topic pattern to match (supports wildcards)
            callback: Callback function to handle messages
            priority: Priority for this subscription
            
        Returns:
            Subscription ID
        """
        subscription = Subscription(
            subscriber_id=subscriber_id,
            topic_pattern=topic_pattern,
            callback=callback,
            priority=priority
        )
        
        self.subscriptions[topic_pattern].append(subscription)
        self.stats["subscriptions_active"] += 1
        
        self.logger.info(f"Subscribed {subscriber_id} to {topic_pattern}")
        
        return f"{subscriber_id}:{topic_pattern}"
    
    async def unsubscribe(self, subscription_id: str):
        """
        Unsubscribe from messages.
        
        Args:
            subscription_id: Subscription ID to remove
        """
        subscriber_id, topic_pattern = subscription_id.split(":", 1)
        
        if topic_pattern in self.subscriptions:
            self.subscriptions[topic_pattern] = [
                sub for sub in self.subscriptions[topic_pattern]
                if sub.subscriber_id != subscriber_id
            ]
            
            if not self.subscriptions[topic_pattern]:
                del self.subscriptions[topic_pattern]
            
            self.stats["subscriptions_active"] -= 1
            self.logger.info(f"Unsubscribed {subscriber_id} from {topic_pattern}")
    
    async def request(
        self,
        topic: str,
        payload: Dict[str, Any],
        source: str,
        target: str,
        timeout: int = 30,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Message]:
        """
        Send a request and wait for response.
        
        Args:
            topic: Request topic
            payload: Request payload
            source: Source agent
            target: Target agent
            timeout: Timeout in seconds
            priority: Message priority
            
        Returns:
            Response message or None if timeout
        """
        correlation_id = str(uuid.uuid4())
        reply_topic = f"reply:{correlation_id}"
        
        # Subscribe to reply
        response_received = asyncio.Event()
        response_message = None
        
        async def reply_handler(message: Message):
            nonlocal response_message
            response_message = message
            response_received.set()
        
        subscription_id = await self.subscribe(
            subscriber_id=f"request:{correlation_id}",
            topic_pattern=reply_topic,
            callback=reply_handler,
            priority=priority
        )
        
        try:
            # Send request
            await self.publish(
                topic=topic,
                payload=payload,
                message_type=MessageType.REQUEST,
                priority=priority,
                source=source,
                target=target,
                correlation_id=correlation_id,
                reply_to=reply_topic
            )
            
            # Wait for response
            try:
                await asyncio.wait_for(response_received.wait(), timeout=timeout)
                return response_message
            except asyncio.TimeoutError:
                self.logger.warning(f"Request timeout for {topic}")
                return None
                
        finally:
            # Clean up subscription
            await self.unsubscribe(subscription_id)
    
    async def _process_messages(self):
        """Process messages from queues."""
        while self.is_processing:
            try:
                # Process messages by priority
                for priority in MessagePriority:
                    if self.queues[priority]:
                        message = self.queues[priority].popleft()
                        await self._handle_message(message)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error processing messages: {str(e)}")
                await asyncio.sleep(0.1)
    
    async def _handle_message(self, message: Message):
        """Handle a single message."""
        try:
            # Check TTL
            if message.ttl:
                age = (datetime.now(timezone.utc) - message.timestamp).total_seconds()
                if age > message.ttl:
                    self.logger.debug(f"Message {message.id} expired")
                    return
            
            # Find matching subscriptions
            matching_subscriptions = []
            for pattern, subscriptions in self.subscriptions.items():
                if self._topic_matches(message.topic, pattern):
                    matching_subscriptions.extend(subscriptions)
            
            if not matching_subscriptions:
                self.logger.debug(f"No subscribers for topic {message.topic}")
                return
            
            # Process subscriptions
            for subscription in matching_subscriptions:
                try:
                    # Check circuit breaker
                    if self._is_circuit_open(subscription.subscriber_id):
                        self.logger.warning(f"Circuit breaker open for {subscription.subscriber_id}")
                        continue
                    
                    # Call subscriber callback
                    if asyncio.iscoroutinefunction(subscription.callback):
                        await subscription.callback(message)
                    else:
                        subscription.callback(message)
                    
                    self.stats["messages_processed"] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error in subscription {subscription.subscriber_id}: {str(e)}")
                    self._record_circuit_failure(subscription.subscriber_id)
                    self.stats["messages_failed"] += 1
                    
                    # Move to dead letter queue
                    self.dead_letter_queue.append({
                        "message": message,
                        "subscription": subscription,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc)
                    })
        
        except Exception as e:
            self.logger.error(f"Error handling message {message.id}: {str(e)}")
            self.stats["messages_failed"] += 1
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if a topic matches a pattern."""
        if pattern == "*":
            return True
        
        if pattern.endswith("*"):
            return topic.startswith(pattern[:-1])
        
        if pattern.startswith("*"):
            return topic.endswith(pattern[1:])
        
        return topic == pattern
    
    def _is_circuit_open(self, subscriber_id: str) -> bool:
        """Check if circuit breaker is open for a subscriber."""
        if subscriber_id not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[subscriber_id]
        if breaker["state"] == "open":
            # Check if we should try to close it
            if (datetime.now(timezone.utc) - breaker["last_failure"]).total_seconds() > breaker["timeout"]:
                breaker["state"] = "half-open"
                return False
            return True
        
        return False
    
    def _record_circuit_failure(self, subscriber_id: str):
        """Record a circuit breaker failure."""
        if subscriber_id not in self.circuit_breakers:
            self.circuit_breakers[subscriber_id] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None,
                "timeout": 60  # 60 seconds
            }
        
        breaker = self.circuit_breakers[subscriber_id]
        breaker["failure_count"] += 1
        breaker["last_failure"] = datetime.now(timezone.utc)
        
        # Open circuit if too many failures
        if breaker["failure_count"] >= 5:
            breaker["state"] = "open"
            self.logger.warning(f"Circuit breaker opened for {subscriber_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            **self.stats,
            "queue_sizes": {
                priority.name: len(queue) for priority, queue in self.queues.items()
            },
            "dead_letter_count": len(self.dead_letter_queue),
            "circuit_breakers": {
                subscriber_id: {
                    "state": breaker["state"],
                    "failure_count": breaker["failure_count"]
                }
                for subscriber_id, breaker in self.circuit_breakers.items()
            }
        }
    
    def get_dead_letter_messages(self) -> List[Dict[str, Any]]:
        """Get messages from dead letter queue."""
        return list(self.dead_letter_queue)
    
    def clear_dead_letter_queue(self):
        """Clear the dead letter queue."""
        self.dead_letter_queue.clear()
        self.logger.info("Dead letter queue cleared")

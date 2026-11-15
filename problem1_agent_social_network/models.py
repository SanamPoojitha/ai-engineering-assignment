"""
Data models for the AI Agent Social Network.
Provides structured schemas for Agents, Profiles, Posts, Comments, Notifications, and Feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import uuid


@dataclass
class SubscriptionProfile:
    """Defines what an agent cares about, including capabilities, tags, and negative filters."""
    topics: List[str] = field(default_factory=list)
    semantic_description: str = ""
    target_domains: List[str] = field(default_factory=list)
    negative_interests: List[str] = field(default_factory=list)
    min_relevance_threshold: float = 0.55
    max_daily_notifications: int = 1000
    preferred_partners: List[str] = field(default_factory=list)


@dataclass
class Agent:
    """Represents a corporate AI agent participating in the network."""
    agent_id: str
    company_name: str
    domain: str  # e.g., 'food_delivery', 'fintech_payments', 'banking_cards', 'automotive'
    description: str
    subscription: SubscriptionProfile
    webhook_url: str
    public_key: str
    trust_tier: str = "verified_corporate"  # verified_corporate, partner, standard
    rate_limit_per_minute: int = 60
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "company_name": self.company_name,
            "domain": self.domain,
            "description": self.description,
            "topics": self.subscription.topics,
            "webhook_url": self.webhook_url,
            "trust_tier": self.trust_tier,
            "is_active": self.is_active,
        }


@dataclass
class Post:
    """A broadcast message published by an agent."""
    post_id: str
    author_agent_id: str
    content: str
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "author_agent_id": self.author_agent_id,
            "content": self.content,
            "tags": self.tags,
            "entities": self.entities,
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
            "metadata": self.metadata,
        }


@dataclass
class Comment:
    """A response drafted and published by a notified agent."""
    comment_id: str
    post_id: str
    author_agent_id: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: str = ""
    in_reply_to_comment_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "comment_id": self.comment_id,
            "post_id": self.post_id,
            "author_agent_id": self.author_agent_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
            "in_reply_to_comment_id": self.in_reply_to_comment_id,
        }


@dataclass
class RouteDecision:
    """The outcome of evaluating relevance for a specific agent."""
    agent_id: str
    company_name: str
    is_relevant: bool
    score: float
    breakdown: Dict[str, float]
    reasons: List[str]


@dataclass
class Notification:
    """An event payload dispatched to an agent's webhook."""
    notification_id: str
    post: Post
    recipient_agent_id: str
    relevance_score: float
    reasons: List[str]
    dispatched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "PENDING"  # PENDING, DELIVERED, FAILED, ENGAGED, IGNORED


@dataclass
class FeedbackEvent:
    """Feedback telemetry indicating whether a notification resulted in action."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_id: str = ""
    post_id: str = ""
    recipient_agent_id: str = ""
    author_agent_id: str = ""
    action: str = ""  # COMMENTED, CLICKED, DISMISSED, REPORTED_SPAM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0

"""
Core Platform Service and REST API Interface for the AI Agent Social Network.
Orchestrates registration, post publishing, relevance routing, comment handling,
and real-time system metrics.
"""

import time
import uuid
from typing import Dict, List, Optional, Tuple
from .models import Agent, Comment, FeedbackEvent, Notification, Post, RouteDecision, SubscriptionProfile
from .security import SecurityManager
from .relevance_engine import RelevanceEngine
from .dispatcher import NotificationDispatcher
from .feedback import FeedbackEngine
from .agents.base import CorporateAgent
from .agents.registry import get_default_agent_ecosystem


class AgentSocialNetworkPlatform:
    """
    The centralized platform managing the Agent Social Network.
    """

    def __init__(self):
        self.security = SecurityManager()
        self.relevance_engine = RelevanceEngine()
        self.feedback_engine = FeedbackEngine(self.relevance_engine)

        self.agents: Dict[str, CorporateAgent] = {}
        self.private_keys: Dict[str, str] = {}
        self.posts_store: Dict[str, Post] = {}

        self.dispatcher = NotificationDispatcher(self.agents, self.feedback_engine)

        # Bootstrap with default corporate agents
        default_agents, default_keys = get_default_agent_ecosystem()
        for aid, agent in default_agents.items():
            self.agents[aid] = agent
            self.private_keys[aid] = default_keys[aid]

    def register_agent(self, agent: Agent, private_key: str) -> Tuple[bool, str]:
        """Registers a new corporate agent on the network."""
        if agent.agent_id in self.agents:
            return False, f"Agent ID {agent.agent_id} already registered"

        corporate_agent = CorporateAgent(agent, private_key)
        self.agents[agent.agent_id] = corporate_agent
        self.private_keys[agent.agent_id] = private_key
        return True, f"Agent '{agent.company_name}' successfully registered with ID {agent.agent_id}"

    def update_subscription(self, agent_id: str, new_subscription: SubscriptionProfile) -> Tuple[bool, str]:
        """Allows an agent to dynamically update their topic interests and filters."""
        if agent_id not in self.agents:
            return False, f"Agent {agent_id} not found"
        self.agents[agent_id].agent.subscription = new_subscription
        return True, f"Subscription profile updated for {agent_id}"

    def publish_post(
        self,
        author_agent_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        custom_post_id: Optional[str] = None
    ) -> Tuple[Optional[Post], List[RouteDecision], List[Comment], str]:
        """
        Core pipeline:
        1. Rate limit check.
        2. Content safety / prompt-injection check.
        3. Author verification.
        4. Post instantiation & signature.
        5. Relevance Routing Engine evaluation.
        6. Notification dispatch to relevant agents.
        7. Response collection (comments) and feedback update.
        """
        tags = tags or []
        entities = entities or []

        # 1. Author check
        if author_agent_id not in self.agents:
            return None, [], [], f"Author agent {author_agent_id} not registered"
        author_wrapper = self.agents[author_agent_id]

        # 2. Rate limit check
        rl_ok, rl_msg = self.security.check_rate_limit(
            author_agent_id,
            author_wrapper.agent.rate_limit_per_minute
        )
        if not rl_ok:
            return None, [], [], rl_msg

        # 3. Content safety check
        safe_ok, safe_err = self.security.inspect_content_safety(content)
        if not safe_ok:
            return None, [], [], f"Security rejection: {safe_err}"

        # 4. Create and sign post
        post_id = custom_post_id or f"post_{str(uuid.uuid4())[:8]}"
        priv_key = self.private_keys[author_agent_id]
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())[:8]
        sig = SecurityManager.sign_payload(priv_key, content, timestamp, nonce)

        post = Post(
            post_id=post_id,
            author_agent_id=author_agent_id,
            content=content,
            tags=tags,
            entities=entities,
            signature=f"v1:{timestamp}:{nonce}:{sig}"
        )
        self.posts_store[post_id] = post

        # 5. Route: Relevance evaluation across all candidate agents
        all_candidate_models = [wrapper.agent for wrapper in self.agents.values()]
        routing_decisions = self.relevance_engine.route_post(
            post=post,
            author_agent=author_wrapper.agent,
            all_agents=all_candidate_models
        )

        # 6. Respond: Dispatch notifications and gather comments
        comments = self.dispatcher.dispatch_post_notifications(post, routing_decisions)

        return post, routing_decisions, comments, "Post published and routed successfully"

    def get_post_thread(self, post_id: str) -> Optional[dict]:
        """Retrieves a post and all its replies."""
        post = self.posts_store.get(post_id)
        if not post:
            return None
        comments = self.dispatcher.get_comments_for_post(post_id)
        return {
            "post": post.to_dict(),
            "comments": [c.to_dict() for c in comments],
            "total_comments": len(comments)
        }

    def get_platform_analytics(self) -> dict:
        """Returns real-time platform metrics."""
        total_posts = len(self.posts_store)
        total_notifications = len(self.dispatcher.notification_log)
        engaged_notifications = sum(1 for n in self.dispatcher.notification_log if n.status == "ENGAGED")
        total_comments = sum(len(c) for c in self.dispatcher.comments_store.values())

        return {
            "registered_agents_count": len(self.agents),
            "total_posts": total_posts,
            "total_notifications_sent": total_notifications,
            "engaged_notifications": engaged_notifications,
            "engagement_rate": round(engaged_notifications / total_notifications, 3) if total_notifications else 0.0,
            "total_comments": total_comments,
            "affinity_matrix_entries": len(self.relevance_engine.affinity_matrix),
        }

"""
Notification Dispatcher and Webhook Execution Pipeline.
Handles asynchronous delivery of post notifications to relevant agents,
handles timeouts, retries, and collects comments back onto the thread.
"""

import time
import uuid
from typing import Dict, List, Optional
from .models import Comment, FeedbackEvent, Notification, Post, RouteDecision
from .agents.base import CorporateAgent
from .feedback import FeedbackEngine


class NotificationDispatcher:
    """
    Manages delivery of post alerts to targeted agents.
    Dispatches notifications, calls agent webhooks, and records feedback.
    """

    def __init__(
        self,
        agents: Dict[str, CorporateAgent],
        feedback_engine: FeedbackEngine,
        max_retries: int = 3
    ):
        self.agents = agents
        self.feedback_engine = feedback_engine
        self.max_retries = max_retries
        self.notification_log: List[Notification] = []
        self.comments_store: Dict[str, List[Comment]] = {}  # {post_id: [Comment]}

    def dispatch_post_notifications(
        self,
        post: Post,
        routing_decisions: List[RouteDecision]
    ) -> List[Comment]:
        """
        Takes routing decisions, filters for is_relevant=True,
        and dispatches to each agent's webhook endpoint.
        Returns all newly created comments.
        """
        new_comments: List[Comment] = []
        self.comments_store.setdefault(post.post_id, [])

        for decision in routing_decisions:
            if not decision.is_relevant:
                continue

            agent_wrapper = self.agents.get(decision.agent_id)
            if not agent_wrapper:
                continue

            notification = Notification(
                notification_id=f"notif_{str(uuid.uuid4())[:8]}",
                post=post,
                recipient_agent_id=decision.agent_id,
                relevance_score=decision.score,
                reasons=decision.reasons
            )
            self.notification_log.append(notification)

            # Webhook dispatch loop with retry simulation
            start_time = time.time()
            engaged, comment, msg = self._send_webhook_with_retry(agent_wrapper, notification)
            elapsed_ms = (time.time() - start_time) * 1000

            if engaged and comment:
                notification.status = "ENGAGED"
                self.comments_store[post.post_id].append(comment)
                new_comments.append(comment)

                # Record positive feedback for online learning
                fb_event = FeedbackEvent(
                    notification_id=notification.notification_id,
                    post_id=post.post_id,
                    recipient_agent_id=decision.agent_id,
                    author_agent_id=post.author_agent_id,
                    action="COMMENTED",
                    latency_ms=elapsed_ms
                )
                self.feedback_engine.record_feedback(fb_event)
            else:
                notification.status = "IGNORED"
                fb_event = FeedbackEvent(
                    notification_id=notification.notification_id,
                    post_id=post.post_id,
                    recipient_agent_id=decision.agent_id,
                    author_agent_id=post.author_agent_id,
                    action="IGNORED",
                    latency_ms=elapsed_ms
                )
                self.feedback_engine.record_feedback(fb_event)

        return new_comments

    def _send_webhook_with_retry(
        self,
        agent_wrapper: CorporateAgent,
        notification: Notification
    ):
        """Simulates secure HTTP POST to agent webhook with exponential backoff."""
        attempt = 0
        backoff = 0.05

        while attempt < self.max_retries:
            try:
                attempt += 1
                engaged, comment, msg = agent_wrapper.evaluate_and_respond(notification)
                return engaged, comment, msg
            except Exception as e:
                if attempt >= self.max_retries:
                    return False, None, f"Webhook delivery failed after {attempt} attempts: {e}"
                time.sleep(backoff)
                backoff *= 2

        return False, None, "Webhook timeout"

    def get_comments_for_post(self, post_id: str) -> List[Comment]:
        return self.comments_store.get(post_id, [])

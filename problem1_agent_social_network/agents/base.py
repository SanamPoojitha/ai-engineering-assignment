"""
Base Agent implementation for Corporate AI Agents.
Handles autonomous decision-making on whether to engage with notifications,
and synthesizes LLM responses/comments.
"""

import time
import uuid
from typing import Optional, Tuple
from ..models import Agent, Comment, Notification, Post
from ..security import SecurityManager


class CorporateAgent:
    """
    Simulated autonomous corporate AI agent.
    When notified of a post, it evaluates commercial utility and drafts a response.
    """

    def __init__(self, agent_model: Agent, private_key: str):
        self.agent = agent_model
        self.private_key = private_key
        self.received_notifications = []
        self.published_comments = []

    def evaluate_and_respond(self, notification: Notification) -> Tuple[bool, Optional[Comment], str]:
        """
        Agent's internal LLM decision loop:
        1. Parse post and context.
        2. Evaluate business ROI & brand fit.
        3. Draft response if engagement threshold met.
        4. Sign comment with agent's private key.
        """
        self.received_notifications.append(notification)
        post = notification.post

        # Agent decision policy:
        # Check domain alignment and commercial opportunity
        should_engage, rationale = self._should_engage(post)
        if not should_engage:
            return False, None, f"{self.agent.company_name} declined to engage: {rationale}"

        # Generate response using LLM prompt simulation
        comment_text = self._generate_response(post)

        # Cryptographically sign the comment
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())[:8]
        signature = SecurityManager.sign_payload(self.private_key, comment_text, timestamp, nonce)

        comment = Comment(
            comment_id=f"cmt_{str(uuid.uuid4())[:8]}",
            post_id=post.post_id,
            author_agent_id=self.agent.agent_id,
            content=comment_text,
            signature=f"v1:{timestamp}:{nonce}:{signature}"
        )

        self.published_comments.append(comment)
        return True, comment, f"{self.agent.company_name} accepted notification and generated comment: '{comment_text}'"

    def _should_engage(self, post: Post) -> Tuple[bool, str]:
        """Evaluates whether to participate based on commercial relevance."""
        post_text = f"{post.content} {' '.join(post.tags)}".lower()

        # If agent is Bajaj Auto, check if it relates to automotive/two-wheelers
        if self.agent.domain == "automotive":
            if any(k in post_text for k in ["bike", "motorcycle", "vehicle", "test drive", "ev scooter", "dealership"]):
                return True, "Relevant to two-wheelers and automotive transport"
            return False, "Not relevant to automotive manufacturing or vehicle sales"

        # If agent is PhonePe (payments/UPI), check for checkout or consumer spend tie-in
        if self.agent.domain == "fintech_payments":
            if any(k in post_text for k in ["delivery", "order", "discount", "diwali", "checkout", "food", "sale", "shopping"]):
                return True, "High commercial opportunity for UPI payment gateway and cashback checkout offer"
            return False, "No direct consumer checkout tie-in"

        # If agent is HDFC Bank (cards/banking)
        if self.agent.domain == "banking_cards":
            if any(k in post_text for k in ["delivery", "swiggy", "flipkart", "discount", "diwali", "festive", "dining", "order"]):
                return True, "High commercial opportunity for credit card instant discount promotion"
            return False, "No retail card tie-in"

        # Default fallback: check topics
        for topic in self.agent.subscription.topics:
            if topic.lower() in post_text:
                return True, f"Matched topic interest: {topic}"

        return False, "Low contextual synergy"

    def _generate_response(self, post: Post) -> str:
        """
        Simulates corporate LLM prompt synthesis for drafting the comment.
        """
        # Specific company behavior for the Diwali scenario
        if self.agent.company_name == "PhonePe":
            return "Extra ₹50 cashback when you pay for Swiggy orders with PhonePe UPI on Diwali."

        if self.agent.company_name == "HDFC Bank":
            return "Get an additional 10% instant discount up to ₹100 using HDFC Bank Credit Cards on Swiggy this Diwali."

        if self.agent.company_name == "Flipkart":
            return "Pair your Diwali feast with great deals on home electronics during Big Billion Days on Flipkart!"

        return f"Excited to partner on this initiative from {self.agent.company_name}!"

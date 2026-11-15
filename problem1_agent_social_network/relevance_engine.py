"""
Relevance Routing Engine for the AI Agent Social Network.
Decides with high precision and recall which agents should receive a post notification.
Uses a multi-stage pipeline:
1. Negative / exclusion filter
2. Semantic vector similarity
3. Bipartite commercial synergy graph
4. Contextual intent boost
5. Historical engagement affinity weights
"""

import math
import re
from typing import Dict, List, Set, Tuple
from .models import Agent, Post, RouteDecision


class TextVectorizer:
    """
    Lightweight, self-contained semantic vectorizer using n-grams and term weighting.
    Provides cosine similarity between post text and agent profiles.
    Pluggable with neural embedding APIs (e.g., text-embedding-3-small, Gemini embeddings).
    """

    def __init__(self):
        # Domain stop words to ignore
        self.stop_words = {
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
            "with", "by", "of", "all", "is", "are", "was", "were", "it", "this"
        }

    def tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-₹%]+\b", text.lower())
        tokens = []
        for w in words:
            if w not in self.stop_words:
                tokens.append(w)
                # Subword n-grams for root matching
                if len(w) > 4:
                    tokens.append(w[:4])
        return tokens

    def compute_vector(self, text: str) -> Dict[str, float]:
        tokens = self.tokenize(text)
        freq: Dict[str, float] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0.0) + 1.0

        # Term frequency normalization
        norm = math.sqrt(sum(v * v for v in freq.values()))
        if norm == 0:
            return {}
        return {k: v / norm for k, v in freq.items()}

    def cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        # Dot product of normalized vectors
        dot = 0.0
        for k, v in vec_a.items():
            if k in vec_b:
                dot += v * vec_b[k]
        return min(max(dot, 0.0), 1.0)


class RelevanceEngine:
    """
    Multi-stage relevance engine that evaluates which agents should be notified of a post.
    """

    # Commercial domain synergy matrix: defines structural partnership probability between industries
    DEFAULT_SYNERGY_GRAPH: Dict[Tuple[str, str], float] = {
        ("food_delivery", "fintech_payments"): 0.90,  # Checkout payment tie-ins, UPI cashback
        ("food_delivery", "banking_cards"): 0.85,     # Credit card discounts, dining rewards
        ("food_delivery", "e_commerce"): 0.50,        # Co-promotions, loyalty programs
        ("food_delivery", "automotive"): 0.05,        # Two-wheelers vs food delivery offers (no tie-in)
        ("e_commerce", "fintech_payments"): 0.95,     # Merchant payment processing, BNPL
        ("e_commerce", "banking_cards"): 0.90,        # Co-branded cards, EMI offers
        ("e_commerce", "automotive"): 0.20,           # Automotive accessories, occasional tie-in
        ("fintech_payments", "banking_cards"): 0.85,  # Cards issued on payment rails
        ("automotive", "banking_cards"): 0.70,        # Auto loans, vehicle financing
        ("automotive", "fintech_payments"): 0.40,     # Fastag, digital toll payments
    }

    def __init__(
        self,
        weight_vector: float = 0.25,
        weight_synergy: float = 0.35,
        weight_intent: float = 0.30,
        weight_affinity: float = 0.10,
        global_threshold: float = 0.50,
    ):
        self.vectorizer = TextVectorizer()
        self.w_vec = weight_vector
        self.w_syn = weight_synergy
        self.w_int = weight_intent
        self.w_aff = weight_affinity
        self.global_threshold = global_threshold

        # Dynamic affinity matrix learned from feedback: {(agent_a, agent_b): weight}
        self.affinity_matrix: Dict[Tuple[str, str], float] = {}

    def get_domain_synergy(self, domain_a: str, domain_b: str) -> float:
        """Returns the commercial partnership synergy between two business domains."""
        if domain_a == domain_b:
            return 0.70  # Peer companies in the same industry (competitive or co-promotional)
        pair1 = (domain_a, domain_b)
        pair2 = (domain_b, domain_a)
        if pair1 in self.DEFAULT_SYNERGY_GRAPH:
            return self.DEFAULT_SYNERGY_GRAPH[pair1]
        if pair2 in self.DEFAULT_SYNERGY_GRAPH:
            return self.DEFAULT_SYNERGY_GRAPH[pair2]
        return 0.10  # Baseline low correlation for unrelated domains

    def compute_intent_boost(self, post: Post, agent: Agent) -> Tuple[float, List[str]]:
        """
        Calculates intent boost when a post's trigger words (e.g. 'Diwali', 'offer', '5% off')
        explicitly match the commercial engagement topics of an agent.
        """
        boost_reasons = []
        boost_score = 0.0

        post_text_lower = f"{post.content} {' '.join(post.tags)} {' '.join(post.entities)}".lower()
        sub = agent.subscription

        # Check explicit topics: token-based, stem-aware, and phrase-based matching
        matched_topics = []
        raw_post_words = set(re.findall(r"\b[a-zA-Z0-9_\-₹%]+\b", post_text_lower))
        stemmed_post_words = {w.rstrip("s") for w in raw_post_words}

        for topic in sub.topics:
            topic_lower = topic.lower()
            raw_topic_words = set(re.findall(r"\b[a-zA-Z0-9_\-₹%]+\b", topic_lower))
            stemmed_topic_words = {w.rstrip("s") for w in raw_topic_words}

            if topic_lower in post_text_lower:
                matched_topics.append(topic)
            elif stemmed_topic_words.intersection(stemmed_post_words):
                matched_topics.append(topic)

        if matched_topics:
            unique_topics = list(set(matched_topics))
            boost_score += min(len(unique_topics) * 0.30, 0.65)
            boost_reasons.append(f"Matched subscribed topics: {unique_topics}")

        # Check commercial tie-in triggers (festive sales, payments, discounts)
        commercial_triggers = {"diwali", "festive", "sale", "discount", "cashback", "off", "card", "upi", "delivery"}
        post_triggers = [trig for trig in commercial_triggers if trig in post_text_lower]

        if post_triggers:
            # If the agent specializes in checkout, offers, cards, or payments
            agent_desc_lower = f"{agent.description} {sub.semantic_description}".lower()
            if any(term in agent_desc_lower for term in ["cashback", "payment", "card", "discount", "offer", "checkout", "rewards"]):
                boost_score += 0.35
                boost_reasons.append(f"Commercial offer triggers aligned: {post_triggers}")

        return min(boost_score, 1.0), boost_reasons

    def evaluate_post_for_agent(
        self,
        post: Post,
        author_agent: Agent,
        candidate_agent: Agent
    ) -> RouteDecision:
        """
        Evaluates a candidate agent against a post and returns a structured RouteDecision.
        """
        # Hard constraint 1: Self-routing is disallowed
        if post.author_agent_id == candidate_agent.agent_id:
            return RouteDecision(
                agent_id=candidate_agent.agent_id,
                company_name=candidate_agent.company_name,
                is_relevant=False,
                score=0.0,
                breakdown={},
                reasons=["Author cannot receive their own post"]
            )

        # Hard constraint 2: Inactive or suspended agent
        if not candidate_agent.is_active:
            return RouteDecision(
                agent_id=candidate_agent.agent_id,
                company_name=candidate_agent.company_name,
                is_relevant=False,
                score=0.0,
                breakdown={},
                reasons=["Agent is marked inactive"]
            )

        post_full_text = f"{post.content} {' '.join(post.tags)} {' '.join(post.entities)}".lower()

        # Hard constraint 3: Negative interest filtering
        for neg_keyword in candidate_agent.subscription.negative_interests:
            if neg_keyword.lower() in post_full_text:
                return RouteDecision(
                    agent_id=candidate_agent.agent_id,
                    company_name=candidate_agent.company_name,
                    is_relevant=False,
                    score=0.0,
                    breakdown={"negative_filter_hit": 1.0},
                    reasons=[f"Filtered by negative interest keyword: '{neg_keyword}'"]
                )

        # 1. Semantic Vector Similarity
        agent_profile_text = (
            f"{candidate_agent.description} {candidate_agent.subscription.semantic_description} "
            f"{' '.join(candidate_agent.subscription.topics)} {candidate_agent.domain}"
        )
        post_vec = self.vectorizer.compute_vector(f"{post.content} {' '.join(post.tags)}")
        agent_vec = self.vectorizer.compute_vector(agent_profile_text)
        vector_sim = self.vectorizer.cosine_similarity(post_vec, agent_vec)

        # 2. Domain Synergy
        synergy_score = self.get_domain_synergy(author_agent.domain, candidate_agent.domain)

        # 3. Contextual Intent Boost
        intent_score, intent_reasons = self.compute_intent_boost(post, candidate_agent)

        # 4. Historical Feedback Affinity
        affinity_key = (post.author_agent_id, candidate_agent.agent_id)
        affinity_score = self.affinity_matrix.get(affinity_key, 0.50)  # Neutral baseline = 0.50

        # Composite Scoring
        total_score = (
            self.w_vec * vector_sim +
            self.w_syn * synergy_score +
            self.w_int * intent_score +
            self.w_aff * affinity_score
        )

        threshold = candidate_agent.subscription.min_relevance_threshold or self.global_threshold
        is_relevant = total_score >= threshold

        reasons = []
        if is_relevant:
            reasons.append(f"Exceeded threshold {threshold:.2f} with total score {total_score:.2f}")
            reasons.append(f"Domain synergy '{author_agent.domain}' <-> '{candidate_agent.domain}': {synergy_score:.2f}")
            reasons.extend(intent_reasons)
        else:
            reasons.append(
                f"Below threshold {threshold:.2f} (Total: {total_score:.2f}, Vector: {vector_sim:.2f}, "
                f"Synergy: {synergy_score:.2f}, Intent: {intent_score:.2f})"
            )

        breakdown = {
            "vector_similarity": round(vector_sim, 3),
            "domain_synergy": round(synergy_score, 3),
            "intent_boost": round(intent_score, 3),
            "historical_affinity": round(affinity_score, 3),
            "composite_score": round(total_score, 3),
        }

        return RouteDecision(
            agent_id=candidate_agent.agent_id,
            company_name=candidate_agent.company_name,
            is_relevant=is_relevant,
            score=round(total_score, 3),
            breakdown=breakdown,
            reasons=reasons
        )

    def route_post(
        self,
        post: Post,
        author_agent: Agent,
        all_agents: List[Agent]
    ) -> List[RouteDecision]:
        """
        Evaluates all candidate agents for a post and returns sorted decisions.
        """
        decisions = []
        for agent in all_agents:
            decision = self.evaluate_post_for_agent(post, author_agent, agent)
            decisions.append(decision)

        # Sort by relevance descending
        decisions.sort(key=lambda d: d.score, reverse=True)
        return decisions

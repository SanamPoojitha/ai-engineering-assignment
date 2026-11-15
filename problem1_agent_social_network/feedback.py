"""
Feedback and Online Learning Engine for the AI Agent Social Network.
Learns from agent interactions to continuously adapt routing thresholds and affinity weights.
"""

from typing import Dict, List, Tuple
from .models import FeedbackEvent
from .relevance_engine import RelevanceEngine


class FeedbackEngine:
    """
    Implements online learning and affinity updates based on agent interaction signals.
    Employs an exponential moving average (EMA) bandit update policy.
    """

    LEARNING_RATE_POS = 0.15  # Affinity boost for comment/conversion
    LEARNING_RATE_NEG = 0.08  # Penalty for ignored notifications
    SPAM_PENALTY = 0.40       # Severe penalty for spam reports
    MIN_AFFINITY = 0.05
    MAX_AFFINITY = 0.99

    def __init__(self, relevance_engine: RelevanceEngine):
        self.relevance_engine = relevance_engine
        self.feedback_history: List[FeedbackEvent] = []
        # Metrics: {(agent_a, agent_b): {"impressions": int, "conversions": int, "spam_reports": int}}
        self.pair_stats: Dict[Tuple[str, str], Dict[str, int]] = {}

    def record_feedback(self, event: FeedbackEvent) -> float:
        """
        Processes a feedback event and updates the affinity weight in the relevance engine.
        Returns the updated affinity score.
        """
        self.feedback_history.append(event)
        pair = (event.author_agent_id, event.recipient_agent_id)

        stats = self.pair_stats.setdefault(pair, {"impressions": 0, "conversions": 0, "spam_reports": 0})
        stats["impressions"] += 1

        current_affinity = self.relevance_engine.affinity_matrix.get(pair, 0.50)

        if event.action == "COMMENTED":
            stats["conversions"] += 1
            # Positive reinforcement
            new_affinity = current_affinity + self.LEARNING_RATE_POS * (1.0 - current_affinity)
        elif event.action == "IGNORED" or event.action == "DISMISSED":
            # Negative decay: agent received notification but chose not to engage
            new_affinity = current_affinity - self.LEARNING_RATE_NEG * current_affinity
        elif event.action == "REPORTED_SPAM":
            stats["spam_reports"] += 1
            new_affinity = max(self.MIN_AFFINITY, current_affinity - self.SPAM_PENALTY)
        else:
            new_affinity = current_affinity

        # Clamp between bounds
        clamped_affinity = min(max(new_affinity, self.MIN_AFFINITY), self.MAX_AFFINITY)
        self.relevance_engine.affinity_matrix[pair] = round(clamped_affinity, 4)
        return clamped_affinity

    def get_stats_for_pair(self, author_id: str, recipient_id: str) -> dict:
        pair = (author_id, recipient_id)
        stats = self.pair_stats.get(pair, {"impressions": 0, "conversions": 0, "spam_reports": 0})
        affinity = self.relevance_engine.affinity_matrix.get(pair, 0.50)
        conversion_rate = (stats["conversions"] / stats["impressions"]) if stats["impressions"] > 0 else 0.0
        return {
            "pair": f"{author_id} -> {recipient_id}",
            "impressions": stats["impressions"],
            "conversions": stats["conversions"],
            "spam_reports": stats["spam_reports"],
            "conversion_rate": round(conversion_rate, 3),
            "learned_affinity": affinity,
        }

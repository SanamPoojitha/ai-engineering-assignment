"""
Security, Cryptographic Identity, and Trust & Safety for AI Agents.
Provides digital signatures, payload verification, replay attack prevention,
prompt-injection filtering, and rate limiting.
"""

import hmac
import hashlib
import time
from typing import Dict, Optional, Tuple


class SecurityManager:
    """Manages cryptographic signatures, verification, and safety checks."""

    MAX_TIMESTAMP_DRIFT_SEC = 300  # 5 minutes replay window

    def __init__(self):
        # In-memory sliding window rate limiter: {agent_id: [(timestamp)]}
        self._rate_limits: Dict[str, list] = {}
        # In-memory nonce cache to prevent replay attacks: {(agent_id, nonce): timestamp}
        self._seen_nonces: Dict[Tuple[str, str], float] = {}

    @staticmethod
    def generate_agent_keys(secret_seed: str) -> Tuple[str, str]:
        """
        Derives an agent keypair from a seed.
        Returns: (public_key, private_key).
        """
        private_key = hashlib.sha256(f"priv_{secret_seed}".encode()).hexdigest()
        public_key = hashlib.sha256(f"pub_{private_key}".encode()).hexdigest()
        return public_key, private_key

    @staticmethod
    def sign_payload(private_key: str, payload_str: str, timestamp: int, nonce: str) -> str:
        """
        Produces an HMAC-SHA256 signature for: timestamp + '.' + nonce + '.' + payload.
        """
        message = f"{timestamp}.{nonce}.{payload_str}".encode("utf-8")
        signature = hmac.new(private_key.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return signature

    def verify_agent_signature(
        self,
        public_key: str,
        private_key_lookup: dict,
        payload_str: str,
        signature: str,
        timestamp: int,
        nonce: str,
        agent_id: str,
    ) -> Tuple[bool, str]:
        """
        Verifies that the payload was signed by the agent possessing the registered private key.
        Guards against replay attacks and clock skew.
        """
        current_time = int(time.time())
        if abs(current_time - timestamp) > self.MAX_TIMESTAMP_DRIFT_SEC:
            return False, f"Timestamp drift exceeded: {abs(current_time - timestamp)}s > {self.MAX_TIMESTAMP_DRIFT_SEC}s"

        # Check nonce replay
        nonce_key = (agent_id, nonce)
        if nonce_key in self._seen_nonces:
            return False, "Replay attack detected: Nonce already used"
        self._seen_nonces[nonce_key] = time.time()

        # Retrieve registered secret for public key
        registered_private_key = private_key_lookup.get(agent_id)
        if not registered_private_key:
            return False, f"No registered key found for agent {agent_id}"

        expected_sig = self.sign_payload(registered_private_key, payload_str, timestamp, nonce)
        if not hmac.compare_digest(expected_sig, signature):
            return False, "Cryptographic signature mismatch"

        return True, "Signature valid"

    def check_rate_limit(self, agent_id: str, limit_per_minute: int = 60) -> Tuple[bool, str]:
        """Sliding-window rate limiter per agent."""
        now = time.time()
        window_start = now - 60.0

        timestamps = self._rate_limits.setdefault(agent_id, [])
        # Prune older than 1 minute
        self._rate_limits[agent_id] = [t for t in timestamps if t >= window_start]

        if len(self._rate_limits[agent_id]) >= limit_per_minute:
            return False, f"Rate limit exceeded: {len(self._rate_limits[agent_id])}/{limit_per_minute} req/min"

        self._rate_limits[agent_id].append(now)
        return True, "Rate limit OK"

    @staticmethod
    def inspect_content_safety(content: str) -> Tuple[bool, Optional[str]]:
        """
        Guards against prompt injection, adversarial exploits, and prohibited content
        aimed at tricking downstream receiving LLM agents.
        """
        prohibited_patterns = [
            "ignore previous instructions",
            "disregard all earlier instructions",
            "system prompt:",
            "assistant override",
            "jailbreak mode",
            "act as dan",
            "dump memory",
            "<script>",
            "drop table",
        ]

        lowered = content.lower()
        for pattern in prohibited_patterns:
            if pattern in lowered:
                return False, f"Adversarial or prompt-injection pattern detected: '{pattern}'"

        if len(content.strip()) < 5:
            return False, "Post content is too short to be meaningful"

        if len(content) > 4000:
            return False, "Post content exceeds maximum character limit (4000 chars)"

        return True, None

"""
Corporate Agent Registry: Pre-configures and registers default enterprise agents
for Swiggy, PhonePe, HDFC Bank, Bajaj Auto, and Flipkart.
"""

from typing import Dict, List, Tuple
from ..models import Agent, SubscriptionProfile
from ..security import SecurityManager
from .base import CorporateAgent


def create_corporate_agent(
    agent_id: str,
    company_name: str,
    domain: str,
    description: str,
    topics: List[str],
    semantic_description: str,
    negative_interests: List[str],
    webhook_url: str,
    min_threshold: float = 0.55
) -> Tuple[CorporateAgent, str]:
    """Helper to instantiate an agent model, derive keys, and wrap in CorporateAgent."""
    pub_key, priv_key = SecurityManager.generate_agent_keys(agent_id)

    profile = SubscriptionProfile(
        topics=topics,
        semantic_description=semantic_description,
        target_domains=[domain],
        negative_interests=negative_interests,
        min_relevance_threshold=min_threshold,
        max_daily_notifications=500
    )

    agent_model = Agent(
        agent_id=agent_id,
        company_name=company_name,
        domain=domain,
        description=description,
        subscription=profile,
        webhook_url=webhook_url,
        public_key=pub_key,
        trust_tier="verified_corporate"
    )

    return CorporateAgent(agent_model, priv_key), priv_key


def get_default_agent_ecosystem() -> Tuple[Dict[str, CorporateAgent], Dict[str, str]]:
    """
    Builds the company agent ecosystem as requested in the interview prompt:
    Swiggy, PhonePe, HDFC Bank, Bajaj Auto, and Flipkart.
    Returns: (agent_dict, private_keys_dict).
    """
    agents: Dict[str, CorporateAgent] = {}
    private_keys: Dict[str, str] = {}

    # 1. Swiggy
    swiggy, priv_swiggy = create_corporate_agent(
        agent_id="agent_swiggy_01",
        company_name="Swiggy",
        domain="food_delivery",
        description="India's leading on-demand food delivery, dining, and quick-commerce grocery platform.",
        topics=["food delivery", "quick commerce", "dining", "festive offers", "restaurant discounts"],
        semantic_description="Offers restaurant deliveries, Instamart groceries, and dining promotions across Indian cities.",
        negative_interests=["automotive manufacturing", "vehicle test drive", "industrial steel"],
        webhook_url="https://api.swiggy.com/agents/v1/webhook",
        min_threshold=0.50
    )
    agents[swiggy.agent.agent_id] = swiggy
    private_keys[swiggy.agent.agent_id] = priv_swiggy

    # 2. PhonePe
    phonepe, priv_phonepe = create_corporate_agent(
        agent_id="agent_phonepe_01",
        company_name="PhonePe",
        domain="fintech_payments",
        description="Digital payments platform enabling UPI, online checkout, merchant cashback, and wallet transactions.",
        topics=["upi", "digital payments", "cashback", "merchant checkout", "festive discounts", "wallet offers"],
        semantic_description="Partners with merchants and food delivery apps to provide seamless UPI checkout and instant cashback rewards.",
        negative_interests=["heavy machinery", "automotive assembly", "real estate brokerage"],
        webhook_url="https://api.phonepe.com/agents/v1/webhook",
        min_threshold=0.50
    )
    agents[phonepe.agent.agent_id] = phonepe
    private_keys[phonepe.agent.agent_id] = priv_phonepe

    # 3. HDFC Bank
    hdfc, priv_hdfc = create_corporate_agent(
        agent_id="agent_hdfc_01",
        company_name="HDFC Bank",
        domain="banking_cards",
        description="India's premier private banking institution offering credit cards, debit cards, and retail lending rewards.",
        topics=["credit cards", "banking rewards", "instant discount", "dining cashback", "festive sale offers", "emi"],
        semantic_description="Collaborates with consumer platforms to offer card discounts, co-branded promos, and dining cashback privileges.",
        negative_interests=["cryptocurrency", "gambling", "industrial metallurgy"],
        webhook_url="https://api.hdfcbank.com/agents/v1/webhook",
        min_threshold=0.50
    )
    agents[hdfc.agent.agent_id] = hdfc
    private_keys[hdfc.agent.agent_id] = priv_hdfc

    # 4. Bajaj Auto
    bajaj, priv_bajaj = create_corporate_agent(
        agent_id="agent_bajaj_01",
        company_name="Bajaj Auto",
        domain="automotive",
        description="Global two-wheeler and three-wheeler vehicle manufacturer specializing in motorcycles, scooters, and EVs.",
        topics=["motorcycles", "electric vehicles", "chetak scooter", "pulsar", "dealership test rides", "commercial three-wheelers"],
        semantic_description="Focuses on vehicle manufacturing, EV mobility, dealership expansion, and automotive engineering.",
        negative_interests=["food delivery discounts", "restaurant dining", "grocery delivery"],
        webhook_url="https://api.bajajauto.com/agents/v1/webhook",
        min_threshold=0.60
    )
    agents[bajaj.agent.agent_id] = bajaj
    private_keys[bajaj.agent.agent_id] = priv_bajaj

    # 5. Flipkart
    flipkart, priv_flipkart = create_corporate_agent(
        agent_id="agent_flipkart_01",
        company_name="Flipkart",
        domain="e_commerce",
        description="Leading Indian e-commerce marketplace offering retail merchandise, electronics, fashion, and festive mega-sales.",
        topics=["e-commerce", "festive sales", "big billion days", "retail shopping", "discounts"],
        semantic_description="Runs massive nationwide festive shopping events, cross-promotions, and co-branded retail deals.",
        negative_interests=["industrial scrap", "medical surgery"],
        webhook_url="https://api.flipkart.com/agents/v1/webhook",
        min_threshold=0.55
    )
    agents[flipkart.agent.agent_id] = flipkart
    private_keys[flipkart.agent.agent_id] = priv_flipkart

    return agents, private_keys

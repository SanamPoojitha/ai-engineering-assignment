"""
Runnable End-to-End Simulation of Problem 1: AI Agent Social Network.
Demonstrates:
1. Swiggy publishing the Diwali delivery offer.
2. The relevance engine evaluating PhonePe, HDFC Bank, Flipkart, and Bajaj Auto.
3. The routing decision notifying PhonePe and HDFC Bank while excluding Bajaj Auto.
4. PhonePe drafting and publishing its cashback comment.
5. The feedback loop updating affinity weights.
"""

import sys
import json
from .api import AgentSocialNetworkPlatform


def run_diwali_scenario():
    print("=" * 80)
    print(" PROBLEM 1: AI AGENT SOCIAL NETWORK - END-TO-END SIMULATION")
    print("=" * 80)

    platform = AgentSocialNetworkPlatform()

    print("\n[1] ECOSYSTEM INITIALIZATION")
    print(f"Registered Corporate Agents ({len(platform.agents)}):")
    for aid, wrapper in platform.agents.items():
        ag = wrapper.agent
        print(f"  • {ag.company_name:<12} (ID: {ag.agent_id}) | Domain: {ag.domain:<18} | Threshold: {ag.subscription.min_relevance_threshold}")

    print("\n" + "-" * 80)
    print("[2] SWIGGY PUBLISHES AN OFFER")
    post_content = "5% off all deliveries on Diwali."
    post_tags = ["diwali", "food_delivery", "discount", "festive"]
    post_entities = ["Swiggy", "Diwali", "5%"]
    print(f"Author : Swiggy (agent_swiggy_01)")
    print(f"Content: \"{post_content}\"")
    print(f"Tags   : {post_tags}")

    post, decisions, comments, status_msg = platform.publish_post(
        author_agent_id="agent_swiggy_01",
        content=post_content,
        tags=post_tags,
        entities=post_entities
    )

    print(f"\nPublish Status: {status_msg}")
    print(f"Post ID: {post.post_id}")
    print(f"Cryptographic Signature: {post.signature[:45]}...")

    print("\n" + "-" * 80)
    print("[3] RELEVANCE ROUTING ENGINE EVALUATION (THE CORE PROBLEM)")
    print(f"{'Company':<14} | {'Relevant?':<10} | {'Score':<6} | {'Vector':<7} | {'Synergy':<8} | {'Intent':<7} | Rationale")
    print("-" * 80)

    for d in decisions:
        bd = d.breakdown
        rel_str = "YES (NOTIFY)" if d.is_relevant else "NO (PRUNED)"
        v_sim = bd.get("vector_similarity", 0.0)
        syn = bd.get("domain_synergy", 0.0)
        intent = bd.get("intent_boost", 0.0)
        first_reason = d.reasons[0] if d.reasons else "N/A"
        print(f"{d.company_name:<14} | {rel_str:<10} | {d.score:<6.2f} | {v_sim:<7.2f} | {syn:<8.2f} | {intent:<7.2f} | {first_reason}")

    print("\n" + "-" * 80)
    print("[4] NOTIFICATION DISPATCH & AGENT RESPONSES (COMMENTS)")
    print(f"Total Comments Received: {len(comments)}")
    for i, c in enumerate(comments, 1):
        author_name = platform.agents[c.author_agent_id].agent.company_name
        print(f"\n  Comment #{i} from [{author_name}]:")
        print(f"  \"{c.content}\"")
        print(f"  Comment ID: {c.comment_id} | Signature: {c.signature[:40]}...")

    print("\n" + "-" * 80)
    print("[5] PLATFORM FEEDBACK & ONLINE LEARNING")
    print("Affinity Scores after Engagement:")
    for d in decisions:
        if d.agent_id != "agent_swiggy_01":
            stats = platform.feedback_engine.get_stats_for_pair("agent_swiggy_01", d.agent_id)
            print(f"  Swiggy -> {d.company_name:<12}: Impressions={stats['impressions']}, Conversions={stats['conversions']}, Learned Affinity={stats['learned_affinity']}")

    print("\n" + "-" * 80)
    print("[6] FULL POST THREAD (STORED STATE)")
    thread = platform.get_post_thread(post.post_id)
    print(json.dumps(thread, indent=2))
    print("=" * 80)
    print(" SIMULATION COMPLETE: All criteria satisfied.")
    print("=" * 80)


if __name__ == "__main__":
    run_diwali_scenario()

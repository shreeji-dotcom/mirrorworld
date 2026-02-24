import streamlit as st
import numpy as np
import pandas as pd
import time

# =========================
# Page + UI Styling (Fix 3 optional)
# =========================
st.set_page_config(page_title="MirrorWorld", layout="wide")

st.markdown("""
<style>
/* Optional: make metrics a bit smaller to prevent truncation on narrow screens */
div[data-testid="stMetricValue"] { font-size: 1.55rem !important; }
div[data-testid="stMetricLabel"] { font-size: 0.92rem !important; }
div[data-testid="stMetricDelta"] { font-size: 0.9rem !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def fmt_m(x):
    # format millions
    return f"${x:,.0f}M"

def pressure_label(p):
    if p >= 80: return "Very High"
    if p >= 60: return "High"
    if p >= 40: return "Moderate"
    if p >= 20: return "Low"
    return "Very Low"

def risk_label(p):
    if p >= 70: return "Critical"
    if p >= 50: return "Elevated"
    if p >= 30: return "Moderate"
    return "Low"

def make_rng(seed):
    return np.random.default_rng(seed)

def now_seed():
    # stable enough for randomization; avoids everyone getting same run
    return int(time.time() * 1000) % 2_147_483_647

# =========================
# Game Design: Levers (with descriptions)
# =========================
LEVER_HELP = {
    "Growth aggressiveness": "How hard you push expansion this quarter. High growth increases valuation faster, but also increases hidden risk and scrutiny.",
    "Governance allocation": "How much you invest in controls: model monitoring, audits, documentation, approvals, and incident response. Higher governance reduces risk and improves trust.",
    "Counterfactual testing": "YES means you run stress tests (what-if outcomes) before shipping. NO means you ship faster but risk hidden issues compounding.",
    "Expansion scope": "Narrow focuses on one segment. Balanced expands thoughtfully. Wide expands broadly (more upside, more volatility).",
    "Product focus": "Credit = underwriting risk & fairness scrutiny. Fraud = detection tradeoffs. Advisory = hallucination/explainability risks.",
    "Model strategy": "Open = fast iteration + lower cost, but more governance work. Closed = stable vendor model + higher cost. Hybrid = in-between.",
    "Data policy": "Minimal = safer, slower learning. Balanced = practical. Aggressive = faster learning, higher privacy/regulatory scrutiny.",
    "PR posture": "Transparent builds trust but costs you speed. Quiet is neutral. Defensive can backfire if the market smells avoidance.",
}

# =========================
# Decision Trees (real trees)
# Each tree = nodes with choices -> next node or resolution effects
# =========================
def build_decision_trees():
    # Three “most relevant today” trees:
    # 1) Credit underwriting fairness scrutiny
    # 2) Fraud false positives & customer harm
    # 3) GenAI advisory hallucination incident
    return {
        "credit_fairness_tree": {
            "title": "Underwriting Fairness Challenge",
            "nodes": {
                "start": {
                    "text": "A journalist claims your credit model is denying a protected segment at higher rates. A regulator requests an explanation in 72 hours.",
                    "choices": [
                        ("Publish model card + adverse action rationale + commit to independent audit (slower, safer)",
                         {"next": "audit_or_delay", "effects": {"trust": +3, "governance": +4, "reg_pressure": -3, "valuation_m": -10}}),
                        ("Provide a high-level explanation only (fast, vague)",
                         {"next": "pushback", "effects": {"trust": -2, "governance": +1, "reg_pressure": +3}}),
                        ("Delay and lawyer up (very fast, high risk)",
                         {"next": "investigation", "effects": {"trust": -4, "reg_pressure": +6, "violations": +1, "valuation_m": -8}}),
                    ],
                },
                "audit_or_delay": {
                    "text": "The audit team finds a drift issue in one feature pipeline. Fix now or ship and monitor?",
                    "choices": [
                        ("Freeze approvals for impacted segment, patch, and re-test",
                         {"next": "resolve_good", "effects": {"hidden_risk": -12, "trust": +2, "valuation_m": -12}}),
                        ("Ship patch and monitor live with guardrails",
                         {"next": "resolve_mid", "effects": {"hidden_risk": +4, "trust": -1, "valuation_m": +6}}),
                    ],
                },
                "pushback": {
                    "text": "Regulator replies: 'We need traceability, not marketing.' Market sentiment turns skeptical.",
                    "choices": [
                        ("Escalate to transparency package + logs",
                         {"next": "resolve_mid", "effects": {"governance": +3, "trust": +1, "reg_pressure": -2, "valuation_m": -6}}),
                        ("Stay vague and push growth story",
                         {"next": "investigation", "effects": {"trust": -3, "reg_pressure": +5, "hidden_risk": +6}}),
                    ],
                },
                "investigation": {
                    "text": "Formal investigation opens. You must choose: cooperate fully or fight narrowly?",
                    "choices": [
                        ("Cooperate fully + remediation plan",
                         {"next": "resolve_mid", "effects": {"governance": +4, "reg_pressure": -2, "trust": +1, "valuation_m": -10}}),
                        ("Fight narrowly (limits exposure now, increases probability of penalties later)",
                         {"next": "resolve_bad", "effects": {"trust": -4, "reg_pressure": +6, "violations": +1}}),
                    ],
                },
                "resolve_good": {"text": "You stabilize fairness, restore trust, and turn the incident into a governance win.", "choices": []},
                "resolve_mid":  {"text": "You contain damage, but the tradeoffs show up in your growth curve and scrutiny.", "choices": []},
                "resolve_bad":  {"text": "The narrative hardens against you. Costs rise, and your risk profile worsens.", "choices": []},
            },
        },

        "fraud_fp_tree": {
            "title": "Fraud System Blowback",
            "nodes": {
                "start": {
                    "text": "Your fraud model catches more fraud, but false positives spike. Influencers post 'MirrorWorld locked my account.'",
                    "choices": [
                        ("Add human-in-the-loop review for edge cases (slower, trust-first)",
                         {"next": "review_cost", "effects": {"trust": +2, "governance": +2, "valuation_m": -8, "hidden_risk": -4}}),
                        ("Lower thresholds to reduce complaints (increases fraud leakage)",
                         {"next": "fraud_leak", "effects": {"trust": +1, "valuation_m": -4, "hidden_risk": +5}}),
                        ("Ignore and push expansion (fast, dangerous)",
                         {"next": "meltdown", "effects": {"trust": -3, "reg_pressure": +4, "hidden_risk": +8}}),
                    ],
                },
                "review_cost": {
                    "text": "Costs rise. Do you invest in better explanations and appeals, or keep it minimal?",
                    "choices": [
                        ("Add appeals + transparent reasons",
                         {"next": "resolve_good", "effects": {"trust": +2, "reg_pressure": -2, "valuation_m": -6}}),
                        ("Keep it minimal and hope it fades",
                         {"next": "resolve_mid", "effects": {"trust": -1, "reg_pressure": +2}}),
                    ],
                },
                "fraud_leak": {
                    "text": "Fraud losses rise quietly. Finance is nervous. Do you retrain now or ride it out?",
                    "choices": [
                        ("Retrain with fresh data + counterfactual checks",
                         {"next": "resolve_mid", "effects": {"hidden_risk": -6, "governance": +2, "valuation_m": -7}}),
                        ("Ride it out for one more quarter",
                         {"next": "meltdown", "effects": {"hidden_risk": +7, "trust": -2}}),
                    ],
                },
                "meltdown": {
                    "text": "A wave of account lockouts becomes a headline. Regulators ask about consumer harm controls.",
                    "choices": [
                        ("Freeze rollout + implement safeguards immediately",
                         {"next": "resolve_mid", "effects": {"trust": +1, "governance": +3, "valuation_m": -10, "reg_pressure": +2}}),
                        ("Defensive PR + blame users and bots",
                         {"next": "resolve_bad", "effects": {"trust": -5, "reg_pressure": +6, "violations": +1}}),
                    ],
                },
                "resolve_good": {"text": "You turn a PR threat into a consumer-protection story. Trust rises.", "choices": []},
                "resolve_mid":  {"text": "You stabilize performance with manageable scars.", "choices": []},
                "resolve_bad":  {"text": "Consumer harm narrative sticks. Costs and scrutiny jump.", "choices": []},
            },
        },

        "advisory_hallucination_tree": {
            "title": "Generative Advisory Incident",
            "nodes": {
                "start": {
                    "text": "Your GenAI advisor confidently gives a wrong recommendation. A user loses money and posts receipts online.",
                    "choices": [
                        ("Add confidence gating + citations + 'I might be wrong' behavior (responsible design)",
                         {"next": "controls", "effects": {"governance": +3, "trust": +2, "valuation_m": -8, "hidden_risk": -5}}),
                        ("Keep answers strong but add a disclaimer (fast, risky)",
                         {"next": "disclaimer", "effects": {"trust": -1, "hidden_risk": +4}}),
                        ("Go quiet and remove the feature temporarily (safe but growth hit)",
                         {"next": "pause", "effects": {"trust": +1, "valuation_m": -12, "reg_pressure": -1}}),
                    ],
                },
                "controls": {
                    "text": "Controls reduce harm but slow the vibe. Do you also add audit logs and red-team testing?",
                    "choices": [
                        ("Yes: red-team + logs + incident playbook",
                         {"next": "resolve_good", "effects": {"governance": +3, "hidden_risk": -6, "reg_pressure": -2}}),
                        ("No: keep it light",
                         {"next": "resolve_mid", "effects": {"hidden_risk": +3, "trust": -1}}),
                    ],
                },
                "disclaimer": {
                    "text": "Users call the disclaimer 'legal wallpaper.' Regulators ask about suitability controls.",
                    "choices": [
                        ("Upgrade to suitability checks + guardrails",
                         {"next": "resolve_mid", "effects": {"governance": +3, "trust": +1, "valuation_m": -6}}),
                        ("Defend it publicly as 'user responsibility'",
                         {"next": "resolve_bad", "effects": {"trust": -4, "reg_pressure": +5, "violations": +1}}),
                    ],
                },
                "pause": {
                    "text": "Feature pause cools the outrage. Competitor copies your product. What now?",
                    "choices": [
                        ("Relaunch with safer design",
                         {"next": "resolve_mid", "effects": {"governance": +2, "trust": +1, "valuation_m": -4}}),
                        ("Stay paused and focus on Credit/Fraud",
                         {"next": "resolve_mid", "effects": {"valuation_m": -2, "trust": +1}}),
                    ],
                },
                "resolve_good": {"text": "You set a responsible GenAI standard. Trust becomes your moat.", "choices": []},
                "resolve_mid":  {"text": "You contain the damage, but the market remembers the incident.", "choices": []},
                "resolve_bad":  {"text": "The advisory system becomes a liability. Scrutiny accelerates.", "choices": []},
            },
        },
    }

TREES = build_decision_trees()

# =========================
# State Initialization (randomized starts)
# =========================
def init_state(mode, seed=None):
    if seed is None:
        seed = now_seed()
    rng = make_rng(seed)

    # Randomize starting conditions so runs differ
    base_trust = float(clamp(rng.normal(55, 6), 40, 70))
    base_gov = float(clamp(rng.normal(50, 7), 35, 70))
    base_reg = float(clamp(rng.normal(22, 8), 5, 45))
    base_crisis = float(clamp(rng.normal(8, 3), 2, 15))
    base_hidden = float(clamp(rng.normal(12, 6), 0, 25))

    return {
        "mode": mode,
        "seed": seed,
        "player_name": "",
        "phase": "setup",

        "quarter": 1,
        "max_quarters": 8 if mode == "Standard" else None,  # Endless mode has no cap

        # core metrics
        "valuation_m": 0.0,
        "trust": base_trust,
        "governance": base_gov,
        "reg_pressure": base_reg,
        "crisis_prob": base_crisis,
        "hidden_risk": base_hidden,
        "violations": 0,

        # competitor
        "comp_strength": float(clamp(rng.normal(12, 6), 5, 25)),
        "comp_strategy": "Observing",

        # gameplay
        "product_line": None,
        "seed_m": 0.0,
        "history": [],
        "narrative": ["Welcome to MirrorWorld. Your first decision is your opening move."],
        "game_over": False,
        "end_reason": "",

        # Decision-tree system
        "pending_tree": None,     # tree_key
        "pending_node": None,     # node_id

        "last_decisions": None,
        "rng_state": rng.bit_generator.state,
    }

def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# =========================
# Core mechanics (Bayesian-ish update)
# =========================
def bayesian_crisis_update(state):
    prior = state["crisis_prob"] / 100.0
    signal = (
        0.55 * (state["hidden_risk"] / 100.0) +
        0.20 * (state["reg_pressure"] / 100.0) +
        0.15 * (max(0.0, 60.0 - state["trust"]) / 60.0) +
        0.10 * (max(0.0, 55.0 - state["governance"]) / 55.0)
    )
    signal = clamp(signal, 0.0, 1.0)
    posterior = 0.62 * prior + 0.38 * signal
    state["crisis_prob"] = clamp(posterior * 100.0, 1.0, 95.0)

def value_creation(state, growth, expansion, product_line, model_strategy):
    base = 16.0 + (growth / 100) * 58.0  # baseline

    if expansion == "Wide":
        base *= 1.20
    elif expansion == "Balanced":
        base *= 1.05
    else:
        base *= 0.92

    if product_line == "Fraud":
        base *= 1.10
    elif product_line == "Credit":
        base *= 1.03
    else:
        base *= 1.00

    if model_strategy == "Open":
        base *= 1.07
    elif model_strategy == "Hybrid":
        base *= 1.03
    else:
        base *= 0.99

    return base

def apply_decisions(state, growth, gov_spend, counterfactual_yes, expansion,
                    product_focus, model_strategy, data_policy, pr_posture):
    rng = get_rng(state)

    # governance & trust drift
    state["governance"] = clamp(
        state["governance"] + (gov_spend / 100) * 11.0 - (growth / 100) * 3.0,
        0, 100
    )

    # Counterfactual YES/NO
    if counterfactual_yes:
        state["hidden_risk"] = clamp(state["hidden_risk"] - 6.5, 0, 100)
        state["trust"] = clamp(state["trust"] + 1.8, 0, 100)
        test_cost = 0.08
    else:
        state["hidden_risk"] = clamp(state["hidden_risk"] + 5.0, 0, 100)
        state["trust"] = clamp(state["trust"] - 1.8, 0, 100)
        test_cost = 0.00

    # data policy
    if data_policy == "Minimal":
        state["trust"] = clamp(state["trust"] + 1.2, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] - 1.5, 0, 100)
        data_boost = 0.96
        risk_boost = 0.88
    elif data_policy == "Balanced":
        data_boost = 1.00
        risk_boost = 1.00
    else:  # Aggressive
        state["trust"] = clamp(state["trust"] - 2.0, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] + 4.0, 0, 100)
        data_boost = 1.08
        risk_boost = 1.18

    # PR posture
    if pr_posture == "Transparent":
        state["trust"] = clamp(state["trust"] + 1.0, 0, 100)
        pr_risk = 0.90
    elif pr_posture == "Defensive":
        state["trust"] = clamp(state["trust"] - 1.0, 0, 100)
        pr_risk = 1.08
    else:
        pr_risk = 1.00

    # product risk tuning
    if product_focus == "Credit":
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.5, 0, 100)
        product_risk = 1.12
    elif product_focus == "Fraud":
        product_risk = 1.00
    else:
        state["trust"] = clamp(state["trust"] - 0.6, 0, 100)
        product_risk = 1.08

    trust_factor = 0.86 + (state["trust"] / 100) * 0.28
    gov_factor = 0.86 + (state["governance"] / 100) * 0.24

    created = value_creation(state, growth, expansion, product_focus, model_strategy)
    created *= trust_factor * gov_factor * data_boost
    created *= (1.0 - test_cost)
    created += rng.normal(0, 3.0)

    # Endless mode = easier/lax: small boost, slightly lower downside
    if state["mode"] == "Endless (Lax/Advanced)":
        created *= 1.08

    state["valuation_m"] = max(0.0, state["valuation_m"] + created)

    # hidden risk accumulation
    risk_add = (growth / 100) * 6.0
    risk_add += max(0.0, (70.0 - state["governance"])) / 100.0 * 4.0
    risk_add *= risk_boost * product_risk * pr_risk

    # governance spend reduces risk more in lax mode
    gov_risk_relief = (gov_spend / 100) * (3.5 if state["mode"] == "Endless (Lax/Advanced)" else 3.0)
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add - gov_risk_relief, 0, 100)

    # regulatory pressure growth
    add_reg = max(0.0, (growth - state["governance"])) / 100.0 * 9.0
    if state["mode"] == "Endless (Lax/Advanced)":
        add_reg *= 0.85
    state["reg_pressure"] = clamp(state["reg_pressure"] + add_reg, 0, 100)

    save_rng(state, rng)

# =========================
# Mirror AI competitor agent
# =========================
def update_competitor_agent(state):
    rng = get_rng(state)
    d = state.get("last_decisions") or {}

    growth = d.get("growth", 50)
    counterfactual_yes = d.get("counterfactual_yes", True)
    pr = d.get("pr_posture", "Quiet")
    gov = d.get("gov_spend", 50)
    data_policy = d.get("data_policy", "Balanced")

    risky_fast = (growth >= 70 and (not counterfactual_yes))
    disciplined = (gov >= 60 and counterfactual_yes and pr == "Transparent")

    if risky_fast:
        state["comp_strategy"] = "Regulatory Trap"
    elif disciplined and state["trust"] >= 60:
        state["comp_strategy"] = "Price War"
    elif disciplined:
        state["comp_strategy"] = "Safety-First"
    else:
        state["comp_strategy"] = "Copycat"

    visibility = min(1.0, state["valuation_m"] / 1000.0)
    learn_rate = 2.0 + 6.0 * visibility
    opening = 0.0
    opening += 3.0 if (not counterfactual_yes) else 0.6
    opening += 2.2 if pr == "Defensive" else 0.7
    opening += 2.0 if data_policy == "Aggressive" else 0.6

    comp_gain = learn_rate + opening + rng.normal(0, 1.0)

    # Lax mode competitor grows slower
    if state["mode"] == "Endless (Lax/Advanced)":
        comp_gain *= 0.85

    state["comp_strength"] = clamp(state["comp_strength"] + comp_gain, 0, 100)

    headlines = []
    s = state["comp_strength"]

    if state["comp_strategy"] == "Price War":
        hit = (0.028 + 0.0005 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        headlines.append("⚔️ Mirror AI starts a price war: growth continues, but margins sting.")
    elif state["comp_strategy"] == "Safety-First":
        trust_hit = 1.0 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.0
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI markets itself as safer: your trust gets benchmarked publicly.")
    elif state["comp_strategy"] == "Copycat":
        steal = (0.02 + 0.00035 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI copies your features: differentiation shrinks.")
    else:  # Regulatory Trap
        add = 3.5 + 0.07 * s
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        if (state["hidden_risk"] >= 55 or (not counterfactual_yes)) and rng.random() < (0.25 if state["mode"] == "Endless (Lax/Advanced)" else 0.35):
            state["violations"] += 1
            state["trust"] = clamp(state["trust"] - 3.5, 0, 100)
            headlines.append("📣 Mirror AI escalates: an incident review opens (+1 violation).")
        headlines.append("🧾 Mirror AI files complaints: scrutiny increases.")

    save_rng(state, rng)
    return headlines

# =========================
# Decision-tree trigger logic
# =========================
def should_trigger_tree(state):
    rng = get_rng(state)

    # Higher probability when risk and competitor strength rise
    p = 0.22
    p += 0.16 if state["hidden_risk"] >= 45 else 0.0
    p += 0.12 if state["reg_pressure"] >= 55 else 0.0
    p += 0.10 if state["comp_strength"] >= 45 else 0.0

    # Endless mode triggers a bit more often (more content)
    if state["mode"] == "Endless (Lax/Advanced)":
        p += 0.08

    p = clamp(p, 0.18, 0.70)
    hit = rng.random() < p

    save_rng(state, rng)
    return hit

def pick_tree(state):
    rng = get_rng(state)

    # bias toward tree that matches product focus (makes it feel “smart”)
    product = state.get("product_line") or "Credit"
    options = ["credit_fairness_tree", "fraud_fp_tree", "advisory_hallucination_tree"]
    weights = np.array([1.0, 1.0, 1.0], dtype=float)
    if product == "Credit": weights = np.array([1.6, 0.9, 0.9])
    if product == "Fraud":  weights = np.array([0.9, 1.6, 0.9])
    if product == "Advisory":weights = np.array([0.9, 0.9, 1.6])

    weights = weights / weights.sum()
    idx = int(rng.choice(len(options), p=weights))

    save_rng(state, rng)
    return options[idx]

def apply_effects(state, effects):
    for k, v in effects.items():
        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + float(v))
        elif k == "violations":
            state["violations"] += int(v)
        else:
            state[k] = clamp(state.get(k, 0.0) + float(v), 0.0, 100.0)

# =========================
# End conditions
# =========================
def end_check(state):
    # Standard mode harsher shutdowns; lax mode softer
    shutdown_at = 3 if state["mode"] == "Standard" else 4

    if state["violations"] >= shutdown_at:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents/violations."
        return

    if state["trust"] < (25 if state["mode"] == "Standard" else 18) and state["reg_pressure"] > (75 if state["mode"] == "Standard" else 82):
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under extreme regulatory pressure."
        return

    if state["crisis_prob"] > (70 if state["mode"] == "Standard" else 78):
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."
        return

    if state["mode"] == "Standard" and state["quarter"] > 8:
        state["game_over"] = True
        state["end_reason"] = "Completed 8 quarters."
        return

def win_condition(state):
    # Standard win condition includes trust; lax mode is easier
    if state["mode"] == "Standard":
        return (state["valuation_m"] >= 1000.0) and (state["trust"] >= 70.0) and (state["violations"] < 3)
    return (state["valuation_m"] >= 1000.0)

def score(state):
    valuation_score = min(100.0, (state["valuation_m"] / 1000.0) * 100.0)
    penalty = state["reg_pressure"] * 0.25 + state["crisis_prob"] * 0.55 + state["violations"] * 9.0
    total = valuation_score * 0.52 + state["trust"] * 0.18 + state["governance"] * 0.18 - penalty * 0.10
    return clamp(total, 0.0, 100.0)

# =========================
# Recommended move + hints
# =========================
def recommend_move(state):
    """
    Simple heuristic recommendation that feels like a “coach.”
    """
    rec = {
        "growth": 60,
        "gov_spend": 55,
        "counterfactual_yes": True,
        "expansion": "Balanced",
        "product_focus": state.get("product_line") or "Credit",
        "model_strategy": "Hybrid",
        "data_policy": "Balanced",
        "pr_posture": "Quiet",
        "why": [],
    }

    if state["trust"] < 55:
        rec["pr_posture"] = "Transparent"
        rec["gov_spend"] = 65
        rec["why"].append("Trust is soft. Transparency + governance stabilizes sentiment.")
    if state["reg_pressure"] > 55:
        rec["data_policy"] = "Minimal"
        rec["counterfactual_yes"] = True
        rec["gov_spend"] = max(rec["gov_spend"], 70)
        rec["why"].append("Reg pressure is elevated. Reduce exposure and document decisions.")
    if state["hidden_risk"] > 45:
        rec["counterfactual_yes"] = True
        rec["growth"] = min(rec["growth"], 55)
        rec["why"].append("Hidden risk is compounding. Slow growth briefly to prevent a shock.")
    if state["valuation_m"] < 200 and state["mode"] == "Endless (Lax/Advanced)":
        rec["growth"] = 70
        rec["expansion"] = "Wide"
        rec["why"].append("Early game in lax mode: you can push growth while still learning.")
    if state["comp_strength"] > 55 and state["trust"] >= 60:
        rec["pr_posture"] = "Transparent"
        rec["why"].append("Competitor is strong. Public benchmarks can protect trust.")

    if not rec["why"]:
        rec["why"] = ["Balanced play maximizes long-run survival while keeping growth healthy."]

    return rec

# =========================
# UI
# =========================
st.title("🪞 MirrorWorld — AI FinTech Leadership Simulation")
st.caption("A rubric-aligned simulation with decision trees, an adaptive AI competitor, and real governance tradeoffs.")

# Sidebar: Mode selection + hints
with st.sidebar:
    st.header("Game Settings")

    mode = st.radio(
        "Choose mode",
        ["Standard", "Endless (Lax/Advanced)"],
        help="Standard: 8 quarters, tougher and rubric-driven. Endless: play until you hit $1B (easier)."
    )

    show_hints = st.toggle("Show Hint / Coaching Panel", value=True)
    show_recommendations = st.toggle("Show Recommended Move", value=True)

    st.markdown("---")
    st.subheader("How to Win (quick)")
    st.write("- You can win rounds with speed, but you win the game with **trust + governance**.")
    st.write("- Counterfactual testing (YES) is your safety brake when risk starts compounding.")
    st.write("- Mirror AI adapts. If you repeat risky patterns, it attacks through regulators and narrative.")

# State creation / reset
if "state" not in st.session_state or st.session_state.state.get("mode") != mode:
    st.session_state.state = init_state(mode)

state = st.session_state.state

# Layout: main + metrics
left, right = st.columns([1.25, 0.75], gap="large")

# =========================
# RIGHT: Metrics Panel  (Fix 1 + Fix 2 here)
# =========================
with right:
    st.subheader("Real-Time Metrics")

    # FIX 1: Use 2 columns per row (instead of 3)
    r1c1, r1c2 = st.columns(2)
    r1c1.metric("Valuation (USD, millions)", fmt_m(state["valuation_m"]))
    r1c2.metric("Trust (out of 100)", f"{state['trust']:.0f}")

    r2c1, r2c2 = st.columns(2)
    r2c1.metric("Governance (out of 100)", f"{state['governance']:.0f}")
    r2c2.metric("Reg Pressure", pressure_label(state["reg_pressure"]))

    # Crisis probability on its own line (prevents truncation)
    st.metric("Crisis Probability", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")

    st.markdown("---")
    st.metric("Mirror AI Strength (out of 100)", f"{state['comp_strength']:.0f}")
    st.write(f"**Mirror AI Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden Risk (latent):** {state['hidden_risk']:.0f} / 100")
    st.write(f"**Violations/Incidents:** {state['violations']}")
    st.write(f"**Score:** {score(state):.1f} / 100")

    st.markdown("---")
    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f} / 100")
        st.success("✅ Win condition met" if win_condition(state) else "❌ Win condition not met")
    else:
        if state["mode"] == "Standard":
            st.info("Goal: reach **$1B** within **8 quarters** while maintaining trust and avoiding shutdown.")
        else:
            st.info("Goal: play until you reach **$1B** (you can stop whenever).")

# =========================
# LEFT: Gameplay
# =========================
with left:
    # Setup phase
    if state["phase"] == "setup":
        st.subheader("Setup: Your Identity + Your First Strategic Commitment")

        player_name = st.text_input("Enter your name (for personalized story)", value=state["player_name"])
        seed_m = st.select_slider("Choose seed funding (millions)", options=[5, 10, 20, 35, 50], value=20)
        product = st.radio("Choose your first product line", ["Credit", "Fraud", "Advisory"], horizontal=True)

        st.info("Seed funding increases your starting valuation, but also increases visibility and scrutiny.")

        if st.button("✅ Start Game", use_container_width=True):
            state["player_name"] = player_name.strip() if player_name.strip() else "Leader"
            state["seed_m"] = float(seed_m)
            state["product_line"] = product

            # Start valuation at 0 then seed converts to initial operating valuation
            state["valuation_m"] = float(seed_m) * 6.0
            state["reg_pressure"] = clamp(state["reg_pressure"] + float(seed_m) / 5.0, 0, 100)

            state["phase"] = "play"
            state["narrative"] = [
                f"Welcome, {state['player_name']}. You just closed a ${seed_m}M seed round.",
                f"You’re launching in **{product}** first. Mirror AI is watching and learning."
            ]
            st.session_state.state = state
            st.rerun()

    else:
        # Coaching panel
        if show_hints or show_recommendations:
            rec = recommend_move(state)

            with st.expander("🧠 Coaching Panel (optional)", expanded=False):
                if show_recommendations:
                    st.markdown("**Recommended move (this quarter):**")
                    st.write(f"- Growth aggressiveness: **{rec['growth']}**")
                    st.write(f"- Governance allocation: **{rec['gov_spend']}**")
                    st.write(f"- Counterfactual testing: **{'YES' if rec['counterfactual_yes'] else 'NO'}**")
                    st.write(f"- Expansion: **{rec['expansion']}**")
                    st.write(f"- Product focus: **{rec['product_focus']}**")
                    st.write(f"- Model strategy: **{rec['model_strategy']}**")
                    st.write(f"- Data policy: **{rec['data_policy']}**")
                    st.write(f"- PR posture: **{rec['pr_posture']}**")
                    st.markdown("**Why this helps:**")
                    for w in rec["why"]:
                        st.write(f"- {w}")

                if show_hints:
                    st.markdown("**Winning heuristics:**")
                    st.write("- If **Hidden Risk > 45**: Counterfactual YES + raise governance + reduce growth one quarter.")
                    st.write("- If **Trust < 55**: Transparent posture + governance investment beats defensive messaging.")
                    st.write("- If **Reg Pressure > 60**: Minimal data + documentation + model cards reduce escalation.")

        # Decision tree pending (choose-your-own-adventure)
        if state["pending_tree"] and state["pending_node"] and not state["game_over"]:
            tree = TREES[state["pending_tree"]]
            node = tree["nodes"][state["pending_node"]]

            st.warning(f"📌 Decision Tree: {tree['title']}")
            st.write(node["text"])
            st.markdown("**Choose your move:**")

            if not node["choices"]:
                st.success("Resolution reached. Continue when ready.")
                if st.button("Continue ▶️", use_container_width=True):
                    state["pending_tree"] = None
                    state["pending_node"] = None
                    st.session_state.state = state
                    st.rerun()
            else:
                for i, (label, payload) in enumerate(node["choices"], start=1):
                    if st.button(f"Option {i}: {label}", use_container_width=True):
                        # apply effects and move to next node
                        apply_effects(state, payload.get("effects", {}))
                        bayesian_crisis_update(state)
                        end_check(state)

                        # narrative update
                        state["narrative"].insert(0, f"{state['player_name']} chose: {label}")

                        nxt = payload.get("next")
                        state["pending_node"] = nxt
                        st.session_state.state = state
                        st.rerun()

        else:
            # Main decisions
            st.subheader(f"Quarter {state['quarter']}" + ("/8" if state["mode"] == "Standard" else ""))

            st.markdown("### Your Decisions (this quarter)")
            growth = st.slider("Growth aggressiveness", 0, 100, 65, help=LEVER_HELP["Growth aggressiveness"])
            gov_spend = st.slider("Governance allocation", 0, 100, 55, help=LEVER_HELP["Governance allocation"])

            counterfactual_yes = st.toggle("Counterfactual testing (YES/NO)", value=True, help=LEVER_HELP["Counterfactual testing"])

            expansion = st.radio("Expansion scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True,
                                 help=LEVER_HELP["Expansion scope"])

            st.markdown("### AI & Strategy Levers (what you are actually changing)")
            c1, c2 = st.columns(2)

            with c1:
                product_focus = st.selectbox("Product focus", ["Credit", "Fraud", "Advisory"],
                                             index=["Credit", "Fraud", "Advisory"].index(state["product_line"]),
                                             help=LEVER_HELP["Product focus"])
                model_strategy = st.selectbox("Model strategy", ["Open", "Hybrid", "Closed"], index=1,
                                              help=LEVER_HELP["Model strategy"])
            with c2:
                data_policy = st.selectbox("Data policy", ["Minimal", "Balanced", "Aggressive"], index=1,
                                           help=LEVER_HELP["Data policy"])
                pr_posture = st.selectbox("PR posture", ["Transparent", "Quiet", "Defensive"], index=1,
                                          help=LEVER_HELP["PR posture"])

            st.markdown("---")
            run_col, reset_col = st.columns(2)

            with run_col:
                if st.button("▶️ Run Quarter", use_container_width=True, disabled=state["game_over"]):
                    # save decisions
                    state["last_decisions"] = {
                        "growth": growth,
                        "gov_spend": gov_spend,
                        "counterfactual_yes": counterfactual_yes,
                        "expansion": expansion,
                        "product_focus": product_focus,
                        "model_strategy": model_strategy,
                        "data_policy": data_policy,
                        "pr_posture": pr_posture,
                    }

                    # Apply your choices
                    apply_decisions(state, growth, gov_spend, counterfactual_yes, expansion,
                                    product_focus, model_strategy, data_policy, pr_posture)

                    # Competitor acts
                    comp_headlines = update_competitor_agent(state)

                    # Risk update
                    bayesian_crisis_update(state)

                    # Potentially trigger a decision tree
                    triggered = should_trigger_tree(state)
                    if triggered:
                        tree_key = pick_tree(state)
                        state["pending_tree"] = tree_key
                        state["pending_node"] = "start"
                        tree_title = TREES[tree_key]["title"]
                        state["narrative"].insert(0, f"📌 A new situation unfolds: {tree_title}.")

                    # End checks
                    end_check(state)

                    # Narrative flavor (short, not blocks)
                    q_line = f"Quarter {state['quarter']} executes: growth={growth}, governance={gov_spend}, counterfactual={'YES' if counterfactual_yes else 'NO'}."
                    state["narrative"].insert(0, q_line)
                    for h in comp_headlines:
                        state["narrative"].insert(0, h)

                    # Log
                    state["history"].append({
                        "Quarter": state["quarter"],
                        "Growth": growth,
                        "Governance": gov_spend,
                        "Counterfactual": "YES" if counterfactual_yes else "NO",
                        "Expansion": expansion,
                        "Product": product_focus,
                        "Model": model_strategy,
                        "DataPolicy": data_policy,
                        "PR": pr_posture,
                        "MirrorAI_Strategy": state["comp_strategy"],
                        "MirrorAI_Strength": round(state["comp_strength"], 1),
                        "Valuation($M)": round(state["valuation_m"], 1),
                        "Trust": round(state["trust"], 1),
                        "GovernanceScore": round(state["governance"], 1),
                        "RegPressure": round(state["reg_pressure"], 1),
                        "CrisisProb(%)": round(state["crisis_prob"], 1),
                        "HiddenRisk": round(state["hidden_risk"], 1),
                        "Violations": state["violations"],
                    })

                    # advance quarter if standard and no pending decision tree and not game over
                    if (not state["game_over"]) and (state["mode"] == "Standard") and (state["pending_tree"] is None):
                        state["quarter"] += 1
                        if state["quarter"] > 8:
                            state["game_over"] = True
                            state["end_reason"] = "Completed 8 quarters."
                    elif (not state["game_over"]) and (state["mode"] != "Standard") and (state["pending_tree"] is None):
                        state["quarter"] += 1  # endless continues

                    # If you hit $1B in endless, let it keep going but celebrate
                    if (not state["game_over"]) and state["mode"] != "Standard" and state["valuation_m"] >= 1000:
                        state["narrative"].insert(0, "🏆 You hit $1B valuation. You can keep playing, or stop and screenshot your win.")

                    st.session_state.state = state
                    st.rerun()

            with reset_col:
                if st.button("🔄 New Run (random start)", use_container_width=True):
                    st.session_state.state = init_state(mode)
                    st.rerun()

            st.markdown("### Story Feed (choose-your-own-adventure)")
            for line in state["narrative"][:10]:
                st.write(f"- {line}")

            st.markdown("### Run Log")
            if state["history"]:
                st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
            else:
                st.info("Run your first quarter to generate the log.")

# App.py — MirrorWorld (Streamlit)
# A rubric-aligned AI FinTech leadership simulation with:
# - Player name + randomized starting conditions (no two runs identical)
# - Two modes: Standard (8 quarters, harder) + Advanced (endless, more lax)
# - Counterfactual testing as YES/NO
# - Choose-your-own-adventure decision trees (3 core trees) + mini-events
# - Adaptive AI competitor (“Mirror AI”) that reacts to your behavior
# - Recommended move + hints (optional) without talking down to players
# - Clear in-app directions + tooltips
# - Metrics layout fix for mobile + no duplicate widget IDs (keys everywhere)

import streamlit as st
import numpy as np
import pandas as pd

# -----------------------------
# Page + CSS (mobile metrics fix)
# -----------------------------
st.set_page_config(page_title="MirrorWorld", layout="wide")

st.markdown(
    """
    <style>
    /* Slightly reduce overall base size for mobile readability */
    html, body, [class*="css"]  { font-size: 15px; }

    /* Streamlit metric label/value sizing (best-effort CSS hooks) */
    div[data-testid="stMetricLabel"] > div { font-size: 0.80rem !important; }
    div[data-testid="stMetricValue"] > div { font-size: 1.25rem !important; }
    div[data-testid="stMetricDelta"] > div { font-size: 0.85rem !important; }

    /* Tighten vertical spacing a bit */
    .block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }

    /* Make headers wrap nicely on smaller screens */
    h1, h2, h3 { word-break: break-word; }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, lo, hi):
    return float(max(lo, min(hi, x)))

def pressure_label(p):
    p = float(p)
    if p >= 80: return "Very High"
    if p >= 60: return "High"
    if p >= 40: return "Moderate"
    if p >= 20: return "Low"
    return "Very Low"

def risk_label(p):
    p = float(p)
    if p >= 70: return "Critical"
    if p >= 50: return "Elevated"
    if p >= 30: return "Moderate"
    return "Low"

def fmt_m(x):
    return f"${x:,.0f}M"

def explain(text):
    st.caption(text)

# -----------------------------
# Game Model (state init)
# -----------------------------
def init_state(seed=None):
    rng = np.random.default_rng(seed if seed is not None else np.random.SeedSequence().entropy)

    # Randomized starting conditions (bounded, plausible)
    trust = rng.normal(55, 8)
    gov = rng.normal(50, 10)
    reg = rng.normal(22, 10)
    crisis = rng.normal(9, 4)
    hidden = rng.normal(12, 6)

    state = {
        "phase": "setup",
        "player_name": "",
        "mode": "Standard",  # Standard or Advanced
        "max_quarters": 8,   # Standard = 8, Advanced = None (endless)
        "quarter": 1,

        # Starts at 0, then seed round sets it
        "valuation_m": 0.0,

        # Core metrics
        "trust": clamp(trust, 30, 75),
        "governance": clamp(gov, 25, 80),
        "reg_pressure": clamp(reg, 5, 55),
        "crisis_prob": clamp(crisis, 3, 20),
        "hidden_risk": clamp(hidden, 0, 30),
        "violations": 0,

        # Player identity / initial choices
        "seed_m": 0.0,
        "product_line": None,

        # Adaptive competitor
        "comp_strength": clamp(rng.normal(12, 5), 5, 25),
        "comp_strategy": "Observing",

        # Narrative + logs
        "headlines": ["Welcome to MirrorWorld. Choose your seed + first product to begin."],
        "history": [],

        # Adventure system
        "pending_tree": None,     # dict: decision tree node
        "tree_memory": {},        # remembers past choices for callbacks
        "pending_event": None,    # mini-event (small decision)

        # Hints & UI
        "show_hints": True,
        "show_recommendations": True,
        "tutorial_on": True,
        "tutorial_step": 1,

        # RNG persistence
        "rng_state": rng.bit_generator.state,

        # Game over
        "game_over": False,
        "end_reason": "",
    }
    return state

def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# -----------------------------
# Core Mechanics
# -----------------------------
def bayesian_crisis_update(state):
    # Simple posterior update: prior blended with “signals”
    prior = state["crisis_prob"] / 100.0
    signal = (
        0.45 * (state["hidden_risk"] / 100.0) +
        0.20 * (state["reg_pressure"] / 100.0) +
        0.20 * (max(0.0, 60.0 - state["trust"]) / 60.0) +
        0.15 * (max(0.0, 55.0 - state["governance"]) / 55.0)
    )
    signal = clamp(signal, 0.0, 1.0)
    posterior = 0.62 * prior + 0.38 * signal
    state["crisis_prob"] = clamp(posterior * 100.0, 1.0, 95.0)

def value_creation(state, growth, expansion, product_focus, model_strategy):
    """
    Creates valuation growth per quarter (in $M).
    Growth lever is primary; other levers modulate.
    """
    base = 14.0 + (growth / 100.0) * 62.0  # 14..76

    # Expansion scope
    if expansion == "Wide":
        base *= 1.18
    elif expansion == "Balanced":
        base *= 1.06
    else:  # Narrow
        base *= 0.92

    # Product economics and scrutiny
    if product_focus == "Fraud":
        base *= 1.10
    elif product_focus == "Credit":
        base *= 1.04
    else:  # Advisory
        base *= 1.00

    # Model strategy tradeoffs
    if model_strategy == "Open":
        base *= 1.08
    elif model_strategy == "Hybrid":
        base *= 1.03
    else:  # Closed
        base *= 0.99

    return base

def apply_decisions(state, *, growth, gov_spend, counterfactual_yes, expansion,
                    product_focus, model_strategy, data_policy, pr_posture):
    rng = get_rng(state)

    # Governance changes: spending helps; growth pulls org toward speed
    state["governance"] = clamp(
        state["governance"] + (gov_spend / 100.0) * 10.0 - (growth / 100.0) * 3.0,
        0, 100
    )

    # Counterfactual testing YES/NO: impacts hidden risk + trust, and costs time
    if counterfactual_yes:
        state["hidden_risk"] = clamp(state["hidden_risk"] - 7.0, 0, 100)
        state["trust"] = clamp(state["trust"] + 1.6, 0, 100)
        test_cost = 0.08
    else:
        state["hidden_risk"] = clamp(state["hidden_risk"] + 5.5, 0, 100)
        state["trust"] = clamp(state["trust"] - 1.8, 0, 100)
        test_cost = 0.00

    # Data policy: higher returns, higher scrutiny
    if data_policy == "Minimal":
        state["trust"] = clamp(state["trust"] + 1.2, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] - 2.0, 0, 100)
        data_boost = 0.96
        risk_boost = 0.88
    elif data_policy == "Balanced":
        data_boost = 1.00
        risk_boost = 1.00
    else:  # Aggressive
        state["trust"] = clamp(state["trust"] - 1.8, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] + 4.0, 0, 100)
        data_boost = 1.08
        risk_boost = 1.18

    # PR posture: narrative management
    if pr_posture == "Transparent":
        state["trust"] = clamp(state["trust"] + 1.0, 0, 100)
        pr_risk = 0.92
    elif pr_posture == "Defensive":
        state["trust"] = clamp(state["trust"] - 0.8, 0, 100)
        pr_risk = 1.06
    else:  # Quiet
        pr_risk = 1.00

    # Product focus: credit tends to face more regulation; advisory can hit trust if sloppy
    if product_focus == "Credit":
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.4, 0, 100)
        product_risk = 1.10
    elif product_focus == "Fraud":
        product_risk = 1.00
    else:  # Advisory
        state["trust"] = clamp(state["trust"] - 0.6, 0, 100)
        product_risk = 1.05

    # Multipliers
    trust_factor = 0.86 + (state["trust"] / 100.0) * 0.30
    gov_factor = 0.86 + (state["governance"] / 100.0) * 0.25

    created = value_creation(state, growth, expansion, product_focus, model_strategy)
    created *= trust_factor * gov_factor * data_boost
    created *= (1.0 - test_cost)
    created += rng.normal(0, 3.2)

    # Apply valuation growth
    state["valuation_m"] = max(0.0, state["valuation_m"] + created)

    # Hidden risk accumulates with speed; governance & testing reduce it
    risk_add = (growth / 100.0) * 6.5
    risk_add += max(0.0, (70.0 - state["governance"])) / 100.0 * 4.5
    risk_add *= risk_boost * product_risk * pr_risk
    risk_add -= (gov_spend / 100.0) * 2.8
    if counterfactual_yes:
        risk_add -= 2.0
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add, 0, 100)

    # Regulatory pressure tends to rise when growth outpaces governance
    state["reg_pressure"] = clamp(
        state["reg_pressure"] + max(0.0, (growth - state["governance"])) / 100.0 * 9.0,
        0, 100
    )

    # Small random incident chance when risky
    incident_prob = 0.02 + 0.003 * (state["hidden_risk"] / 10.0)
    incident_prob += 0.02 if not counterfactual_yes else 0.0
    incident_prob += 0.02 if data_policy == "Aggressive" else 0.0
    incident_prob = clamp(incident_prob, 0.02, 0.22)

    if rng.random() < incident_prob:
        state["violations"] += 1
        state["trust"] = clamp(state["trust"] - rng.uniform(2.5, 6.5), 0, 100)

    save_rng(state, rng)

# -----------------------------
# Adaptive Competitor (“Mirror AI”)
# -----------------------------
def update_competitor(state, last_decisions):
    """
    Competitor adapts to your behavior and impacts valuation/trust/reg pressure.
    """
    rng = get_rng(state)

    growth = last_decisions["growth"]
    counterfactual_yes = last_decisions["counterfactual_yes"]
    gov = last_decisions["gov_spend"]
    data_policy = last_decisions["data_policy"]
    pr = last_decisions["pr_posture"]

    risky_fast = (growth >= 70 and (not counterfactual_yes))
    disciplined = (gov >= 60 and counterfactual_yes and pr == "Transparent")

    # Choose strategy
    if risky_fast:
        strat = "Regulatory Trap"
    elif disciplined and state["trust"] >= 60:
        strat = "Price War"
    elif disciplined:
        strat = "Safety-First"
    else:
        strat = "Copycat"

    state["comp_strategy"] = strat

    # Strength gains (learning from your visibility)
    visibility = min(1.0, state["valuation_m"] / 1000.0)
    learn_rate = 2.0 + 6.0 * visibility

    opening = 0.0
    opening += 3.0 if not counterfactual_yes else 0.5
    opening += 2.0 if pr == "Defensive" else 0.7
    opening += 2.0 if data_policy == "Aggressive" else 0.6

    comp_gain = learn_rate + opening + rng.normal(0, 1.0)
    state["comp_strength"] = clamp(state["comp_strength"] + comp_gain, 0, 100)

    # Apply impacts
    s = state["comp_strength"]
    headlines = []

    if strat == "Price War":
        hit = (0.02 + 0.0006 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        if pr == "Transparent":
            state["trust"] = clamp(state["trust"] + 0.6, 0, 100)
        headlines.append("⚔️ Mirror AI starts a price war: growth slows unless you differentiate.")

    elif strat == "Safety-First":
        trust_hit = 0.9 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.2
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI markets ‘safer by design’: trust becomes a competitive battlefield.")

    elif strat == "Copycat":
        steal = (0.018 + 0.00045 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI copies your feature: differentiation erodes.")

    else:  # Regulatory Trap
        add = 4.0 + 0.08 * s
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        if state["hidden_risk"] >= 50 or not counterfactual_yes:
            if rng.random() < 0.28:
                state["violations"] += 1
                state["trust"] = clamp(state["trust"] - 4.0, 0, 100)
                headlines.append("📣 A complaint triggers an additional review (+1 incident).")
        headlines.append("🧾 Mirror AI sets a regulatory trap: scrutiny intensifies.")

    save_rng(state, rng)
    return headlines

# -----------------------------
# Decision Trees (3 relevant ones)
# -----------------------------
def build_decision_trees():
    """
    Choose-your-own-adventure trees aligned to today’s market:
    1) Credit & Underwriting fairness scrutiny
    2) Fraud detection false-positive blowback
    3) GenAI advisory hallucination + suitability risk
    Each tree returns nodes with: id, title, story, choices[(label, effects, next_id)]
    """
    trees = {}

    # Tree 1: Credit / Underwriting scrutiny
    trees["credit_tree"] = {
        "root": {
            "id": "c1",
            "title": "Underwriting Audit: Fairness Challenge",
            "story": "A watchdog report claims your approvals vary across segments. The story is gaining traction.",
            "choices": [
                ("Publish a fairness dashboard + pause one segment temporarily",
                 {"trust": +3, "governance": +4, "valuation_m": -10, "reg_pressure": -2, "hidden_risk": -6}, "c2"),
                ("Keep the model live, promise improvements later",
                 {"trust": -2, "governance": +1, "reg_pressure": +3, "hidden_risk": +5}, "c3"),
                ("Aggressively dispute the report and go defensive",
                 {"trust": -5, "reg_pressure": +6, "hidden_risk": +3}, "c4"),
            ],
        },
        "c2": {
            "id": "c2",
            "title": "The Follow-Up Question",
            "story": "Regulators ask: can you explain decisions at an individual level—clearly and consistently?",
            "choices": [
                ("Ship model cards + reason codes + appeal workflow",
                 {"governance": +4, "trust": +2, "valuation_m": -8, "reg_pressure": -4}, None),
                ("Provide a high-level methodology only",
                 {"governance": +1, "trust": -1, "reg_pressure": +2}, None),
            ],
        },
        "c3": {
            "id": "c3",
            "title": "The Slow Burn",
            "story": "Complaints rise quietly. Nothing breaks today… but the risk is compounding.",
            "choices": [
                ("Run counterfactual tests retroactively and recalibrate thresholds",
                 {"hidden_risk": -8, "governance": +2, "valuation_m": -6, "trust": +1}, None),
                ("Do nothing and focus on growth",
                 {"hidden_risk": +10, "trust": -3, "reg_pressure": +4}, None),
            ],
        },
        "c4": {
            "id": "c4",
            "title": "Narrative Backfires",
            "story": "The defensive posture becomes the headline. Now people ask what you’re hiding.",
            "choices": [
                ("Reverse course: transparency pivot + independent audit",
                 {"trust": +2, "governance": +3, "valuation_m": -10, "reg_pressure": -1}, None),
                ("Double down and lawyer up",
                 {"trust": -3, "reg_pressure": +6, "violations": +1}, None),
            ],
        },
    }

    # Tree 2: Fraud detection false positives
    trees["fraud_tree"] = {
        "root": {
            "id": "f1",
            "title": "Fraud Spike: False Positives vs Losses",
            "story": "A fraud wave hits. Tightening rules stops fraud—but freezes legitimate customers too.",
            "choices": [
                ("Tighten aggressively for 1 quarter, then retrain with feedback",
                 {"valuation_m": +6, "trust": -2, "hidden_risk": +3}, "f2"),
                ("Balance: add human-in-the-loop for edge cases",
                 {"trust": +2, "governance": +2, "valuation_m": -4, "hidden_risk": -2}, "f3"),
                ("Loosen to protect UX and accept higher fraud losses",
                 {"valuation_m": +3, "hidden_risk": +7, "reg_pressure": +2}, "f4"),
            ],
        },
        "f2": {
            "id": "f2",
            "title": "Customer Backlash",
            "story": "Social posts show people locked out of accounts. The story is spreading.",
            "choices": [
                ("Issue immediate remediation + transparency report",
                 {"trust": +3, "valuation_m": -6, "governance": +2, "reg_pressure": -1}, None),
                ("Quietly fix behind the scenes",
                 {"trust": -1, "reg_pressure": +2, "hidden_risk": +2}, None),
            ],
        },
        "f3": {
            "id": "f3",
            "title": "Ops Load",
            "story": "Human review improves fairness, but staffing costs increase.",
            "choices": [
                ("Automate reviewer assist with guardrails + sampling audits",
                 {"governance": +3, "hidden_risk": -4, "valuation_m": -3, "trust": +1}, None),
                ("Remove human review to reduce costs",
                 {"valuation_m": +4, "trust": -2, "hidden_risk": +6}, None),
            ],
        },
        "f4": {
            "id": "f4",
            "title": "Losses vs Trust",
            "story": "Fraud losses climb. Partners ask if your controls are weakening.",
            "choices": [
                ("Rebuild controls with phased rollouts + counterfactual checks",
                 {"governance": +3, "hidden_risk": -5, "valuation_m": -5, "trust": +1}, None),
                ("Hope the wave ends",
                 {"hidden_risk": +8, "reg_pressure": +3, "trust": -2}, None),
            ],
        },
    }

    # Tree 3: GenAI advisory hallucination + suitability
    trees["advisory_tree"] = {
        "root": {
            "id": "a1",
            "title": "GenAI Advice Goes Viral",
            "story": "A screenshot circulates: your advisor made a confident claim that appears incorrect.",
            "choices": [
                ("Add confidence gating + citations and temporarily restrict scope",
                 {"trust": +3, "governance": +3, "valuation_m": -8, "hidden_risk": -5}, "a2"),
                ("Keep it live and patch prompts quietly",
                 {"trust": -2, "hidden_risk": +6, "reg_pressure": +2}, "a3"),
                ("Blame user misuse and go defensive",
                 {"trust": -5, "reg_pressure": +5, "violations": +1}, "a4"),
            ],
        },
        "a2": {
            "id": "a2",
            "title": "Suitability Question",
            "story": "Regulators ask: how do you ensure advice is appropriate to the customer’s profile?",
            "choices": [
                ("Add suitability checks + disclosure + human escalation paths",
                 {"governance": +4, "trust": +2, "reg_pressure": -3, "valuation_m": -6}, None),
                ("Add a disclaimer only",
                 {"trust": -1, "reg_pressure": +2, "hidden_risk": +3}, None),
            ],
        },
        "a3": {
            "id": "a3",
            "title": "Second Incident",
            "story": "A second screenshot appears. Now it looks systemic.",
            "choices": [
                ("Roll back features and publish what changed",
                 {"trust": +2, "valuation_m": -10, "governance": +2, "hidden_risk": -4}, None),
                ("Keep going—growth first",
                 {"trust": -3, "hidden_risk": +10, "reg_pressure": +4}, None),
            ],
        },
        "a4": {
            "id": "a4",
            "title": "Narrative Escalation",
            "story": "Media frames it as “AI advice without accountability.”",
            "choices": [
                ("Independent audit + transparency pivot",
                 {"trust": +2, "governance": +3, "valuation_m": -8, "reg_pressure": -1}, None),
                ("Litigate and delay disclosures",
                 {"trust": -3, "reg_pressure": +6, "violations": +1}, None),
            ],
        },
    }

    return trees

TREES = build_decision_trees()

def pick_tree_for_product(product_line):
    if product_line == "Credit":
        return "credit_tree"
    if product_line == "Fraud":
        return "fraud_tree"
    return "advisory_tree"

def apply_effects(state, effects):
    for k, v in effects.items():
        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + float(v))
        elif k == "violations":
            state["violations"] += int(v)
        else:
            state[k] = clamp(state.get(k, 0.0) + float(v), 0.0, 100.0)

def maybe_trigger_tree(state):
    """
    Trigger a decision tree occasionally, weighted by risk/reg pressure/competitor strength.
    In Advanced mode, slightly less punishing and more frequent (more “gameplay”).
    """
    rng = get_rng(state)

    base = 0.22
    base += 0.14 if state["hidden_risk"] >= 45 else 0.0
    base += 0.10 if state["reg_pressure"] >= 55 else 0.0
    base += 0.10 if state["comp_strength"] >= 45 else 0.0
    if state["mode"] == "Advanced":
        base += 0.06

    p = clamp(base, 0.15, 0.65)
    trigger = rng.random() < p

    save_rng(state, rng)
    if not trigger:
        return None

    tree_key = pick_tree_for_product(state["product_line"])
    return {"tree_key": tree_key, "node_id": "root"}

# -----------------------------
# Mini Events (quick, lightweight)
# -----------------------------
def maybe_trigger_mini_event(state):
    rng = get_rng(state)
    p = 0.18
    p += 0.10 if state["hidden_risk"] >= 55 else 0.0
    p += 0.08 if state["reg_pressure"] >= 60 else 0.0
    p = clamp(p, 0.10, 0.50)

    if rng.random() > p:
        save_rng(state, rng)
        return None

    templates = [
        {
            "title": "Partner Due Diligence Call",
            "setup": "A strategic partner asks about governance controls and incident response.",
            "choices": [
                ("Share governance KPIs + incident playbook (transparent)",
                 {"trust": +1.5, "governance": +2.0, "reg_pressure": -2.0, "valuation_m": -4.0}),
                ("Give high-level answers only",
                 {"trust": -0.8, "reg_pressure": +1.5}),
                ("Deflect and push for commercial terms first",
                 {"trust": -2.0, "reg_pressure": +2.5}),
            ],
        },
        {
            "title": "Model Monitoring Alert",
            "setup": "Monitoring flags a new edge-case drift. It’s subtle—right now.",
            "choices": [
                ("Pause rollout and investigate",
                 {"hidden_risk": -6.0, "valuation_m": -5.0, "governance": +1.5}),
                ("Patch quickly and keep shipping",
                 {"hidden_risk": +3.5, "valuation_m": +3.0}),
                ("Ignore it",
                 {"hidden_risk": +7.5, "trust": -2.0}),
            ],
        },
        {
            "title": "Public Narrative Swing",
            "setup": "A popular creator posts about your AI product. Tone could go either way.",
            "choices": [
                ("Engage with transparency and specifics",
                 {"trust": +2.0, "valuation_m": +2.0}),
                ("Stay quiet",
                 {"trust": -0.5}),
                ("Respond defensively",
                 {"trust": -2.5, "reg_pressure": +1.0}),
            ],
        },
    ]

    ev = templates[int(rng.integers(0, len(templates)))]
    save_rng(state, rng)
    return ev

# -----------------------------
# End / Score / Win
# -----------------------------
def end_check(state):
    # Advanced mode is more lax: allow 4 violations before shutdown, and crisis threshold higher
    max_violations = 3 if state["mode"] == "Standard" else 4
    crisis_cap = 70 if state["mode"] == "Standard" else 78

    if state["violations"] >= max_violations:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents."
    elif state["trust"] < 25 and state["reg_pressure"] > 75:
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under high regulatory pressure."
    elif state["crisis_prob"] > crisis_cap:
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."
    else:
        # Standard ends at 8 quarters
        if state["mode"] == "Standard" and state["quarter"] > state["max_quarters"]:
            state["game_over"] = True
            state["end_reason"] = "Completed 8 quarters."

def score(state):
    valuation_score = min(100.0, (state["valuation_m"] / 1000.0) * 100.0)
    penalty = state["reg_pressure"] * 0.25 + state["crisis_prob"] * 0.55 + state["violations"] * 10.0
    total = valuation_score * 0.52 + state["trust"] * 0.18 + state["governance"] * 0.18 - penalty * 0.10
    return clamp(total, 0.0, 100.0)

def win_condition(state):
    # Win is unicorn + trust threshold and no shutdown
    return (state["valuation_m"] >= 1000.0) and (state["trust"] >= 70.0) and (not state["game_over"])

# -----------------------------
# Recommendations (non-cheesy)
# -----------------------------
def recommend_move(state):
    """
    Suggest a move based on current state.
    It's a hint, not a command.
    """
    recs = []

    # If trust is low, transparency & governance should matter
    if state["trust"] < 50:
        recs.append("Consider a more Transparent posture and/or more Governance allocation to stabilize trust.")

    # If hidden risk is high, counterfactual testing is important
    if state["hidden_risk"] >= 45:
        recs.append("Hidden risk is compounding—counterfactual testing YES can slow crises and protect trust.")

    # If regulatory pressure is high, scale more carefully
    if state["reg_pressure"] >= 60:
        recs.append("Reg pressure is high—avoid ‘Wide’ expansion until governance recovers.")

    # Competitor pressure
    if state["comp_strength"] >= 55:
        recs.append("Mirror AI is strong—differentiation via governance + transparency tends to outperform pure speed.")

    if not recs:
        recs.append("Your metrics are stable—this is a good time to expand carefully while keeping counterfactual testing on.")

    return recs[:3]

# -----------------------------
# UI: Title
# -----------------------------
st.title("🪞 MirrorWorld — AI FinTech Leadership Simulation")
st.caption("A playful, rubric-aligned simulation with decision trees, an adaptive AI competitor, and real governance tradeoffs.")

# -----------------------------
# Session State
# -----------------------------
if "state" not in st.session_state:
    st.session_state.state = init_state()

state = st.session_state.state

# -----------------------------
# Sidebar: Controls + Tutorial Wizard
# -----------------------------
with st.sidebar:
    st.subheader("Controls")

    # Player name for personalization
    state["player_name"] = st.text_input(
        "Player name (for story)",
        value=state.get("player_name", ""),
        key="player_name_input"
    )

    # Mode selection
    mode = st.radio(
        "Mode",
        options=["Standard (8 quarters, tougher)", "Advanced (endless, more forgiving)"],
        index=0 if state["mode"] == "Standard" else 1,
        key="mode_radio"
    )
    state["mode"] = "Standard" if mode.startswith("Standard") else "Advanced"
    state["max_quarters"] = 8 if state["mode"] == "Standard" else None

    st.markdown("---")

    # Hints + recommendations toggles (keys are critical to avoid duplicates)
    state["show_hints"] = st.toggle("Show hints", value=state.get("show_hints", True), key="toggle_hints")
    state["show_recommendations"] = st.toggle("Show recommended move", value=state.get("show_recommendations", True), key="toggle_recs")
    state["tutorial_on"] = st.toggle("Tutorial wizard", value=state.get("tutorial_on", True), key="toggle_tutorial")

    st.markdown("---")
    if st.button("🔄 Reset run (new randomized start)", use_container_width=True, key="btn_reset"):
        st.session_state.state = init_state()
        st.rerun()

# -----------------------------
# Tutorial Wizard (friendly, not condescending)
# -----------------------------
def tutorial_panel(state):
    if not state["tutorial_on"]:
        return

    with st.expander("🧭 Tutorial Wizard (optional)", expanded=(state["tutorial_step"] <= 2),):
        st.write("MirrorWorld is simple: you make leadership choices, the market reacts, and the Mirror AI adapts.")
        step = state["tutorial_step"]

        if step == 1:
            st.markdown("**Step 1 — Start the run**")
            st.write("Choose a seed amount and a first product line. Bigger seed = faster momentum but more scrutiny.")
            if st.button("Next", key="tut_next_1"):
                state["tutorial_step"] = 2
                st.session_state.state = state
                st.rerun()

        elif step == 2:
            st.markdown("**Step 2 — Make quarterly decisions**")
            st.write("Pick your growth speed, governance allocation, counterfactual testing (YES/NO), and expansion.")
            st.write("Think of it as: **Speed vs Resilience**.")
            if st.button("Next", key="tut_next_2"):
                state["tutorial_step"] = 3
                st.session_state.state = state
                st.rerun()

        elif step == 3:
            st.markdown("**Step 3 — Handle decision trees**")
            st.write("Sometimes the simulation pauses for a mini story. Your choice has consequences—just like real leadership.")
            st.write("In Advanced mode you can keep playing until you hit $1B (or stop whenever).")
            if st.button("Done", key="tut_done"):
                state["tutorial_step"] = 99
                st.session_state.state = state
                st.rerun()

tutorial_panel(state)

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([1.35, 0.90], gap="large")

# -----------------------------
# RIGHT: Metrics panel
# -----------------------------
with right:
    st.subheader("Real-Time Metrics")

    # Short labels help mobile
    c1, c2, c3 = st.columns(3)
    c1.metric("Val", fmt_m(state["valuation_m"]))
    c2.metric("Trust", f"{state['trust']:.0f}/100")
    c3.metric("Gov", f"{state['governance']:.0f}/100")

    c4, c5 = st.columns(2)
    c4.metric("Crisis", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")
    c5.metric("Reg", f"{pressure_label(state['reg_pressure'])}")

    st.markdown("---")
    st.metric("Mirror AI", f"{state['comp_strength']:.0f}/100")
    st.write(f"**Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden risk:** {state['hidden_risk']:.0f}/100")
    st.write(f"**Incidents:** {state['violations']}")
    st.write(f"**Score:** {score(state):.1f}/100")

    if state["show_recommendations"] and state["phase"] != "setup" and not state["game_over"]:
        st.markdown("---")
        st.markdown("**Recommended move (optional):**")
        for rec in recommend_move(state):
            st.write("• " + rec)

    st.markdown("---")
    if state["game_over"]:
        st.error(f"Game Over — {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
        if win_condition(state):
            st.success("✅ Win: Unicorn + Trust ≥ 70")
        else:
            st.info("You can reset to try a new run with different starting conditions.")
    else:
        if state["mode"] == "Standard":
            st.info("Goal: reach **$1B** by Quarter 8 while keeping trust high and avoiding shutdown.")
        else:
            st.info("Goal: reach **$1B** at your pace. You can keep playing as long as you want.")

# -----------------------------
# LEFT: Game play area
# -----------------------------
with left:
    # Header for current run
    if state["mode"] == "Standard":
        st.subheader(f"Quarter {state['quarter']} / 8")
    else:
        st.subheader(f"Quarter {state['quarter']} (Endless Mode)")

    # Setup phase
    if state["phase"] == "setup":
        st.markdown("### Setup: Your First Strategic Commitment")

        explain("Seed funding gives momentum but increases scrutiny. Pick your first product line—the game will tailor decision trees to it.")

        seed = st.select_slider(
            "Seed funding ($M)",
            options=[5, 10, 20, 35, 50],
            value=20,
            key="seed_slider"
        )

        product = st.radio(
            "First product line",
            ["Credit", "Fraud", "Advisory"],
            horizontal=True,
            key="product_radio"
        )

        if state["show_hints"]:
            st.caption("Hint: Credit grows steadily but faces more regulation. Fraud scales fast but can trigger false-positive backlash. Advisory is powerful but can amplify trust risk.")

        start_btn = st.button("✅ Start Run", use_container_width=True, key="btn_start")
        if start_btn:
            rng = get_rng(state)

            state["seed_m"] = float(seed)
            state["product_line"] = product

            # Starts at 0, then seed round sets valuation (still “starts from zero”)
            state["valuation_m"] = float(seed) * float(rng.uniform(4.8, 6.8))

            # Seed increases scrutiny slightly
            state["reg_pressure"] = clamp(state["reg_pressure"] + float(seed) / 6.0, 0, 100)

            # Flavor headline
            nm = state["player_name"].strip() or "You"
            state["headlines"] = [f"🎬 {nm} closes a ${seed}M seed round and launches {product}. Mirror AI starts observing."]
            state["phase"] = "play"

            save_rng(state, rng)
            st.session_state.state = state
            st.rerun()

    else:
        # If a decision tree is pending, resolve it first
        if state["pending_tree"] and not state["game_over"]:
            tkey = state["pending_tree"]["tree_key"]
            node_id = state["pending_tree"]["node_id"]
            node = TREES[tkey][node_id]
            nm = state["player_name"].strip() or "You"

            st.warning(f"📚 Decision Tree — {node['title']}")
            st.write(f"**Story:** {node['story']}")

            st.markdown("**Choose your move:**")
            for i, (label, effects, next_id) in enumerate(node["choices"], start=1):
                if st.button(f"Option {i}: {label}", use_container_width=True, key=f"tree_{tkey}_{node_id}_{i}"):
                    apply_effects(state, effects)
                    bayesian_crisis_update(state)

                    # Store memory for flavor (optional)
                    state["tree_memory"][f"{tkey}:{node_id}"] = label

                    # Next node or end tree
                    if next_id is None:
                        state["pending_tree"] = None
                        state["headlines"] = [f"📚 {nm} chose: {label}"] + state["headlines"]
                    else:
                        state["pending_tree"] = {"tree_key": tkey, "node_id": next_id}
                        state["headlines"] = [f"📚 {nm} chose: {label}"] + state["headlines"]

                    end_check(state)
                    st.session_state.state = state
                    st.rerun()

        # If a mini-event is pending, resolve it
        elif state["pending_event"] and not state["game_over"]:
            ev = state["pending_event"]
            nm = state["player_name"].strip() or "You"

            st.warning(f"🧩 Mini Event — {ev['title']}")
            st.write(ev["setup"])
            st.markdown("**Choose your response:**")

            for i, (label, effects) in enumerate(ev["choices"], start=1):
                if st.button(f"Option {i}: {label}", use_container_width=True, key=f"ev_{ev['title']}_{i}"):
                    apply_effects(state, effects)
                    bayesian_crisis_update(state)
                    state["pending_event"] = None
                    state["headlines"] = [f"🧩 {nm} chose: {label}"] + state["headlines"]
                    end_check(state)
                    st.session_state.state = state
                    st.rerun()

        else:
            # Main decision controls
            st.markdown("### Your Leadership Decisions (This Quarter)")

            # Growth + governance
            growth = st.slider("Growth aggressiveness", 0, 100, 65, key="sl_growth",
                               help="Higher = faster valuation growth, but more risk and scrutiny.")
            gov_spend = st.slider("Governance allocation", 0, 100, 55, key="sl_gov",
                                  help="Higher = stronger controls, monitoring, audits, and incident readiness.")

            # Counterfactual testing YES/NO (as requested)
            counterfactual_yes = st.toggle(
                "Counterfactual testing (YES/NO)",
                value=True,
                key="toggle_counterfactual",
                help="YES reduces hidden risk and increases trust, but costs some speed this quarter."
            )

            # Expansion scope
            expansion = st.radio(
                "Expansion scope",
                ["Narrow", "Balanced", "Wide"],
                index=1,
                horizontal=True,
                key="radio_expansion",
                help="Wide expands faster but amplifies operational and regulatory complexity."
            )

            st.markdown("### AI & Strategy Levers")
            explain("These levers describe how you deploy generative AI in a FinTech environment—each has tradeoffs.")

            colA, colB = st.columns(2)

            with colA:
                product_focus = st.selectbox(
                    "Product focus",
                    ["Credit", "Fraud", "Advisory"],
                    index=["Credit", "Fraud", "Advisory"].index(state["product_line"]),
                    key="sel_product_focus",
                    help="Where your AI is applied most this quarter (and where scrutiny concentrates)."
                )
                st.caption("• Credit: speed vs fairness\n• Fraud: fraud-loss vs false positives\n• Advisory: helpfulness vs hallucinations")

                model_strategy = st.selectbox(
                    "Model strategy",
                    ["Open", "Hybrid", "Closed"],
                    index=1,
                    key="sel_model_strategy",
                    help="Open is faster/cheaper but can be harder to control; Closed is more controlled but slower."
                )
                st.caption("Open = velocity • Hybrid = pragmatic • Closed = controlled")

            with colB:
                data_policy = st.selectbox(
                    "Data policy",
                    ["Minimal", "Balanced", "Aggressive"],
                    index=1,
                    key="sel_data_policy",
                    help="How aggressively you use data signals. More data can mean better performance—but higher privacy and compliance risk."
                )
                st.caption("Minimal = trust-first • Aggressive = growth-first")

                pr_posture = st.selectbox(
                    "PR posture",
                    ["Transparent", "Quiet", "Defensive"],
                    index=1,
                    key="sel_pr",
                    help="How you communicate with the public and regulators. Transparency usually stabilizes trust over time."
                )
                st.caption("Transparent = trust engine • Defensive = reputation risk")

            # Optional hint block
            if state["show_hints"]:
                st.info(
                    "Play style tip: If you push growth hard, counterfactual testing YES + more governance helps you avoid compounding risk. "
                    "If Mirror AI gets strong, differentiation via transparency and controls often wins over pure speed."
                )

            # Run quarter
            st.markdown("---")
            run_col, stop_col = st.columns(2)

            with run_col:
                if st.button("▶️ Run Quarter", use_container_width=True, key="btn_run", disabled=state["game_over"]):
                    nm = state["player_name"].strip() or "You"

                    last = {
                        "growth": growth,
                        "gov_spend": gov_spend,
                        "counterfactual_yes": counterfactual_yes,
                        "expansion": expansion,
                        "product_focus": product_focus,
                        "model_strategy": model_strategy,
                        "data_policy": data_policy,
                        "pr_posture": pr_posture,
                    }

                    # Apply your decisions
                    apply_decisions(
                        state,
                        growth=growth,
                        gov_spend=gov_spend,
                        counterfactual_yes=counterfactual_yes,
                        expansion=expansion,
                        product_focus=product_focus,
                        model_strategy=model_strategy,
                        data_policy=data_policy,
                        pr_posture=pr_posture
                    )

                    # Competitor reacts
                    comp_headlines = update_competitor(state, last)

                    # Update crisis probability
                    bayesian_crisis_update(state)

                    # Sometimes trigger decision tree
                    if not state["game_over"]:
                        maybe = maybe_trigger_tree(state)
                        if maybe:
                            state["pending_tree"] = maybe

                    # Sometimes trigger mini-event (if no tree triggered)
                    if (not state["game_over"]) and (state["pending_tree"] is None):
                        ev = maybe_trigger_mini_event(state)
                        if ev:
                            # Normalize to expected format
                            state["pending_event"] = {
                                "title": ev["title"],
                                "setup": ev["setup"],
                                "choices": ev["choices"],
                            }

                    # Check end conditions
                    end_check(state)

                    # Log history
                    state["history"].append({
                        "Quarter": state["quarter"],
                        "Growth": growth,
                        "Gov": gov_spend,
                        "Counterfactual": "YES" if counterfactual_yes else "NO",
                        "Expansion": expansion,
                        "Product": product_focus,
                        "Model": model_strategy,
                        "Data": data_policy,
                        "PR": pr_posture,
                        "CompStrat": state["comp_strategy"],
                        "CompStr": round(state["comp_strength"], 1),
                        "Val($M)": round(state["valuation_m"], 1),
                        "Trust": round(state["trust"], 1),
                        "GovScore": round(state["governance"], 1),
                        "Reg": round(state["reg_pressure"], 1),
                        "Crisis%": round(state["crisis_prob"], 1),
                        "Hidden": round(state["hidden_risk"], 1),
                        "Incidents": state["violations"],
                    })

                    # Headlines
                    base = [f"📈 {nm} executes Quarter {state['quarter']}. The market recalibrates."] + comp_headlines
                    if state["pending_tree"]:
                        base = ["📚 A decision tree has triggered—resolve it to continue."] + base
                    if state["pending_event"]:
                        base = ["🧩 A mini-event has triggered—make your move to continue."] + base
                    state["headlines"] = base + state["headlines"][:6]

                    # Advance quarter
                    if not state["game_over"]:
                        state["quarter"] += 1

                    st.session_state.state = state
                    st.rerun()

            with stop_col:
                if state["mode"] == "Advanced":
                    # “Stop run” is optional in endless mode
                    if st.button("⏸️ Stop Run (end here)", use_container_width=True, key="btn_stop"):
                        state["game_over"] = True
                        state["end_reason"] = "Run ended by player (Advanced mode)."
                        st.session_state.state = state
                        st.rerun()

            # Headlines area
            st.markdown("### Headlines")
            for h in state["headlines"]:
                st.write("• " + h)

            # Win notification (Advanced can win anytime)
            if (not state["game_over"]) and state["valuation_m"] >= 1000 and state["trust"] >= 70:
                st.success("🎉 You hit Unicorn + Trust ≥ 70. You can keep playing, or stop the run in the sidebar/Stop button.")

            # Log table
            st.markdown("### Run Log")
            if state["history"]:
                st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
            else:
                st.info("Run a quarter to generate the log.")

# Persist state
st.session_state.state = state
```0

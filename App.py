# App.py
# MirrorWorld — AI FinTech Leadership Simulation (Premium Streamlit Prototype)
# Two modes:
#   - Standard (Endless): play as long as you want until you reach $1B (or crash)
#   - Advanced (8 quarters): tighter, harder, “capstone” run
#
# Features:
#   - Front-page start screen (name, mode, seed, product, tutorial)
#   - Counterfactuals as YES/NO (simple lever)
#   - Choose-your-own-adventure decision-tree events (clear + visible)
#   - Adaptive Mirror AI competitor “agent” that reacts to your patterns
#   - Premium HUD: readable metrics + progress bars + compact labels (mobile-friendly)
#   - Strategy Coach (optional): recommended moves without spoiling
#   - Randomized starting conditions so no two runs feel identical
#
# NOTE: This is a single-file Streamlit app. Deploy to Streamlit Cloud as App.py.

import time
import math
import streamlit as st
import numpy as np
import pandas as pd

# ----------------------------
# Page config + premium styling
# ----------------------------
st.set_page_config(page_title="MirrorWorld", layout="wide")

st.markdown(
    """
    <style>
      /* Make metrics readable on mobile / narrow screens */
      [data-testid="stMetricValue"] { font-size: 1.55rem; }
      [data-testid="stMetricLabel"] { font-size: 0.9rem; }
      .mw-hero { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; }
      .mw-sub { font-size: 1.05rem; opacity: 0.9; }
      .mw-card { padding: 1rem 1.1rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.04); }
      .mw-chip { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; background: rgba(255,255,255,0.08); margin-right: 0.4rem; font-size: 0.85rem;}
      .mw-muted { opacity: 0.8; }
      .mw-divider { height: 1px; background: rgba(255,255,255,0.10); margin: 0.8rem 0; }
      .mw-small { font-size: 0.92rem; opacity: 0.92; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Helpers
# ----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def fmt_m(x):
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

def trend_arrow(delta):
    if delta > 1.5: return "▲"
    if delta < -1.5: return "▼"
    return "→"

def as_pct(x):
    return f"{x:.0f}%"

# ----------------------------
# State + RNG
# ----------------------------
def init_state():
    seed = int(time.time() * 1000) % 2_000_000_000
    rng = np.random.default_rng(seed)

    return {
        # experience
        "phase": "setup",
        "player_name": "",
        "mode": "Standard",        # Standard or Advanced
        "max_quarters": None,      # None = endless; int = 8
        "tutorial_on": True,
        "tutorial_step": 1,

        # time
        "quarter": 1,
        "game_over": False,
        "end_reason": "",
        "won": False,

        # core metrics (randomized on start)
        "valuation_m": 0.0,
        "trust": 55.0,
        "governance": 50.0,
        "reg_pressure": 20.0,
        "crisis_prob": 8.0,
        "hidden_risk": 10.0,
        "violations": 0,

        # user selections
        "seed_m": 0.0,
        "product_line": None,

        # competitor agent
        "comp_strength": 10.0,
        "comp_strategy": "Observing",
        "comp_memory": {"you_skip_checks": 0, "you_go_fast": 0, "you_go_transparent": 0},

        # decision events
        "pending_event": None,
        "pending_event_meta": None,  # store context for nicer copy

        # narrative
        "briefing": "",
        "debrief": "",
        "headlines": ["Welcome to MirrorWorld."],

        # history
        "history": [],

        # rng
        "rng_state": rng.bit_generator.state,
    }

def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# ----------------------------
# Core Sim Mechanics
# ----------------------------
def bayesian_crisis_update(state):
    prior = state["crisis_prob"] / 100.0
    signal = (
        0.52 * (state["hidden_risk"] / 100.0) +
        0.20 * (state["reg_pressure"] / 100.0) +
        0.18 * (max(0.0, 65.0 - state["trust"]) / 65.0) +
        0.10 * (max(0.0, 55.0 - state["governance"]) / 55.0)
    )
    signal = clamp(signal, 0.0, 1.0)
    posterior = 0.62 * prior + 0.38 * signal
    state["crisis_prob"] = clamp(posterior * 100.0, 1.0, 95.0)

def value_creation(state, growth, expansion, product_focus, model_strategy):
    # baseline creates "fun" movement without being too mathy
    base = 14.0 + (growth / 100) * 62.0  # ~14..76

    # expansion multiplier
    if expansion == "Wide":
        base *= 1.18
    elif expansion == "Balanced":
        base *= 1.06
    else:
        base *= 0.92

    # product multipliers
    if product_focus == "Fraud":
        base *= 1.12
    elif product_focus == "Credit":
        base *= 1.04
    else:  # Advisory
        base *= 1.02

    # model strategy multiplier (simple)
    if model_strategy == "Open":
        base *= 1.07
    elif model_strategy == "Hybrid":
        base *= 1.03
    else:
        base *= 0.98

    return base

def apply_decisions(state, growth, gov_budget, counterfactual_yes, expansion,
                    product_focus, model_strategy, data_policy, pr_posture):
    rng = get_rng(state)

    # Governance moves slower, but matters a lot
    state["governance"] = clamp(
        state["governance"] + (gov_budget / 100) * 10.5 - (growth / 100) * 3.2,
        0, 100
    )

    # Counterfactual YES/NO lever (simple, but powerful)
    if counterfactual_yes:
        # cost: slightly less growth, benefits: lower hidden risk + more trust
        state["hidden_risk"] = clamp(state["hidden_risk"] - 7.5, 0, 100)
        state["trust"] = clamp(state["trust"] + 2.2, 0, 100)
        test_cost = 0.08
    else:
        # speed now, risk later
        state["hidden_risk"] = clamp(state["hidden_risk"] + 6.0, 0, 100)
        state["trust"] = clamp(state["trust"] - 1.8, 0, 100)
        test_cost = 0.00

    # Data policy: Minimal / Balanced / Aggressive
    if data_policy == "Minimal":
        state["trust"] = clamp(state["trust"] + 1.2, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] - 1.5, 0, 100)
        data_boost = 0.96
        risk_boost = 0.86
    elif data_policy == "Balanced":
        data_boost = 1.00
        risk_boost = 1.00
    else:
        state["trust"] = clamp(state["trust"] - 2.1, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] + 4.2, 0, 100)
        data_boost = 1.08
        risk_boost = 1.22

    # PR posture
    if pr_posture == "Transparent":
        state["trust"] = clamp(state["trust"] + 1.1, 0, 100)
        pr_risk = 0.92
    elif pr_posture == "Defensive":
        state["trust"] = clamp(state["trust"] - 0.9, 0, 100)
        pr_risk = 1.06
    else:
        pr_risk = 1.00

    # Product risk profile
    if product_focus == "Credit":
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.6, 0, 100)
        product_risk = 1.10
    elif product_focus == "Fraud":
        product_risk = 1.00
    else:
        state["trust"] = clamp(state["trust"] - 0.7, 0, 100)
        product_risk = 1.05

    # Trust + governance affect your ability to scale safely
    trust_factor = 0.86 + (state["trust"] / 100) * 0.30
    gov_factor = 0.86 + (state["governance"] / 100) * 0.25

    created = value_creation(state, growth, expansion, product_focus, model_strategy)
    created *= trust_factor * gov_factor * data_boost
    created *= (1.0 - test_cost)
    created += rng.normal(0, 3.3)

    # Update valuation
    state["valuation_m"] = max(0.0, state["valuation_m"] + created)

    # Hidden risk accumulation (compounds when going fast without guardrails)
    risk_add = (growth / 100) * 6.2
    risk_add += max(0.0, (70.0 - state["governance"])) / 100.0 * 4.1
    risk_add *= risk_boost * product_risk * pr_risk
    if counterfactual_yes:
        risk_add *= 0.88  # checks reduce the compounding effect
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add - (gov_budget / 100) * 3.2, 0, 100)

    # Regulatory pressure rises when growth outpaces governance
    state["reg_pressure"] = clamp(
        state["reg_pressure"] + max(0.0, (growth - state["governance"])) / 100.0 * 9.2,
        0, 100
    )

    save_rng(state, rng)

# ----------------------------
# Mirror AI Competitor Agent
# ----------------------------
def update_competitor_agent(state, decision):
    """
    Adaptive competitor: reacts to your patterns.
    Keeps it intuitive:
      - If you skip counterfactuals / go defensive / aggressive data -> competitor attacks via regulators
      - If you're disciplined -> competitor tries price war or copycat
    """
    rng = get_rng(state)
    mem = state["comp_memory"]

    growth = decision["growth"]
    cf_yes = decision["counterfactual_yes"]
    pr = decision["pr_posture"]
    data_policy = decision["data_policy"]
    gov_budget = decision["gov_budget"]

    # Update memory signals
    if not cf_yes:
        mem["you_skip_checks"] += 1
    if growth >= 70:
        mem["you_go_fast"] += 1
    if pr == "Transparent":
        mem["you_go_transparent"] += 1

    # Determine competitor posture
    risky_profile = (mem["you_skip_checks"] >= 2) or (data_policy == "Aggressive") or (pr == "Defensive")
    disciplined_profile = (gov_budget >= 60) and cf_yes and (pr == "Transparent")

    if risky_profile and state["reg_pressure"] >= 35:
        state["comp_strategy"] = "Regulatory Trap"
    elif disciplined_profile and state["trust"] >= 60:
        state["comp_strategy"] = "Price War"
    elif disciplined_profile:
        state["comp_strategy"] = "Safety-First"
    else:
        state["comp_strategy"] = "Copycat"

    # Strength growth: more you grow, more it learns from your public footprint
    visibility = min(1.0, state["valuation_m"] / 1000.0)  # 0..1
    learn_rate = 2.2 + 6.2 * visibility

    opening = 0.0
    opening += 3.2 if not cf_yes else 0.6
    opening += 2.2 if pr == "Defensive" else 0.8
    opening += 1.8 if data_policy == "Aggressive" else 0.7

    comp_gain = learn_rate + opening + rng.normal(0, 1.0)
    state["comp_strength"] = clamp(state["comp_strength"] + comp_gain, 0, 100)

    headlines = []
    s = state["comp_strength"]

    if state["comp_strategy"] == "Price War":
        hit = (0.025 + 0.00055 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        headlines.append("⚔️ Mirror AI opens a price war: margins compress and churn pressure rises.")

    elif state["comp_strategy"] == "Safety-First":
        trust_hit = 0.9 + (max(0.0, 62 - state["governance"]) / 40.0) * 2.2
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI markets 'safer by design': your trust gets publicly benchmarked.")

    elif state["comp_strategy"] == "Copycat":
        steal = (0.02 + 0.00035 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI clones your feature set: differentiation shrinks.")

    else:  # Regulatory Trap
        add = 3.8 + 0.08 * s
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        headlines.append("🧾 Mirror AI triggers a regulatory narrative: complaints and scrutiny rise.")
        # occasional incident when you're already risky
        if state["hidden_risk"] >= 55 and rng.random() < 0.30:
            state["violations"] += 1
            state["trust"] = clamp(state["trust"] - 3.5, 0, 100)
            headlines.append("📣 A complaint escalates into an incident review (+1 violation).")

    save_rng(state, rng)
    return headlines

# ----------------------------
# Choose-your-own-adventure Decision Trees
# ----------------------------
def make_event_templates():
    """
    Three most relevant modern market decision trees, plus a few extras.
    They are written as story-first, but apply real governance consequences.
    """
    return [
        # 1) Credit underwriting fairness / bias scandal
        {
            "id": "credit_fairness_storm",
            "title": "Credit Fairness Storm",
            "setup": "A journalist finds a pattern: one protected group is getting systematically worse terms. The story drops at 7AM.",
            "trigger_hint": "More likely when you scale Credit fast without counterfactual checks.",
            "choices": [
                (
                    "Pause affected segment, publish a model card + remediation timeline",
                    {"trust": +3.0, "governance": +4.0, "reg_pressure": -2.0, "valuation_m": -14.0, "hidden_risk": -8.0}
                ),
                (
                    "Quiet patch + internal note (no public disclosure)",
                    {"trust": -2.2, "governance": +1.0, "reg_pressure": +3.0, "valuation_m": -6.0, "hidden_risk": +3.0}
                ),
                (
                    "Deny and blame data quality (defensive posture)",
                    {"trust": -5.0, "governance": -1.0, "reg_pressure": +6.0, "valuation_m": -10.0, "violations": +1, "hidden_risk": +4.0}
                ),
            ],
        },

        # 2) Fraud: false positives + customer harm
        {
            "id": "fraud_false_positive_wave",
            "title": "Fraud False-Positive Wave",
            "setup": "Your fraud model starts blocking legit users during a traffic spike. Social media calls it 'financial lockout.'",
            "trigger_hint": "More likely when you go Wide + aggressive automation in Fraud.",
            "choices": [
                (
                    "Introduce human-in-the-loop for edge cases and lower the threshold temporarily",
                    {"trust": +2.5, "governance": +2.5, "valuation_m": -9.0, "hidden_risk": -6.0}
                ),
                (
                    "Keep the model strict (loss prevention first) and offer refunds later",
                    {"trust": -3.2, "valuation_m": +7.0, "reg_pressure": +2.0, "hidden_risk": +4.0}
                ),
                (
                    "Roll back to the previous model version immediately",
                    {"trust": +1.2, "valuation_m": -6.0, "hidden_risk": -4.0}
                ),
            ],
        },

        # 3) GenAI advisory: hallucination / suitability issue
        {
            "id": "advisory_suitability_shock",
            "title": "Advisory Suitability Shock",
            "setup": "A user follows your AI’s advice and posts proof it invented a rule and recommended an unsuitable product.",
            "trigger_hint": "More likely when Advisory is scaled fast with weak safeguards.",
            "choices": [
                (
                    "Add confidence scoring + citations + refuse-to-answer policy for uncertain outputs",
                    {"trust": +3.0, "governance": +3.0, "valuation_m": -10.0, "hidden_risk": -8.0, "reg_pressure": -1.0}
                ),
                (
                    "Add a disclaimer and continue shipping",
                    {"trust": -1.8, "valuation_m": +4.0, "hidden_risk": +4.0}
                ),
                (
                    "Temporarily disable advisory and offer a waitlist for the safer version",
                    {"trust": +1.8, "valuation_m": -12.0, "hidden_risk": -6.0}
                ),
            ],
        },

        # Regulator inquiry (common across all)
        {
            "id": "regulator_explainability_call",
            "title": "Regulator: 'Explain It.'",
            "setup": "A regulator requests decision traceability. They want logs, not marketing.",
            "trigger_hint": "More likely when your Reg Pressure is already high.",
            "choices": [
                (
                    "Provide decision logs + model card + monitoring plan",
                    {"governance": +4.0, "trust": +1.0, "reg_pressure": -5.0, "valuation_m": -7.0}
                ),
                (
                    "High-level explanation only (no internals)",
                    {"governance": +1.0, "trust": -0.8, "reg_pressure": +2.5}
                ),
                (
                    "Delay response and lawyer up",
                    {"reg_pressure": +6.0, "trust": -2.2, "violations": +1, "valuation_m": -5.0}
                ),
            ],
        },

        # Competitor attack (ties to Mirror AI)
        {
            "id": "mirror_ai_undercut",
            "title": "Mirror AI Undercuts You",
            "setup": "Mirror AI launches a copycat feature—cheaper, positioned as 'safer,' and with polished PR.",
            "trigger_hint": "More likely when competitor strength is high.",
            "choices": [
                (
                    "Differentiate with transparency: benchmarks + safeguards page",
                    {"trust": +2.0, "governance": +2.0, "valuation_m": -7.0, "comp_strength": -3.0}
                ),
                (
                    "Slash prices immediately",
                    {"valuation_m": +8.0, "trust": -1.0, "hidden_risk": +3.0}
                ),
                (
                    "Escalate a narrative war (complaints + counter-campaign)",
                    {"reg_pressure": +3.0, "trust": -2.0, "comp_strength": -4.0}
                ),
            ],
        },
    ]

def event_probability(state, decision):
    # Base probability: we want frequent enough to feel like a story
    p = 0.28
    if state["hidden_risk"] >= 45:
        p += 0.14
    if state["reg_pressure"] >= 55:
        p += 0.10
    if state["comp_strength"] >= 45:
        p += 0.10
    # scaling fast w/out counterfactual checks increases drama
    if decision["growth"] >= 70 and not decision["counterfactual_yes"]:
        p += 0.12
    return clamp(p, 0.18, 0.72)

def choose_event(state, decision):
    rng = get_rng(state)
    templates = make_event_templates()

    # weighted selection based on context
    weights = []
    for t in templates:
        w = 1.0
        if t["id"].startswith("credit") and decision["product_focus"] == "Credit":
            w += 0.9
        if t["id"].startswith("fraud") and decision["product_focus"] == "Fraud":
            w += 0.9
        if t["id"].startswith("advisory") and decision["product_focus"] == "Advisory":
            w += 0.9
        if t["id"].startswith("regulator") and state["reg_pressure"] >= 50:
            w += 0.7
        if t["id"].startswith("mirror") and state["comp_strength"] >= 40:
            w += 0.7
        if (not decision["counterfactual_yes"]) and ("Suitability" in t["title"] or "Fairness" in t["title"]):
            w += 0.4
        weights.append(w)

    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    idx = int(rng.choice(len(templates), p=weights))
    save_rng(state, rng)
    return templates[idx]

def apply_event_effects(state, effects):
    for k, v in effects.items():
        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + float(v))
        elif k == "violations":
            state["violations"] += int(v)
        elif k == "comp_strength":
            state["comp_strength"] = clamp(state["comp_strength"] + float(v), 0, 100)
        else:
            state[k] = clamp(state.get(k, 0.0) + float(v), 0.0, 100)

# ----------------------------
# Win/Lose + Score
# ----------------------------
def end_check(state):
    if state["violations"] >= 3:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents/violations."
    elif state["trust"] < 25 and state["reg_pressure"] > 75:
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under high regulatory pressure."
    elif state["crisis_prob"] > 75:
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."

def win_check(state):
    # win: reach $1B with trust >= 70 and no shutdown
    if state["valuation_m"] >= 1000.0 and state["trust"] >= 70.0 and state["violations"] < 3:
        state["won"] = True

def score(state):
    valuation_score = min(100.0, (state["valuation_m"] / 1000.0) * 100.0)
    penalty = state["reg_pressure"] * 0.24 + state["crisis_prob"] * 0.58 + state["violations"] * 10.0
    total = valuation_score * 0.52 + state["trust"] * 0.20 + state["governance"] * 0.20 - penalty * 0.10
    return clamp(total, 0.0, 100.0)

# ----------------------------
# Narrative
# ----------------------------
def quarter_briefing(state):
    nm = state["player_name"] or "You"
    lines = []

    # Mood
    if state["trust"] >= 70:
        mood = "The market believes you can scale responsibly."
    elif state["trust"] >= 50:
        mood = "Confidence is cautious—one bad story could swing sentiment."
    else:
        mood = "Trust is fragile. People are looking for reasons to doubt you."

    # Scrutiny
    if state["reg_pressure"] >= 70:
        scrutiny = "Regulators are circling. Every decision needs receipts."
    elif state["reg_pressure"] >= 45:
        scrutiny = "Scrutiny is rising—expect questions about governance and transparency."
    else:
        scrutiny = "Regulatory pressure is manageable—for now."

    # Competitor
    if state["comp_strength"] >= 70:
        comp = "Mirror AI is extremely capable now—assume it anticipates your next move."
    elif state["comp_strength"] >= 45:
        comp = "Mirror AI is learning fast. It will punish predictable patterns."
    else:
        comp = "Mirror AI is watching and collecting data on your behavior."

    lines.append(f"**Quarter {state['quarter']} Briefing for {nm}:** {mood}")
    lines.append(f"{scrutiny} {comp}")
    return " ".join(lines)

def quarter_debrief(state, deltas, comp_headlines, event_note=None):
    parts = []
    parts.append("**Quarter Debrief:**")

    # show “what changed” without reading the slide
    parts.append(
        f"Valuation {trend_arrow(deltas['valuation'])} {fmt_m(state['valuation_m'])}, "
        f"Trust {trend_arrow(deltas['trust'])} {state['trust']:.0f}, "
        f"Governance {trend_arrow(deltas['gov'])} {state['governance']:.0f}."
    )

    if event_note:
        parts.append(event_note)

    if comp_headlines:
        parts.append(" ".join(comp_headlines))

    # add a subtle coaching line
    if state["reg_pressure"] >= 65 and state["trust"] < 55:
        parts.append("Your next best move is to trade speed for credibility—one quarter of discipline can prevent a spiral.")
    elif state["hidden_risk"] >= 60:
        parts.append("Hidden risk is compounding. Counterfactual checks and governance spend will reduce future shock probability.")
    return " ".join(parts)

# ----------------------------
# Strategy Coach (optional)
# ----------------------------
def recommend_move(state):
    recs = []
    # Minimal “winning heuristics” (feels premium, not hand-holdy)
    if state["hidden_risk"] >= 55:
        recs.append("Turn **Counterfactuals = YES** next quarter to reduce compounding risk.")
    if state["reg_pressure"] >= 60:
        recs.append("Avoid **Wide** expansion while pressure is high; choose **Balanced** or **Narrow**.")
    if state["trust"] < 50:
        recs.append("Use **PR = Transparent** to stabilize trust and reduce narrative volatility.")
    if state["governance"] < 50 and state["valuation_m"] > 250:
        recs.append("Increase **Governance Budget**—big companies get audited harder.")
    if not recs:
        recs.append("You’re in a stable zone. You can push growth—just keep one eye on hidden risk.")
    return recs

# ----------------------------
# Tutorial Wizard
# ----------------------------
def tutorial_panel(state):
    if not state.get("tutorial_on", False):
        return

    step = state.get("tutorial_step", 1)
    nm = (state.get("player_name") or "You").strip() or "You"

    st.markdown("### 🧭 Guided Walkthrough")

    if step == 1:
        st.write(f"Welcome, **{nm}**. You’re the CEO. Your job is to scale *and* stay credible.")
        st.write("Think of this as a leadership simulator: **speed earns valuation**, **discipline earns survivability**.")
        if st.button("Next → (Your levers)", key="tut_next_1", use_container_width=True):
            state["tutorial_step"] = 2
            st.session_state.state = state
            st.rerun()

    elif step == 2:
        st.write("Your main levers:")
        st.write("• **Growth Target**: faster valuation, more risk.")
        st.write("• **Governance Budget**: slower now, prevents blowups later.")
        st.write("• **Counterfactuals (YES/NO)**: YES reduces hidden risk and stabilizes trust.")
        if st.button("Next → (How you win)", key="tut_next_2", use_container_width=True):
            state["tutorial_step"] = 3
            st.session_state.state = state
            st.rerun()

    elif step == 3:
        st.write("Winning pattern (simple):")
        st.write("1) Keep **Counterfactuals = YES** often (especially when scaling).")
        st.write("2) If **Reg Pressure** rises, slow expansion for one quarter.")
        st.write("3) If **Trust** dips, go **Transparent** to reduce narrative shocks.")
        if st.button("Next → (Make your first move)", key="tut_next_3", use_container_width=True):
            state["tutorial_step"] = 4
            st.session_state.state = state
            st.rerun()

    else:
        st.write("You’re ready. Make decisions, then **Commit Decisions** to run the quarter.")
        if st.button("Hide walkthrough", key="tut_hide", use_container_width=True):
            state["tutorial_on"] = False
            st.session_state.state = state
            st.rerun()

# ----------------------------
# Start Screen
# ----------------------------
def start_screen(state):
    st.markdown('<div class="mw-hero">🪞 MirrorWorld — AI FinTech Leadership Simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="mw-sub mw-muted">A rubric-aligned simulation with decision trees, an adaptive AI competitor, and real governance tradeoffs.</div>', unsafe_allow_html=True)
    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    st.markdown("### What you do (fast)")
    st.markdown(
        """
        - Choose how aggressively to scale an AI FinTech
        - Decide whether to run **counterfactual checks** (YES/NO)
        - Handle **choose-your-own-adventure** market events
        - Outplay a learning competitor: **Mirror AI**
        """
    )

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown("### Your identity")
        name = st.text_input(
            "Name (used in the story)",
            value=state.get("player_name", ""),
            key="front_name"
        )

        st.markdown("### Mode")
        mode_choice = st.radio(
            "Pick your run style",
            options=["Standard (Endless) — play until you hit $1B", "Advanced (8 quarters) — harder capstone run"],
            index=0,
            key="front_mode"
        )
        tutorial_on = st.checkbox("Guided walkthrough (recommended first run)", value=True, key="front_tutorial")

        st.markdown('<span class="mw-chip">Goal</span> Reach <b>$1B</b> without collapse.', unsafe_allow_html=True)
        st.markdown('<span class="mw-chip">Lose</span> 3 violations or systemic crisis.', unsafe_allow_html=True)

    with right:
        st.markdown("### Starting conditions")
        seed_m = st.select_slider(
            "Seed funding ($M) — higher seed = higher visibility/scrutiny",
            options=[5, 10, 20, 35, 50],
            value=20,
            key="front_seed"
        )
        product = st.radio(
            "Your first product line",
            ["Credit", "Fraud", "Advisory"],
            horizontal=True,
            key="front_product"
        )

        # friendly but not patronizing: quick meaning
        if product == "Credit":
            st.info("**Credit**: growth is steadier; fairness/explainability expectations are high.")
        elif product == "Fraud":
            st.info("**Fraud**: fast wins; risk is false positives and customer harm.")
        else:
            st.info("**Advisory**: big upside; risk is hallucinations and suitability scrutiny.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    if st.button("🚀 Start Simulation", use_container_width=True, key="front_start_btn"):
        rng = get_rng(state)

        state["player_name"] = name.strip()
        state["tutorial_on"] = bool(tutorial_on)
        state["tutorial_step"] = 1

        if mode_choice.startswith("Standard"):
            state["mode"] = "Standard"
            state["max_quarters"] = None
        else:
            state["mode"] = "Advanced"
            state["max_quarters"] = 8

        state["seed_m"] = float(seed_m)
        state["product_line"] = product

        # Randomize starting metrics (premium replayability)
        # Seed increases valuation and also increases scrutiny slightly
        state["valuation_m"] = float(seed_m) * float(rng.uniform(4.6, 7.1))

        # Trust/Gov start slightly different each run; advanced starts harsher
        if state["mode"] == "Advanced":
            state["trust"] = float(rng.uniform(46, 60))
            state["governance"] = float(rng.uniform(42, 58))
            state["reg_pressure"] = float(rng.uniform(18, 30) + seed_m / 8.0)
            state["crisis_prob"] = float(rng.uniform(8, 14))
            state["hidden_risk"] = float(rng.uniform(12, 20))
        else:
            state["trust"] = float(rng.uniform(52, 66))
            state["governance"] = float(rng.uniform(48, 62))
            state["reg_pressure"] = float(rng.uniform(14, 26) + seed_m / 10.0)
            state["crisis_prob"] = float(rng.uniform(6, 12))
            state["hidden_risk"] = float(rng.uniform(8, 16))

        state["violations"] = 0
        state["comp_strength"] = float(rng.uniform(8, 16))
        state["comp_strategy"] = "Observing"
        state["comp_memory"] = {"you_skip_checks": 0, "you_go_fast": 0, "you_go_transparent": 0}

        state["quarter"] = 1
        state["game_over"] = False
        state["won"] = False
        state["end_reason"] = ""
        state["pending_event"] = None
        state["pending_event_meta"] = None
        state["history"] = []

        nm = state["player_name"] or "You"
        state["headlines"] = [
            f"🎬 {nm} closes a ${seed_m}M seed round and launches {product}. Mirror AI starts observing."
        ]

        state["phase"] = "play"
        save_rng(state, rng)
        st.session_state.state = state
        st.rerun()

# ----------------------------
# UI: Main App
# ----------------------------
if "state" not in st.session_state:
    st.session_state.state = init_state()

state = st.session_state.state

# Setup screen
if state["phase"] == "setup":
    start_screen(state)
    st.stop()

# ----------------------------
# Layout
# ----------------------------
left, right = st.columns([1.25, 0.75], gap="large")

# ----------------------------
# Right: Premium HUD
# ----------------------------
with right:
    st.markdown("### Executive Dashboard")

    # compact metric labels (prevents truncation)
    c1, c2, c3 = st.columns(3)
    c1.metric("Val", fmt_m(state["valuation_m"]))
    c2.metric("Trust", f"{state['trust']:.0f}/100")
    c3.metric("Gov", f"{state['governance']:.0f}/100")

    d1, d2 = st.columns(2)
    d1.metric("Crisis", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")
    d2.metric("Reg", pressure_label(state["reg_pressure"]))

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # bars = readable everywhere
    st.progress(int(clamp(state["trust"], 0, 100)))
    st.caption(f"Trust: {state['trust']:.0f}/100")
    st.progress(int(clamp(state["governance"], 0, 100)))
    st.caption(f"Governance: {state['governance']:.0f}/100")
    st.progress(int(clamp(state["crisis_prob"], 0, 100)))
    st.caption(f"Crisis probability: {state['crisis_prob']:.0f}%")
    st.progress(int(clamp(state["reg_pressure"], 0, 100)))
    st.caption(f"Regulatory pressure: {pressure_label(state['reg_pressure'])}")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.metric("Mirror AI", f"{state['comp_strength']:.0f}/100")
    st.write(f"**Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden Risk:** {state['hidden_risk']:.0f}/100")
    st.write(f"**Violations:** {state['violations']} (shutdown at 3)")
    st.write(f"**Score:** {score(state):.1f}/100")

    # optional strategy coach
    with st.expander("🧠 Strategy Coach (optional)", expanded=False):
        for r in recommend_move(state):
            st.write("• " + r)
        st.caption("Coach gives direction without guaranteeing outcomes—Mirror AI adapts.")

    # end-of-game banner
    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
        st.success("✅ Win condition achieved" if state["won"] else "❌ Win condition not met")
    elif state["won"]:
        st.success("🏆 You reached $1B with strong trust. You can keep playing—or end the run.")

# ----------------------------
# Left: Gameplay + Story
# ----------------------------
with left:
    nm = state["player_name"] or "You"
    mode_line = "Standard (Endless)" if state["max_quarters"] is None else f"Advanced ({state['max_quarters']} quarters)"
    st.markdown(f"## Quarter {state['quarter']} — {mode_line}")

    # Tutorial wizard (opt-in)
    tutorial_panel(state)

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # If a decision event is pending, show it FIRST (this is your “decision tree” moment)
    if state["pending_event"] and not state["game_over"]:
        ev = state["pending_event"]
        st.warning(f"🧩 Story Decision: {ev['title']}")
        st.write(ev["setup"])
        st.caption(ev.get("trigger_hint", ""))

        st.markdown("**Choose your move:**")
        for i, (label, effects) in enumerate(ev["choices"], start=1):
            # show a tiny “consequence hint” without dumping numbers
            hint_bits = []
            if "trust" in effects and effects["trust"] != 0:
                hint_bits.append("Trust")
            if "governance" in effects and effects["governance"] != 0:
                hint_bits.append("Governance")
            if "reg_pressure" in effects and effects["reg_pressure"] != 0:
                hint_bits.append("Reg")
            if "valuation_m" in effects and effects["valuation_m"] != 0:
                hint_bits.append("Valuation")
            if "violations" in effects and effects["violations"] != 0:
                hint_bits.append("Violation risk")

            hint = f"Impacts: {', '.join(hint_bits)}" if hint_bits else ""

            if st.button(f"Option {i}: {label}", key=f"event_opt_{ev['id']}_{i}", use_container_width=True):
                # Apply event branch
                apply_event_effects(state, effects)
                bayesian_crisis_update(state)
                end_check(state)
                win_check(state)

                state["headlines"] = [f"🧩 {nm} chose: {label}"] + state["headlines"]
                state["pending_event"] = None
                state["pending_event_meta"] = None

                st.session_state.state = state
                st.rerun()

        st.info("After you choose, the simulation recalculates risk and the quarter continues.")
        st.stop()

    # Quarter briefing (story tone; not reading a slide)
    state["briefing"] = quarter_briefing(state)
    st.markdown(state["briefing"])

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Your Decisions (this quarter)")

    # --- Main levers (simple, readable) ---
    growth = st.slider(
        "Growth Target",
        0, 100, 65,
        key=f"growth_q{state['quarter']}"
    )
    st.caption("Higher growth increases valuation faster—but compounds hidden model risk and draws scrutiny.")

    gov_budget = st.slider(
        "Governance Budget",
        0, 100, 55,
        key=f"gov_q{state['quarter']}"
    )
    st.caption("This funds monitoring, controls, audit readiness, and safer deployment practices.")

    counterfactual_yes = st.toggle(
        "Counterfactual Checks (YES/NO)",
        value=True,
        key=f"cf_q{state['quarter']}"
    )
    st.caption("YES = slower now, safer later. NO = faster now, higher chance of shock events later.")

    expansion = st.radio(
        "Expansion Scope",
        ["Narrow", "Balanced", "Wide"],
        index=1,
        horizontal=True,
        key=f"exp_q{state['quarter']}"
    )
    st.caption("Wide boosts growth but increases market exposure and failure surface area.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### AI & Strategy Levers")

    # Keep the game easy: clear names + quick descriptions
    c1, c2 = st.columns(2)

    with c1:
        product_focus = st.selectbox(
            "Product Focus",
            ["Credit", "Fraud", "Advisory"],
            index=["Credit", "Fraud", "Advisory"].index(state["product_line"]),
            key=f"prod_q{state['quarter']}"
        )
        st.caption("Your focus determines what kind of problems you’ll face under stress.")

        model_strategy = st.selectbox(
            "Model Strategy",
            ["Open", "Hybrid", "Closed"],
            index=1,
            key=f"model_q{state['quarter']}"
        )
        st.caption("Open = fast/cheap. Closed = controlled. Hybrid = balanced rollout.")

    with c2:
        data_policy = st.selectbox(
            "Data Policy",
            ["Minimal", "Balanced", "Aggressive"],
            index=1,
            key=f"data_q{state['quarter']}"
        )
        st.caption("Aggressive increases performance—but raises privacy/compliance risk.")

        pr_posture = st.selectbox(
            "PR Posture",
            ["Transparent", "Quiet", "Defensive"],
            index=1,
            key=f"pr_q{state['quarter']}"
        )
        st.caption("Transparent stabilizes trust. Defensive can trigger narrative backlash.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # Controls
    run_col, reset_col = st.columns([1, 1])

    with run_col:
        if st.button("✅ Commit Decisions (Run Quarter)", key=f"run_q{state['quarter']}", use_container_width=True, disabled=state["game_over"]):
            # Store "before" for deltas
            before = {
                "valuation": state["valuation_m"],
                "trust": state["trust"],
                "gov": state["governance"],
            }

            decision = {
                "growth": growth,
                "gov_budget": gov_budget,
                "counterfactual_yes": counterfactual_yes,
                "expansion": expansion,
                "product_focus": product_focus,
                "model_strategy": model_strategy,
                "data_policy": data_policy,
                "pr_posture": pr_posture,
            }

            # Apply quarter decisions
            apply_decisions(
                state,
                growth=growth,
                gov_budget=gov_budget,
                counterfactual_yes=counterfactual_yes,
                expansion=expansion,
                product_focus=product_focus,
                model_strategy=model_strategy,
                data_policy=data_policy,
                pr_posture=pr_posture,
            )

            # Competitor acts
            comp_headlines = update_competitor_agent(state, decision)

            # Update crisis probability
            bayesian_crisis_update(state)

            # Maybe trigger a story decision event (decision tree)
            rng = get_rng(state)
            if rng.random() < event_probability(state, decision):
                ev = choose_event(state, decision)
                state["pending_event"] = ev
                state["pending_event_meta"] = {"decision": decision}
            save_rng(state, rng)

            # End checks + win checks
            end_check(state)
            win_check(state)

            # Log this quarter
            state["history"].append({
                "Quarter": state["quarter"],
                "Mode": state["mode"],
                "Growth": growth,
                "GovBudget": gov_budget,
                "Counterfactual": "YES" if counterfactual_yes else "NO",
                "Expansion": expansion,
                "Product": product_focus,
                "Model": model_strategy,
                "DataPolicy": data_policy,
                "PR": pr_posture,
                "CompStrategy": state["comp_strategy"],
                "CompStrength": round(state["comp_strength"], 1),
                "Valuation($M)": round(state["valuation_m"], 1),
                "Trust": round(state["trust"], 1),
                "Governance": round(state["governance"], 1),
                "RegPressure": round(state["reg_pressure"], 1),
                "CrisisProb(%)": round(state["crisis_prob"], 1),
                "HiddenRisk": round(state["hidden_risk"], 1),
                "Violations": state["violations"],
            })

            # Deltas for readable debrief
            deltas = {
                "valuation": state["valuation_m"] - before["valuation"],
                "trust": state["trust"] - before["trust"],
                "gov": state["governance"] - before["gov"],
            }

            event_note = None
            if state["pending_event"]:
                event_note = "A story decision has been triggered—resolve it before the next quarter."

            state["debrief"] = quarter_debrief(state, deltas, comp_headlines, event_note=event_note)

            # Headlines
            state["headlines"] = [state["debrief"]] + state["headlines"]

            # Advance time:
            # - If advanced mode (8 quarters), stop at 8 (unless game over earlier)
            # - If standard mode, keep going until player stops
            if not state["game_over"] and not state["pending_event"]:
                if state["max_quarters"] is None:
                    state["quarter"] += 1
                else:
                    if state["quarter"] >= state["max_quarters"]:
                        state["game_over"] = True
                        state["end_reason"] = "Advanced run complete: 8 quarters executed."
                    else:
                        state["quarter"] += 1

            st.session_state.state = state
            st.rerun()

    with reset_col:
        if st.button("🔄 New Run (Reset)", key="reset_all", use_container_width=True):
            st.session_state.state = init_state()
            st.rerun()

    # Headlines / narrative feed
    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Newsfeed (what the world is saying)")
    for h in state["headlines"][:8]:
        st.write("• " + h)

    # Run log
    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Run Log")
    if state["history"]:
        st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
    else:
        st.info("Commit your first quarter to generate the run log.")
        

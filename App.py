import streamlit as st
import numpy as np
import pandas as pd

# ============================================================
# MirrorWorld — AI FinTech Leadership Simulation (Prototype)
# Random, risk-based decision-tree mini events + adaptive competitor agent
# ============================================================

st.set_page_config(page_title="MirrorWorld", layout="wide")

# ----------------------------
# Helpers
# ----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

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

def fmt_m(x):
    return f"${x:.0f}M"

def event_tag(event_id: str) -> str:
    if "fair" in event_id or "credit" in event_id:
        return "⚖️ Fairness"
    if "policy" in event_id or "reg" in event_id:
        return "🏛️ Regulatory"
    if "advice" in event_id or "halluc" in event_id:
        return "🧠 GenAI"
    return "🧩 Event"

# ----------------------------
# RNG persistence (stable randomness)
# ----------------------------
def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# ----------------------------
# Decision-tree event library (3 trees)
# Most relevant in the market: hallucinations, fairness, regulatory whiplash
# ----------------------------
GENAI_HALLUCINATION_TREE = [
    {
        "id": "advice_hallucination",
        "title": "GenAI Advisory Hallucination (Stage 1)",
        "setup": "Your generative advisory tool confidently recommends an ineligible product to a customer. A screenshot is trending. Mirror AI reposts it: “This is why AI can’t be trusted in finance.”",
        "choices": [
            {
                "label": "Pause advisory + issue correction + run incident review",
                "effects": {"trust": +2.0, "governance": +3.0, "valuation_m": -10.0, "hidden_risk": -4.0, "reg_pressure": -1.0},
                "next_event": "advice_hallucination_stage2_a",
            },
            {
                "label": "Hotfix guardrails and keep it live",
                "effects": {"valuation_m": +4.0, "trust": -1.0, "hidden_risk": +4.0, "governance": +1.0},
                "next_event": "advice_hallucination_stage2_b",
            },
            {
                "label": "Deny it’s advice, claim “education only”",
                "effects": {"trust": -3.0, "reg_pressure": +5.0, "hidden_risk": +6.0, "violations": +1},
                "next_event": "advice_hallucination_stage2_c",
            },
        ],
    },
    {
        "id": "advice_hallucination_stage2_a",
        "title": "GenAI Advisory Hallucination (Stage 2)",
        "setup": "Your review finds the root cause: retrieval used an outdated policy doc. Fixing it requires tighter knowledge controls and monitoring.",
        "choices": [
            {"label": "Lock retrieval governance: approved sources + version control + audits",
             "effects": {"governance": +4.0, "hidden_risk": -6.0, "trust": +1.0, "valuation_m": -6.0}},
            {"label": "Add confidence scoring + refusal behavior for uncertainty",
             "effects": {"trust": +1.5, "hidden_risk": -4.0, "valuation_m": -4.0}},
            {"label": "Quietly patch and move on",
             "effects": {"hidden_risk": +3.0, "trust": -1.0, "reg_pressure": +2.0}},
        ],
    },
    {
        "id": "advice_hallucination_stage2_b",
        "title": "GenAI Advisory Hallucination (Stage 2)",
        "setup": "A regulator asks whether customers can distinguish model outputs from human advice. Mirror AI pitches “human-in-the-loop certified advisory” to your clients.",
        "choices": [
            {"label": "Add human review for high-impact recommendations (HITL tier)",
             "effects": {"governance": +3.0, "trust": +1.5, "valuation_m": -7.0, "reg_pressure": -2.0}},
            {"label": "Add strong disclosures + opt-in consent",
             "effects": {"trust": +0.5, "governance": +2.0, "reg_pressure": -1.0}},
            {"label": "Keep as-is; fight on speed",
             "effects": {"valuation_m": +6.0, "trust": -2.5, "hidden_risk": +5.0, "comp_strength": +4.0}},
        ],
    },
    {
        "id": "advice_hallucination_stage2_c",
        "title": "GenAI Advisory Hallucination (Stage 2)",
        "setup": "The “education only” defense backfires. The story becomes: “They knew it was risky and shipped anyway.” Press requests incident metrics.",
        "choices": [
            {"label": "Reverse course: transparency report + corrective plan",
             "effects": {"trust": +1.0, "governance": +2.0, "valuation_m": -10.0, "reg_pressure": -1.0}},
            {"label": "Limit access to beta users only and go quiet",
             "effects": {"valuation_m": -3.0, "trust": -2.0, "reg_pressure": +3.0}},
            {"label": "Launch a new feature to drown the narrative",
             "effects": {"valuation_m": +8.0, "trust": -2.5, "hidden_risk": +4.0}},
        ],
    },
]

CREDIT_FAIRNESS_TREE = [
    {
        "id": "credit_fairness_shock",
        "title": "Fair Lending Shock (Stage 1)",
        "setup": "An internal audit shows approval-rate disparity across a protected class. Mirror AI launches “bias-safe underwriting.” Investors ask if you’re exposed.",
        "choices": [
            {"label": "Freeze impacted segment + run counterfactual fairness tests",
             "effects": {"governance": +3.0, "trust": +1.5, "valuation_m": -12.0, "hidden_risk": -5.0},
             "next_event": "credit_fairness_shock_stage2_a"},
            {"label": "Patch with thresholds to hit parity this quarter",
             "effects": {"valuation_m": +5.0, "hidden_risk": +6.0, "trust": -1.5},
             "next_event": "credit_fairness_shock_stage2_b"},
            {"label": "Do nothing until complaints become external",
             "effects": {"trust": -2.5, "reg_pressure": +4.0, "hidden_risk": +8.0},
             "next_event": "credit_fairness_shock_stage2_c"},
        ],
    },
    {
        "id": "credit_fairness_shock_stage2_a",
        "title": "Fair Lending Shock (Stage 2)",
        "setup": "Counterfactual tests reveal a proxy feature driving disparities. Fixing it reduces short-term speed and accuracy.",
        "choices": [
            {"label": "Remove proxy + add explainability overlays for adverse actions",
             "effects": {"governance": +4.0, "trust": +2.0, "valuation_m": -10.0, "hidden_risk": -7.0}},
            {"label": "Keep proxy but cap influence and monitor",
             "effects": {"valuation_m": +2.0, "hidden_risk": +4.0, "reg_pressure": +2.0}},
            {"label": "Shift to a simpler interpretable scorecard model",
             "effects": {"governance": +3.0, "trust": +1.0, "valuation_m": -14.0, "hidden_risk": -4.0}},
        ],
    },
    {
        "id": "credit_fairness_shock_stage2_b",
        "title": "Fair Lending Shock (Stage 2)",
        "setup": "Your quick fix improves top-line parity. Then an advocacy group asks for subgroup metrics and method transparency. Mirror AI offers them a dashboard demo.",
        "choices": [
            {"label": "Publish subgroup metrics + fairness methodology summary",
             "effects": {"trust": +1.5, "governance": +2.0, "reg_pressure": -2.0, "valuation_m": -4.0}},
            {"label": "Refuse disclosure and cite IP protection",
             "effects": {"trust": -2.0, "reg_pressure": +5.0, "comp_strength": +3.0}},
            {"label": "Commission independent fairness assessment",
             "effects": {"governance": +3.0, "valuation_m": -7.0, "reg_pressure": -1.0}},
        ],
    },
    {
        "id": "credit_fairness_shock_stage2_c",
        "title": "Fair Lending Shock (Stage 2)",
        "setup": "Regulators request training data lineage, monitoring logs, and adverse action explainability. The deadline is tight.",
        "choices": [
            {"label": "Full cooperation + remediation plan + governance overhaul",
             "effects": {"governance": +4.0, "trust": +1.0, "reg_pressure": -4.0, "valuation_m": -8.0}},
            {"label": "Minimal response and delay details",
             "effects": {"reg_pressure": +4.0, "trust": -1.0}},
            {"label": "Miss deadline",
             "effects": {"reg_pressure": +6.0, "trust": -2.5, "violations": +1}},
        ],
    },
]

REGULATORY_DRIFT_TREE = [
    {
        "id": "policy_whiplash",
        "title": "Regulatory Whiplash (Stage 1)",
        "setup": "New supervisory guidance reframes what counts as “explainable.” Your current disclosures may now be insufficient.",
        "choices": [
            {"label": "Preemptively upgrade compliance: model cards + decision logs + audit trails",
             "effects": {"governance": +4.0, "reg_pressure": -3.0, "valuation_m": -8.0, "hidden_risk": -3.0},
             "next_event": "policy_whiplash_stage2_a"},
            {"label": "Wait and see; monitor enforcement signals",
             "effects": {"valuation_m": +3.0, "hidden_risk": +5.0, "reg_pressure": +2.0},
             "next_event": "policy_whiplash_stage2_b"},
            {"label": "Lobby hard and keep scaling",
             "effects": {"valuation_m": +6.0, "trust": -1.5, "reg_pressure": +4.0, "hidden_risk": +4.0},
             "next_event": "policy_whiplash_stage2_c"},
        ],
    },
    {
        "id": "policy_whiplash_stage2_a",
        "title": "Regulatory Whiplash (Stage 2)",
        "setup": "Your proactive package becomes a competitive asset, but it slows launches. Mirror AI tries to beat you on speed.",
        "choices": [
            {"label": "Hold discipline: governance as brand strategy",
             "effects": {"trust": +2.0, "governance": +2.0, "valuation_m": -4.0, "comp_strength": +2.0}},
            {"label": "Automate compliance to regain speed (policy-as-code)",
             "effects": {"governance": +2.0, "valuation_m": +2.0, "hidden_risk": -2.0}},
            {"label": "Cut corners to match competitor velocity",
             "effects": {"valuation_m": +6.0, "trust": -2.0, "hidden_risk": +5.0}},
        ],
    },
    {
        "id": "policy_whiplash_stage2_b",
        "title": "Regulatory Whiplash (Stage 2)",
        "setup": "Enforcement ramps faster than expected. A targeted inquiry lands asking for audit logs and explainability documentation.",
        "choices": [
            {"label": "Rapid compliance sprint + third-party audit",
             "effects": {"governance": +3.0, "reg_pressure": -2.0, "valuation_m": -7.0}},
            {"label": "Provide partial logs; claim full package is coming",
             "effects": {"reg_pressure": +3.0, "trust": -1.0, "hidden_risk": +3.0}},
            {"label": "Ignore inquiry and focus on growth",
             "effects": {"reg_pressure": +6.0, "trust": -2.0, "violations": +1}},
        ],
    },
    {
        "id": "policy_whiplash_stage2_c",
        "title": "Regulatory Whiplash (Stage 2)",
        "setup": "The lobbying story leaks. Headlines say you’re “fighting transparency.” Mirror AI positions itself as “compliance-first.”",
        "choices": [
            {"label": "Pivot: publish transparency commitments and roadmap",
             "effects": {"trust": +1.5, "governance": +2.0, "valuation_m": -6.0}},
            {"label": "Double down: speed at all costs",
             "effects": {"valuation_m": +8.0, "trust": -3.0, "hidden_risk": +6.0, "reg_pressure": +2.0}},
            {"label": "Quietly build compliance while staying silent publicly",
             "effects": {"governance": +2.0, "trust": -1.0, "reg_pressure": +1.0}},
        ],
    },
]

EVENTS = []
EVENTS += GENAI_HALLUCINATION_TREE
EVENTS += CREDIT_FAIRNESS_TREE
EVENTS += REGULATORY_DRIFT_TREE

def get_event_by_id(event_id):
    for e in EVENTS:
        if e["id"] == event_id:
            return e
    return None

def maybe_trigger_decision_event(state):
    """
    Random risk-based trigger for Stage 1 events only.
    Probability increases with hidden risk, regulatory pressure, and competitor strength.
    """
    rng = get_rng(state)

    p = 0.20
    p += 0.15 if state["hidden_risk"] >= 40 else 0.0
    p += 0.10 if state["reg_pressure"] >= 50 else 0.0
    p += 0.10 if state["comp_strength"] >= 45 else 0.0
    p = clamp(p, 0.15, 0.65)

    if rng.random() > p:
        save_rng(state, rng)
        return None

    stage1 = [e for e in EVENTS if "stage2" not in e["id"]]
    event = stage1[int(rng.integers(0, len(stage1)))]
    save_rng(state, rng)
    return event

# ----------------------------
# State initialization
# ----------------------------
def init_state(seed=7):
    rng = np.random.default_rng(seed)
    return {
        "phase": "setup",
        "quarter": 1,
        "valuation_m": 0.0,     # starts at 0
        "trust": 55.0,
        "governance": 50.0,
        "reg_pressure": 20.0,
        "crisis_prob": 8.0,
        "hidden_risk": 10.0,
        "violations": 0,

        # competitor agent
        "comp_strength": 10.0,      # 0..100
        "comp_strategy": "Observing",

        # gameplay
        "product_line": None,
        "seed_m": 0.0,
        "history": [],
        "last_headlines": ["Welcome to MirrorWorld. Choose your seed + first product line to start."],
        "game_over": False,
        "end_reason": "",

        # decision-tree mini-event system
        "pending_event": None,      # event dict awaiting decision
        "last_decisions": None,     # last quarter decisions

        "rng_state": rng.bit_generator.state,
    }

# ----------------------------
# Competitor agent (Mirror AI)
# ----------------------------
def update_competitor_agent(state):
    """
    Adaptive competitor agent:
    - chooses strategy based on player behavior
    - grows in strength with your visibility + openings you create
    - applies measurable market/regulatory effects
    """
    rng = get_rng(state)
    d = state.get("last_decisions") or {}

    growth = d.get("growth", 50)
    testing = d.get("testing", "Medium")
    pr = d.get("pr_posture", "Quiet")
    gov = d.get("gov_spend", 50)
    data_policy = d.get("data_policy", "Balanced")

    risky_fast = (growth >= 70 and testing in ["Low", "Skip"])
    disciplined = (gov >= 60 and testing in ["High", "Medium"] and pr == "Transparent")

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
    opening += 3.5 if testing in ["Low", "Skip"] else 0.5
    opening += 2.5 if pr == "Defensive" else 0.7
    opening += 2.0 if data_policy == "Aggressive" else 0.6

    comp_gain = learn_rate + opening + rng.normal(0, 1.0)
    state["comp_strength"] = clamp(state["comp_strength"] + comp_gain, 0, 100)

    headlines = []
    s = state["comp_strength"]

    if state["comp_strategy"] == "Price War":
        hit = (0.03 + 0.0006 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        if pr == "Transparent":
            state["trust"] = clamp(state["trust"] + 0.8, 0, 100)
        headlines.append("⚔️ Mirror AI triggers a price war: margins compress, churn pressure rises.")

    elif state["comp_strategy"] == "Safety-First":
        trust_hit = 1.0 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.0
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI runs a safety-first campaign: your trust is benchmarked in public.")

    elif state["comp_strategy"] == "Copycat":
        steal = (0.02 + 0.0004 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI clones your feature set: differentiation shrinks.")

    elif state["comp_strategy"] == "Regulatory Trap":
        add = 4.0 + 0.08 * s
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        if state["hidden_risk"] >= 50 or testing in ["Low", "Skip"]:
            if rng.random() < 0.35:
                state["violations"] += 1
                state["trust"] = clamp(state["trust"] - 4.0, 0, 100)
                headlines.append("📣 Mirror AI escalates: a complaint triggers an additional incident review (+1 violation).")
        headlines.append("🧾 Mirror AI sets a regulatory trap: complaints + scrutiny rise.")

    save_rng(state, rng)
    return headlines

# ----------------------------
# Core mechanics
# ----------------------------
def bayesian_crisis_update(state):
    prior = state["crisis_prob"] / 100.0
    signal = (
        0.50 * (state["hidden_risk"] / 100.0) +
        0.20 * (state["reg_pressure"] / 100.0) +
        0.20 * (max(0.0, 60.0 - state["trust"]) / 60.0) +
        0.10 * (max(0.0, 55.0 - state["governance"]) / 55.0)
    )
    signal = clamp(signal, 0.0, 1.0)
    posterior = 0.62 * prior + 0.38 * signal
    state["crisis_prob"] = clamp(posterior * 100.0, 1.0, 95.0)

def value_creation(state, growth, expansion, product_line, model_strategy):
    base = 18.0 + (growth / 100) * 55.0  # additive value creation

    if expansion == "Wide":
        base *= 1.18
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
        base *= 1.08
    elif model_strategy == "Hybrid":
        base *= 1.03
    else:
        base *= 0.98

    return base

def apply_decisions(state, growth, gov_spend, testing, expansion,
                    product_focus, model_strategy, data_policy, pr_posture):
    rng = get_rng(state)

    state["governance"] = clamp(
        state["governance"] + (gov_spend / 100) * 10.0 - (growth / 100) * 3.0,
        0, 100
    )

    if testing == "High":
        state["hidden_risk"] = clamp(state["hidden_risk"] - 7.0, 0, 100)
        state["trust"] = clamp(state["trust"] + 2.0, 0, 100)
        test_cost = 0.10
    elif testing == "Medium":
        state["hidden_risk"] = clamp(state["hidden_risk"] - 4.0, 0, 100)
        state["trust"] = clamp(state["trust"] + 1.0, 0, 100)
        test_cost = 0.06
    elif testing == "Low":
        state["hidden_risk"] = clamp(state["hidden_risk"] - 2.0, 0, 100)
        test_cost = 0.03
    else:  # Skip
        state["hidden_risk"] = clamp(state["hidden_risk"] + 5.5, 0, 100)
        state["trust"] = clamp(state["trust"] - 2.5, 0, 100)
        test_cost = 0.00

    if data_policy == "Minimal":
        state["trust"] = clamp(state["trust"] + 1.5, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] - 2.0, 0, 100)
        data_boost = 0.95
        risk_boost = 0.85
    elif data_policy == "Balanced":
        data_boost = 1.00
        risk_boost = 1.00
    else:  # Aggressive
        state["trust"] = clamp(state["trust"] - 2.0, 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] + 4.0, 0, 100)
        data_boost = 1.08
        risk_boost = 1.20

    if pr_posture == "Transparent":
        state["trust"] = clamp(state["trust"] + 1.2, 0, 100)
        pr_risk = 0.90
    elif pr_posture == "Defensive":
        state["trust"] = clamp(state["trust"] - 0.8, 0, 100)
        pr_risk = 1.05
    else:
        pr_risk = 1.00

    if product_focus == "Credit":
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.5, 0, 100)
        product_risk = 1.10
    elif product_focus == "Fraud":
        product_risk = 1.00
    else:  # Advisory
        state["trust"] = clamp(state["trust"] - 0.8, 0, 100)
        product_risk = 1.05

    trust_factor = 0.85 + (state["trust"] / 100) * 0.30
    gov_factor = 0.85 + (state["governance"] / 100) * 0.25

    created = value_creation(state, growth, expansion, product_focus, model_strategy)
    created *= trust_factor * gov_factor * data_boost
    created *= (1.0 - test_cost)
    created += rng.normal(0, 3.0)

    state["valuation_m"] = max(0.0, state["valuation_m"] + created)

    risk_add = (growth / 100) * 6.0
    risk_add += max(0.0, (70.0 - state["governance"])) / 100.0 * 4.0
    risk_add *= risk_boost * product_risk * pr_risk
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add - (gov_spend / 100) * 3.0, 0, 100)

    state["reg_pressure"] = clamp(
        state["reg_pressure"] + max(0.0, (growth - state["governance"])) / 100.0 * 9.0,
        0, 100
    )

    save_rng(state, rng)

# ----------------------------
# Event choice application (supports valuation & integer fields)
# ----------------------------
def apply_event_choice(state, effects):
    for k, v in effects.items():
        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + float(v))
        elif k == "violations":
            state["violations"] += int(v)
        elif k == "comp_strength":
            state["comp_strength"] = clamp(state["comp_strength"] + float(v), 0.0, 100.0)
        else:
            state[k] = clamp(state.get(k, 0.0) + float(v), 0.0, 100.0)

# ----------------------------
# End conditions + scoring
# ----------------------------
def end_check(state):
    if state["violations"] >= 3:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents/violations."
    elif state["trust"] < 25 and state["reg_pressure"] > 75:
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under high regulatory pressure."
    elif state["crisis_prob"] > 70:
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."
    elif state["quarter"] >= 8:
        state["game_over"] = True
        state["end_reason"] = "Completed 8 quarters."

def score(state):
    valuation_score = min(100.0, (state["valuation_m"] / 1000.0) * 100.0)
    penalty = state["reg_pressure"] * 0.25 + state["crisis_prob"] * 0.55 + state["violations"] * 10.0
    total = valuation_score * 0.50 + state["trust"] * 0.20 + state["governance"] * 0.20 - penalty * 0.10
    return clamp(total, 0.0, 100.0)

def win_condition(state):
    return (state["valuation_m"] >= 1000.0) and (state["trust"] >= 70.0) and (state["violations"] < 3)

# ----------------------------
# UI
# ----------------------------
st.title("🪞 MirrorWorld — AI FinTech Leadership Simulation (Prototype)")
st.caption("Random decision-tree mini events + adaptive Mirror AI competitor agent.")

if "state" not in st.session_state:
    st.session_state.state = init_state(seed=7)

state = st.session_state.state

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader(f"Quarter {state['quarter']} / 8")

    # ---- Setup phase ----
    if state["phase"] == "setup":
        st.markdown("### Setup: Your First Strategic Commitment")
        seed = st.select_slider("Choose seed funding (sets starting momentum)", options=[5, 10, 20, 35, 50], value=20)
        product = st.radio("Choose your first product line", ["Credit", "Fraud", "Advisory"], horizontal=True)
        st.info("Seed funding converts $0 into an operating valuation. Higher seed increases visibility and scrutiny.")
        if st.button("✅ Start Game", use_container_width=True):
            state["seed_m"] = float(seed)
            state["product_line"] = product
            state["valuation_m"] = float(seed) * 6.0  # seed -> operating valuation
            state["reg_pressure"] = clamp(state["reg_pressure"] + float(seed) / 5.0, 0, 100)
            state["phase"] = "play"
            state["last_headlines"] = [f"Seed round closed: ${seed}M. Product launched: {product}. The market is watching."]
            st.session_state.state = state
            st.rerun()

    # ---- Play phase ----
    else:
        # If an event is pending, resolve it before proceeding
        if state["pending_event"] and not state["game_over"]:
            ev = state["pending_event"]
            st.warning(f"{event_tag(ev['id'])} Decision Event: {ev['title']}")
            st.write(ev["setup"])
            st.markdown("**Choose your move:**")

            for i, ch in enumerate(ev["choices"], start=1):
                if st.button(f"Option {i}: {ch['label']}", use_container_width=True):
                    apply_event_choice(state, ch["effects"])

                    next_id = ch.get("next_event")
                    if next_id:
                        state["pending_event"] = get_event_by_id(next_id)
                        state["last_headlines"] = [f"🧩 You chose: {ch['label']} → complication unlocked."] + state["last_headlines"]
                    else:
                        state["pending_event"] = None
                        state["last_headlines"] = [f"🧩 You chose: {ch['label']}"] + state["last_headlines"]

                    # update meta-risk after choice
                    bayesian_crisis_update(state)
                    end_check(state)

                    # Quarter advances ONLY after the tree is fully resolved
                    if (not state["game_over"]) and (state["pending_event"] is None) and (state["quarter"] < 8):
                        state["quarter"] += 1

                    st.session_state.state = state
                    st.rerun()

        else:
            st.markdown("### Decisions (This Quarter)")

            growth = st.slider("Growth aggressiveness", 0, 100, 65)
            gov_spend = st.slider("Governance allocation", 0, 100, 55)
            testing = st.select_slider("Counterfactual testing", ["High", "Medium", "Low", "Skip"], value="Medium")
            expansion = st.radio("Expansion scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True)

            st.markdown("### AI & Strategy Levers")
            c1, c2 = st.columns(2)
            with c1:
                product_focus = st.selectbox(
                    "Product focus",
                    ["Credit", "Fraud", "Advisory"],
                    index=["Credit", "Fraud", "Advisory"].index(state["product_line"]) if state["product_line"] else 0
                )
                model_strategy = st.selectbox("Model strategy", ["Open", "Hybrid", "Closed"], index=1)
            with c2:
                data_policy = st.selectbox("Data policy", ["Minimal", "Balanced", "Aggressive"], index=1)
                pr_posture = st.selectbox("PR posture", ["Transparent", "Quiet", "Defensive"], index=1)

            st.markdown("---")
            run_col, reset_col = st.columns(2)

            with run_col:
                if st.button("▶️ Run Quarter", use_container_width=True, disabled=state["game_over"]):
                    # Store decisions (for competitor logic)
                    state["last_decisions"] = {
                        "growth": growth,
                        "gov_spend": gov_spend,
                        "testing": testing,
                        "expansion": expansion,
                        "product_focus": product_focus,
                        "model_strategy": model_strategy,
                        "data_policy": data_policy,
                        "pr_posture": pr_posture,
                    }

                    # Apply quarter decisions
                    apply_decisions(
                        state,
                        growth, gov_spend, testing, expansion,
                        product_focus, model_strategy, data_policy, pr_posture
                    )

                    # Competitor acts
                    comp_headlines = update_competitor_agent(state)

                    # Update crisis probability
                    bayesian_crisis_update(state)

                    # Possibly trigger a decision-tree event (random)
                    ev = maybe_trigger_decision_event(state)
                    if ev:
                        state["pending_event"] = ev

                    # End checks
                    end_check(state)

                    # Log quarter (note: quarter increments later if no pending event)
                    state["history"].append({
                        "Quarter": state["quarter"],
                        "Growth": growth,
                        "GovSpend": gov_spend,
                        "Testing": testing,
                        "Expansion": expansion,
                        "Product": product_focus,
                        "Model": model_strategy,
                        "DataPolicy": data_policy,
                        "PR": pr_posture,
                        "CompetitorStrategy": state["comp_strategy"],
                        "CompetitorStrength": round(state["comp_strength"], 1),
                        "Valuation($M)": round(state["valuation_m"], 1),
                        "Trust": round(state["trust"], 1),
                        "Governance": round(state["governance"], 1),
                        "RegPressure": round(state["reg_pressure"], 1),
                        "CrisisProb(%)": round(state["crisis_prob"], 1),
                        "HiddenRisk": round(state["hidden_risk"], 1),
                        "Violations": state["violations"],
                        "EventTriggered": ev["id"] if ev else "None"
                    })

                    # Headlines
                    base = ["Quarter executed. Market recalibrates."] + comp_headlines
                    if state["pending_event"]:
                        base = ["🧩 A decision event has been triggered. Make a choice to continue."] + base
                    state["last_headlines"] = base

                    # Advance quarter only if no pending event and not game over
                    if (not state["game_over"]) and (state["pending_event"] is None) and (state["quarter"] < 8):
                        state["quarter"] += 1
                    elif state["game_over"] and state["end_reason"] == "":
                        state["end_reason"] = "Completed 8 quarters."

                    st.session_state.state = state
                    st.rerun()

            with reset_col:
                if st.button("🔄 Reset", use_container_width=True):
                    st.session_state.state = init_state(seed=7)
                    st.rerun()

            st.markdown("### Headlines")
            for h in state["last_headlines"]:
                st.write(f"- {h}")

            st.markdown("### Run Log")
            if state["history"]:
                st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
            else:
                st.info("Run Quarter 1 to generate the log.")

with right:
    st.subheader("Real-Time Metrics")

    a, b, c = st.columns(3)
    a.metric("Valuation", fmt_m(state["valuation_m"]))
    b.metric("Trust", f"{state['trust']:.0f}/100")
    c.metric("Governance", f"{state['governance']:.0f}/100")

    d, e = st.columns(2)
    d.metric("Crisis Probability", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")
    e.metric("Reg Pressure", f"{pressure_label(state['reg_pressure'])}")

    st.markdown("---")
    st.metric("Mirror AI Strength", f"{state['comp_strength']:.0f}/100")
    st.write(f"**Mirror AI Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden Risk (latent):** {state['hidden_risk']:.0f}/100")
    st.write(f"**Violations/Incidents:** {state['violations']} (shutdown at 3)")
    st.write(f"**Score:** {score(state):.1f}/100")

    st.markdown("---")
    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
        st.success("✅ Win: unicorn + trust + no shutdown" if win_condition(state) else "❌ Did not meet win condition")
    else:
        st.info("Goal: reach **$1B valuation** in 8 quarters while keeping trust high and avoiding shutdown.")

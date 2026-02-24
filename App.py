# App.py — MirrorWorld (Premium Prototype)
# Standard = Endless (play until you stop or crash; goal: $1B)
# Advanced = 8 quarters (hard stop after Q8 unless you lose earlier)
#
# Core design:
# - You start as a $200M AI FinTech (fixed baseline).
# - You choose Seed Raise ($5–$50M). Seed affects runway/visibility/scrutiny (NOT valuation).
# - Each quarter: choose simple levers (Growth, Governance, Counterfactual YES/NO, Expansion)
# - Plus AI strategy levers (Product focus, Model strategy, Data policy, PR posture).
# - Mirror AI competitor adapts to your behavior.
# - “Choose-your-own-adventure” Decision Events trigger frequently enough to feel like a story.
#
# Goals:
# - Fun, easy to understand, but masters-level concepts (risk, governance, ethics, disruption).
# - Clear instructions, premium UI, readable metrics, non-choppy narrative.

import time
import streamlit as st
import numpy as np
import pandas as pd

# -----------------------------
# Page + Premium UI styling
# -----------------------------
st.set_page_config(page_title="MirrorWorld", layout="wide")

st.markdown(
    """
    <style>
      .mw-hero { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; }
      .mw-sub { font-size: 1.02rem; opacity: 0.90; }
      .mw-card { padding: 1rem 1.1rem; border-radius: 18px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.04); }
      .mw-chip { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; background: rgba(255,255,255,0.08); margin-right: 0.4rem; font-size: 0.85rem;}
      .mw-divider { height: 1px; background: rgba(255,255,255,0.10); margin: 0.9rem 0; }
      [data-testid="stMetricValue"] { font-size: 1.55rem; }
      [data-testid="stMetricLabel"] { font-size: 0.9rem; }
      .mw-muted { opacity: 0.86; }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, lo, hi):
    return float(max(lo, min(hi, x)))

def fmt_m(x):
    return f"${x:,.0f}M"

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

def arrow(delta):
    if delta > 1.2: return "▲"
    if delta < -1.2: return "▼"
    return "→"

# -----------------------------
# State + RNG
# -----------------------------
def init_state():
    # random seed gives replayability
    seed = int(time.time() * 1000) % 2_000_000_000
    rng = np.random.default_rng(seed)

    return {
        "phase": "setup",
        "player_name": "",
        "mode": "Standard",      # Standard (Endless) / Advanced (8)
        "max_quarters": None,    # None = endless; 8 = advanced
        "tutorial_on": True,
        "tutorial_step": 1,

        "quarter": 1,
        "game_over": False,
        "end_reason": "",
        "won": False,

        # Baseline: fixed valuation
        "valuation_m": 0.0,

        # key state
        "trust": 55.0,
        "governance": 52.0,
        "reg_pressure": 22.0,
        "crisis_prob": 10.0,
        "hidden_risk": 14.0,
        "violations": 0,

        # runway & seed choice
        "seed_m": 0.0,
        "runway_q": 6.0,          # quarters of runway buffer; seed increases this
        "product_line": None,

        # Mirror AI competitor
        "comp_strength": 12.0,     # 0..100
        "comp_strategy": "Observing",
        "comp_memory": {"skipped_checks": 0, "fast_growth": 0, "transparent": 0},

        # narrative + logs
        "headlines": ["Welcome to MirrorWorld."],
        "briefing": "",
        "debrief": "",

        # decision event system
        "pending_event": None,   # dict with title/setup/choices
        "history": [],

        "rng_state": rng.bit_generator.state,
    }

def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# -----------------------------
# Game tuning knobs (easy to adjust)
# -----------------------------
GOAL_VALUATION = 1000.0     # $1B
BASE_START_VALUATION = 200.0

# Growth tuning: “feel good” but not trivial
# typical good quarter adds ~40–120M depending on choices and health
GROWTH_BASE = 22.0          # baseline lift per quarter
GROWTH_MAX_ADD = 95.0       # additional based on growth target + multipliers

# Advanced is harsher on risk/penalties
ADV_RISK_MULT = 1.12
ADV_REG_MULT = 1.10

# -----------------------------
# Decision Events (Choose-your-own-adventure)
# -----------------------------
def decision_event_templates():
    # Keep choices understandable: each option is a plain-English move with clear tradeoffs.
    return [
        {
            "id": "credit_fairness",
            "title": "Credit Fairness Storm",
            "setup": "A report alleges biased outcomes in underwriting. It’s trending before markets open.",
            "choices": [
                ("Publish a fairness dashboard + pause one segment to remediate",
                 {"trust": +3.0, "governance": +4.0, "reg_pressure": -2.0, "valuation_m": -14.0, "hidden_risk": -8.0}),
                ("Patch quietly and keep shipping",
                 {"trust": -2.0, "governance": +1.0, "reg_pressure": +3.0, "valuation_m": -6.0, "hidden_risk": +3.5}),
                ("Deny and go defensive on comms",
                 {"trust": -5.0, "reg_pressure": +6.0, "valuation_m": -10.0, "violations": +1, "hidden_risk": +4.0}),
            ],
        },
        {
            "id": "fraud_wave",
            "title": "Fraud Spike vs Customer Harm",
            "setup": "Fraud surges. Tight controls stop losses—but freeze real customers too.",
            "choices": [
                ("Add human-in-the-loop for edge cases + monitor false positives",
                 {"trust": +2.5, "governance": +2.0, "valuation_m": -8.0, "hidden_risk": -6.0}),
                ("Keep the model strict (loss prevention first)",
                 {"trust": -3.0, "valuation_m": +8.0, "reg_pressure": +2.0, "hidden_risk": +4.5}),
                ("Roll back to the prior stable model for one quarter",
                 {"trust": +1.0, "valuation_m": -6.0, "hidden_risk": -4.0}),
            ],
        },
        {
            "id": "advisory_hallucination",
            "title": "GenAI Advice Hallucination",
            "setup": "A viral screenshot shows your AI advisor inventing a rule and recommending an unsuitable product.",
            "choices": [
                ("Add confidence gating + citations + refusal for uncertain outputs",
                 {"trust": +3.0, "governance": +3.0, "valuation_m": -10.0, "hidden_risk": -8.0, "reg_pressure": -1.0}),
                ("Add a disclaimer and continue shipping",
                 {"trust": -1.8, "valuation_m": +4.0, "hidden_risk": +4.2}),
                ("Temporarily disable advisory and relaunch safer",
                 {"trust": +1.8, "valuation_m": -12.0, "hidden_risk": -6.0}),
            ],
        },
        {
            "id": "regulator_call",
            "title": "Regulator: 'Explain It.'",
            "setup": "A regulator requests traceability—decision logs and monitoring evidence, not marketing.",
            "choices": [
                ("Provide logs + model card + monitoring plan",
                 {"governance": +4.0, "trust": +1.0, "reg_pressure": -5.0, "valuation_m": -7.0}),
                ("Provide a high-level explanation only",
                 {"governance": +1.0, "trust": -0.8, "reg_pressure": +2.5}),
                ("Delay response and lawyer up",
                 {"reg_pressure": +6.0, "trust": -2.2, "violations": +1, "valuation_m": -5.0}),
            ],
        },
        {
            "id": "mirror_undercut",
            "title": "Mirror AI Undercuts You",
            "setup": "Mirror AI launches a similar feature—cheaper, positioned as 'safer,' with polished PR.",
            "choices": [
                ("Differentiate with transparency: benchmarks + safeguards page",
                 {"trust": +2.0, "governance": +2.0, "valuation_m": -7.0, "comp_strength": -3.0}),
                ("Cut prices immediately to protect market share",
                 {"valuation_m": +9.0, "trust": -1.0, "hidden_risk": +3.0}),
                ("Escalate a narrative war (complaints + counter-campaign)",
                 {"reg_pressure": +3.0, "trust": -2.0, "comp_strength": -4.0}),
            ],
        },
    ]

def apply_effects(state, effects):
    for k, v in effects.items():
        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + float(v))
        elif k == "violations":
            state["violations"] += int(v)
        elif k == "comp_strength":
            state["comp_strength"] = clamp(state["comp_strength"] + float(v), 0, 100)
        else:
            state[k] = clamp(state.get(k, 0.0) + float(v), 0, 100)

def event_probability(state, decision):
    # Intentionally frequent enough to feel like a real story.
    p = 0.25
    p += 0.10 if state["hidden_risk"] >= 45 else 0.0
    p += 0.08 if state["reg_pressure"] >= 55 else 0.0
    p += 0.08 if state["comp_strength"] >= 45 else 0.0
    p += 0.10 if (decision["growth"] >= 70 and not decision["counterfactual_yes"]) else 0.0
    if state["mode"] == "Advanced":
        p += 0.05
    return clamp(p, 0.18, 0.65)

def choose_event(state, decision):
    rng = get_rng(state)
    templates = decision_event_templates()

    # Weighted by product focus + current context
    weights = []
    for t in templates:
        w = 1.0
        if decision["product_focus"] == "Credit" and t["id"] == "credit_fairness":
            w += 1.0
        if decision["product_focus"] == "Fraud" and t["id"] == "fraud_wave":
            w += 1.0
        if decision["product_focus"] == "Advisory" and t["id"] == "advisory_hallucination":
            w += 1.0
        if t["id"] == "regulator_call" and state["reg_pressure"] >= 50:
            w += 0.8
        if t["id"] == "mirror_undercut" and state["comp_strength"] >= 40:
            w += 0.8
        weights.append(w)

    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    idx = int(rng.choice(len(templates), p=weights))
    save_rng(state, rng)
    return templates[idx]

# -----------------------------
# Core mechanics (tuned growth math)
# -----------------------------
def compute_valuation_gain(state, decision):
    """
    Tuned for fun pacing:
      - A “good” quarter: ~60–120M gain
      - A sloppy quarter: can be 20–50M and sets up future pain
    """
    rng = get_rng(state)

    growth = decision["growth"] / 100.0
    gov = decision["gov_budget"] / 100.0
    cf_yes = decision["counterfactual_yes"]

    expansion = decision["expansion"]
    product = decision["product_focus"]
    model = decision["model_strategy"]
    data = decision["data_policy"]
    pr = decision["pr_posture"]

    # Base growth: scaled by growth target
    base = GROWTH_BASE + growth * GROWTH_MAX_ADD

    # Expansion multiplier
    if expansion == "Wide":
        base *= 1.18
    elif expansion == "Balanced":
        base *= 1.06
    else:
        base *= 0.93

    # Product upside vs sensitivity
    if product == "Fraud":
        base *= 1.10
    elif product == "Credit":
        base *= 1.04
    else:  # Advisory
        base *= 1.06

    # Model strategy
    if model == "Open":
        base *= 1.06
    elif model == "Hybrid":
        base *= 1.03
    else:  # Closed
        base *= 0.99

    # Data policy
    if data == "Aggressive":
        base *= 1.07
    elif data == "Minimal":
        base *= 0.96

    # PR posture affects conversion & retention slightly
    if pr == "Transparent":
        base *= 1.02
    elif pr == "Defensive":
        base *= 0.97

    # Health multipliers: trust + governance improve scalable execution
    trust_factor = 0.86 + (state["trust"] / 100.0) * 0.28
    gov_factor = 0.86 + (state["governance"] / 100.0) * 0.22
    base *= trust_factor * gov_factor

    # Counterfactual checks: slightly reduce immediate speed but prevent blowups
    if cf_yes:
        base *= 0.94
    else:
        base *= 1.02

    # Runway: more runway reduces forced panic decisions (slight upside)
    runway_factor = 0.98 + min(0.06, state["runway_q"] * 0.006)  # caps at +6%
    base *= runway_factor

    # Noise
    base += rng.normal(0, 4.0)

    save_rng(state, rng)
    return max(0.0, float(base))

def apply_risk_dynamics(state, decision):
    rng = get_rng(state)

    growth = decision["growth"] / 100.0
    gov = decision["gov_budget"] / 100.0
    cf_yes = decision["counterfactual_yes"]
    expansion = decision["expansion"]
    data = decision["data_policy"]
    pr = decision["pr_posture"]
    product = decision["product_focus"]

    # Governance & trust drift
    # Governance improves with spend, slightly erodes with extreme growth
    state["governance"] = clamp(
        state["governance"] + gov * 10.0 - growth * 3.2,
        0, 100
    )

    # Counterfactual YES improves trust; NO hurts trust
    state["trust"] = clamp(
        state["trust"] + (1.8 if cf_yes else -1.6) + (0.8 if pr == "Transparent" else (-0.7 if pr == "Defensive" else 0.0)),
        0, 100
    )

    # Hidden risk accumulation (compounding)
    risk_add = 4.0 + growth * 7.0
    risk_add += 2.5 if expansion == "Wide" else (1.0 if expansion == "Balanced" else 0.2)
    risk_add += 2.8 if data == "Aggressive" else (0.0 if data == "Balanced" else -1.2)
    risk_add += 1.2 if pr == "Defensive" else 0.0
    risk_add += 1.8 if product == "Credit" else (0.8 if product == "Advisory" else 0.2)

    # Governance reduces risk; counterfactual reduces compounding
    risk_add -= gov * 6.0
    if cf_yes:
        risk_add *= 0.78
    else:
        risk_add *= 1.08

    if state["mode"] == "Advanced":
        risk_add *= ADV_RISK_MULT

    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add + rng.normal(0, 1.0), 0, 100)

    # Regulatory pressure: rises when growth outpaces governance; aggressive data increases it
    reg_add = max(0.0, (decision["growth"] - state["governance"])) / 100.0 * 9.0
    reg_add += 3.5 if data == "Aggressive" else 0.0
    reg_add -= 1.5 if pr == "Transparent" else 0.0

    if state["mode"] == "Advanced":
        reg_add *= ADV_REG_MULT

    state["reg_pressure"] = clamp(state["reg_pressure"] + reg_add + rng.normal(0, 0.8), 0, 100)

    # Crisis probability update (simple Bayesian-ish smoothing)
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

    # Incidents/violations chance (readable + fair)
    # More likely with high hidden risk, high reg pressure, NO counterfactuals
    incident_p = 0.02
    incident_p += 0.0012 * state["hidden_risk"]         # up to +0.12
    incident_p += 0.0007 * state["reg_pressure"]        # up to +0.07
    incident_p += 0.03 if not cf_yes else 0.0
    incident_p += 0.02 if data == "Aggressive" else 0.0
    incident_p += 0.02 if expansion == "Wide" else 0.0
    if state["mode"] == "Advanced":
        incident_p += 0.02

    incident_p = clamp(incident_p, 0.02, 0.28)

    if rng.random() < incident_p:
        state["violations"] += 1
        state["trust"] = clamp(state["trust"] - rng.uniform(2.8, 6.8), 0, 100)

    save_rng(state, rng)

def update_runway(state, decision):
    # Runway slowly burns; good governance slows burn, aggressive growth speeds it up
    burn = 1.0
    burn += 0.3 if decision["expansion"] == "Wide" else (0.1 if decision["expansion"] == "Balanced" else -0.05)
    burn += 0.25 if decision["growth"] >= 75 else 0.0
    burn -= 0.25 if decision["gov_budget"] >= 65 else 0.0

    state["runway_q"] = max(0.0, state["runway_q"] - burn)

# -----------------------------
# Competitor (Mirror AI)
# -----------------------------
def update_competitor(state, decision):
    rng = get_rng(state)
    mem = state["comp_memory"]

    if not decision["counterfactual_yes"]:
        mem["skipped_checks"] += 1
    if decision["growth"] >= 70:
        mem["fast_growth"] += 1
    if decision["pr_posture"] == "Transparent":
        mem["transparent"] += 1

    risky = (mem["skipped_checks"] >= 2) or (decision["data_policy"] == "Aggressive") or (decision["pr_posture"] == "Defensive")
    disciplined = (decision["gov_budget"] >= 60) and decision["counterfactual_yes"] and (decision["pr_posture"] == "Transparent")

    if risky and state["reg_pressure"] >= 35:
        state["comp_strategy"] = "Regulatory Trap"
    elif disciplined and state["trust"] >= 60:
        state["comp_strategy"] = "Price War"
    elif disciplined:
        state["comp_strategy"] = "Safety-First"
    else:
        state["comp_strategy"] = "Copycat"

    # Strength grows with your visibility (valuation) + your openings
    visibility = min(1.0, state["valuation_m"] / 1000.0)
    opening = 0.8
    opening += 2.7 if not decision["counterfactual_yes"] else 0.4
    opening += 2.0 if decision["pr_posture"] == "Defensive" else 0.6
    opening += 1.7 if decision["data_policy"] == "Aggressive" else 0.5
    if state["mode"] == "Advanced":
        opening += 0.6

    gain = (2.0 + 6.0 * visibility) + opening + rng.normal(0, 0.9)
    state["comp_strength"] = clamp(state["comp_strength"] + gain, 0, 100)

    headlines = []
    s = state["comp_strength"]

    if state["comp_strategy"] == "Price War":
        hit = (0.02 + 0.00055 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        headlines.append("⚔️ Mirror AI opens a price war: you feel margin + churn pressure.")

    elif state["comp_strategy"] == "Safety-First":
        trust_hit = 0.8 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.0
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI markets 'safer by design': trust becomes a competitive scoreboard.")

    elif state["comp_strategy"] == "Copycat":
        steal = (0.017 + 0.00035 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI clones your feature: differentiation shrinks.")

    else:
        add = 3.6 + 0.08 * s
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        headlines.append("🧾 Mirror AI escalates a regulatory narrative: scrutiny rises.")
        if state["hidden_risk"] >= 55 and rng.random() < (0.30 if state["mode"] == "Advanced" else 0.22):
            state["violations"] += 1
            state["trust"] = clamp(state["trust"] - 3.8, 0, 100)
            headlines.append("📣 A complaint triggers an incident review (+1 violation).")

    save_rng(state, rng)
    return headlines

# -----------------------------
# End / Win / Score
# -----------------------------
def end_check(state):
    # Standard & Advanced both shutdown at 3 violations (keeps rubric serious)
    if state["violations"] >= 3:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents/violations."
        return

    # collapse condition
    if state["trust"] < 25 and state["reg_pressure"] > 75:
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under high regulatory pressure."
        return

    # systemic crisis cap differs by mode
    cap = 70 if state["mode"] == "Advanced" else 78
    if state["crisis_prob"] > cap:
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."
        return

def win_check(state):
    if (state["valuation_m"] >= GOAL_VALUATION) and (state["trust"] >= 70.0) and (not state["game_over"]):
        state["won"] = True

def score(state):
    val_score = min(100.0, (state["valuation_m"] / GOAL_VALUATION) * 100.0)
    penalty = state["reg_pressure"] * 0.24 + state["crisis_prob"] * 0.58 + state["violations"] * 10.0
    total = val_score * 0.52 + state["trust"] * 0.20 + state["governance"] * 0.20 - penalty * 0.10
    return clamp(total, 0.0, 100.0)

# -----------------------------
# Story copy (briefing/debrief)
# -----------------------------
def quarter_briefing(state):
    nm = state["player_name"] or "You"
    if state["trust"] >= 70:
        mood = "Markets believe you can scale responsibly."
    elif state["trust"] >= 50:
        mood = "Confidence is cautious—one bad story could swing sentiment."
    else:
        mood = "Trust is fragile. People are waiting for a reason to doubt you."

    if state["reg_pressure"] >= 70:
        reg = "Regulators are circling. Every decision needs evidence."
    elif state["reg_pressure"] >= 45:
        reg = "Scrutiny is rising—expect governance questions."
    else:
        reg = "Regulatory pressure is manageable—for now."

    if state["comp_strength"] >= 65:
        comp = "Mirror AI is strong—assume it anticipates your next move."
    elif state["comp_strength"] >= 40:
        comp = "Mirror AI is learning fast. It punishes predictable patterns."
    else:
        comp = "Mirror AI is observing and collecting signals."

    return f"**Briefing for {nm}:** {mood} {reg} {comp}"

def quarter_debrief(state, before, comp_headlines, event_triggered):
    dv = state["valuation_m"] - before["valuation_m"]
    dt = state["trust"] - before["trust"]
    dg = state["governance"] - before["governance"]

    debrief = (
        f"**Debrief:** Valuation {arrow(dv)} {fmt_m(state['valuation_m'])} "
        f"({dv:+.0f}M), Trust {arrow(dt)} {state['trust']:.0f} ({dt:+.1f}), "
        f"Governance {arrow(dg)} {state['governance']:.0f} ({dg:+.1f})."
    )

    if event_triggered:
        debrief += " A story decision has triggered—resolve it to continue."

    if comp_headlines:
        debrief += " " + " ".join(comp_headlines)

    return debrief

# -----------------------------
# Tutorial wizard (opt-in, non-condescending)
# -----------------------------
def tutorial_panel(state):
    if not state.get("tutorial_on", False):
        return

    step = int(state.get("tutorial_step", 1))
    nm = (state.get("player_name") or "You").strip() or "You"

    st.markdown("### 🧭 Optional Walkthrough")
    if step == 1:
        st.write(f"Welcome, **{nm}**. You’ll run an AI FinTech through disruption while Mirror AI competes.")
        st.write("Your scoreboard is simple: **Valuation**, **Trust**, **Governance**, and **Reg Pressure**.")
        if st.button("Next → Levers", key="tut_next_1", use_container_width=True):
            state["tutorial_step"] = 2
            st.session_state.state = state
            st.rerun()
    elif step == 2:
        st.write("Your core levers:")
        st.write("• **Growth Target** increases valuation but compounds risk.")
        st.write("• **Governance Budget** improves survivability and reduces future penalties.")
        st.write("• **Counterfactuals YES/NO**: YES slows you slightly now, but prevents blowups later.")
        if st.button("Next → How to win", key="tut_next_2", use_container_width=True):
            state["tutorial_step"] = 3
            st.session_state.state = state
            st.rerun()
    elif step == 3:
        st.write("Winning pattern (simple and realistic):")
        st.write("1) Keep **Counterfactuals = YES** most quarters when scaling.")
        st.write("2) If **Reg Pressure** spikes, avoid **Wide** expansion for a quarter.")
        st.write("3) If **Trust** dips, go **Transparent** and increase governance.")
        if st.button("Next → Play", key="tut_next_3", use_container_width=True):
            state["tutorial_step"] = 4
            st.session_state.state = state
            st.rerun()
    else:
        st.write("You’re set. Make decisions, then **Commit Quarter**. Story events will interrupt you with big choices.")
        if st.button("Hide walkthrough", key="tut_hide", use_container_width=True):
            state["tutorial_on"] = False
            st.session_state.state = state
            st.rerun()

# -----------------------------
# Start screen (premium)
# -----------------------------
def start_screen(state):
    st.markdown('<div class="mw-hero">🪞 MirrorWorld — AI FinTech Leadership Simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="mw-sub mw-muted">A premium “choose-your-own-adventure” sim: grow to $1B without collapsing trust, ethics, or compliance.</div>', unsafe_allow_html=True)

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    st.markdown("### How it works (quick)")
    st.markdown(
        """
        - You start as a **$200M** AI FinTech (growth-stage).
        - You choose a **seed raise** to set runway and scrutiny.
        - Each quarter you commit decisions; **Mirror AI** adapts; story events trigger.
        - **Win:** reach **$1B** with **Trust ≥ 70** (no shutdown).
        """
    )

    c1, c2 = st.columns([1.05, 0.95], gap="large")

    with c1:
        name = st.text_input("Your name (used in the story)", value=state.get("player_name", ""), key="setup_name")
        mode_choice = st.radio(
            "Mode",
            options=["Standard (Endless)", "Advanced (8 quarters)"],
            index=0,
            key="setup_mode"
        )
        tutorial_on = st.checkbox("Guided walkthrough (recommended first run)", value=True, key="setup_tutorial")

        st.markdown('<span class="mw-chip">Standard</span> Endless play', unsafe_allow_html=True)
        st.markdown('<span class="mw-chip">Advanced</span> Hard stop at Q8', unsafe_allow_html=True)

    with c2:
        seed_m = st.select_slider(
            "Seed raise ($M) — affects runway + visibility",
            options=[5, 10, 20, 35, 50],
            value=20,
            key="setup_seed"
        )
        product = st.radio(
            "First product line",
            ["Credit", "Fraud", "Advisory"],
            horizontal=True,
            key="setup_product"
        )

        if product == "Credit":
            st.info("**Credit**: steady growth, high fairness/explainability scrutiny.")
        elif product == "Fraud":
            st.info("**Fraud**: faster wins, risk of false positives and customer harm.")
        else:
            st.info("**Advisory**: high upside, risk of hallucinations/suitability issues.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    if st.button("🚀 Start Simulation", use_container_width=True, key="setup_start"):
        rng = get_rng(state)

        state["player_name"] = name.strip()
        state["tutorial_on"] = bool(tutorial_on)
        state["tutorial_step"] = 1

        if mode_choice.startswith("Standard"):
            state["mode"] = "Standard"
            state["max_quarters"] = None   # endless
        else:
            state["mode"] = "Advanced"
            state["max_quarters"] = 8      # hard stop

        state["seed_m"] = float(seed_m)
        state["product_line"] = product

        # Fixed baseline valuation (your request)
        state["valuation_m"] = BASE_START_VALUATION

        # Seed sets runway + scrutiny + competitor learning speed
        # (This is how you "feel" the seed choice without faking valuation.)
        state["runway_q"] = clamp(5.5 + seed_m / 10.0 + rng.uniform(-0.3, 0.3), 4.5, 11.5)

        base_reg = rng.uniform(16, 26)
        state["reg_pressure"] = clamp(base_reg + seed_m / 7.5, 0, 100)

        base_comp = rng.uniform(10, 16)
        state["comp_strength"] = clamp(base_comp + seed_m / 12.0, 0, 100)

        # Randomized but sensible starting governance/trust
        if state["mode"] == "Advanced":
            state["trust"] = float(rng.uniform(48, 60))
            state["governance"] = float(rng.uniform(45, 58))
            state["hidden_risk"] = float(rng.uniform(14, 22))
            state["crisis_prob"] = float(rng.uniform(9, 14))
        else:
            state["trust"] = float(rng.uniform(54, 68))
            state["governance"] = float(rng.uniform(50, 66))
            state["hidden_risk"] = float(rng.uniform(10, 18))
            state["crisis_prob"] = float(rng.uniform(6, 12))

        state["violations"] = 0
        state["quarter"] = 1
        state["game_over"] = False
        state["won"] = False
        state["end_reason"] = ""
        state["pending_event"] = None
        state["history"] = []

        state["comp_strategy"] = "Observing"
        state["comp_memory"] = {"skipped_checks": 0, "fast_growth": 0, "transparent": 0}

        nm = state["player_name"] or "You"
        state["headlines"] = [
            f"🎬 {nm} takes the helm of a ${BASE_START_VALUATION:.0f}M AI FinTech and raises ${seed_m:.0f}M. The market is watching."
        ]

        save_rng(state, rng)
        state["phase"] = "play"
        st.session_state.state = state
        st.rerun()

# -----------------------------
# Main
# -----------------------------
if "state" not in st.session_state:
    st.session_state.state = init_state()

state = st.session_state.state

if state["phase"] == "setup":
    start_screen(state)
    st.stop()

# -----------------------------
# Sidebar: settings + reset
# -----------------------------
with st.sidebar:
    st.subheader("Controls")

    state["tutorial_on"] = st.toggle("Tutorial wizard", value=state.get("tutorial_on", True), key="sb_tutorial")
    show_coach = st.toggle("Strategy Coach (optional)", value=True, key="sb_coach")

    st.markdown("---")
    if st.button("🔄 New randomized run", use_container_width=True, key="sb_reset"):
        st.session_state.state = init_state()
        st.rerun()

# -----------------------------
# Layout: left game / right HUD
# -----------------------------
left, right = st.columns([1.25, 0.75], gap="large")

# -----------------------------
# HUD (right) — premium and readable
# -----------------------------
with right:
    st.markdown("### Executive Dashboard")

    a, b, c = st.columns(3)
    a.metric("Val", fmt_m(state["valuation_m"]))
    b.metric("Trust", f"{state['trust']:.0f}/100")
    c.metric("Gov", f"{state['governance']:.0f}/100")

    d, e = st.columns(2)
    d.metric("Crisis", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")
    e.metric("Reg", pressure_label(state["reg_pressure"]))

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # progress bars (great on mobile)
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
    st.write(f"**Runway:** {state['runway_q']:.1f} quarters")
    st.write(f"**Violations:** {state['violations']} (shutdown at 3)")
    st.write(f"**Score:** {score(state):.1f}/100")

    if show_coach and (not state["game_over"]):
        with st.expander("🧠 Strategy Coach (optional)", expanded=False):
            tips = []
            if state["hidden_risk"] >= 55:
                tips.append("Turn **Counterfactuals = YES** next quarter to stop compounding risk.")
            if state["reg_pressure"] >= 60:
                tips.append("Avoid **Wide** expansion while pressure is high.")
            if state["trust"] < 50:
                tips.append("Use **PR = Transparent** and increase governance to stabilize trust.")
            if state["runway_q"] <= 1.5:
                tips.append("Runway is tight—reduce expansion and increase governance to avoid forced crisis decisions.")
            if not tips:
                tips.append("You’re stable—push growth carefully, and keep an eye on hidden risk.")
            for t in tips[:4]:
                st.write("• " + t)

    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
    elif state["won"]:
        st.success("🏆 You reached $1B with strong trust. You can keep playing—or end the run.")

# -----------------------------
# Game (left)
# -----------------------------
with left:
    nm = state["player_name"] or "You"
    mode_label = "Standard (Endless)" if state["max_quarters"] is None else "Advanced (8 quarters)"
    st.markdown(f"## Quarter {state['quarter']} — {mode_label}")

    tutorial_panel(state)

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # If a decision event is pending, show it and block the quarter progression.
    if state["pending_event"] and (not state["game_over"]):
        ev = state["pending_event"]
        st.warning(f"🧩 Decision Event: {ev['title']}")
        st.write(ev["setup"])
        st.markdown("**Choose your move:**")

        for i, (label, effects) in enumerate(ev["choices"], start=1):
            if st.button(f"Option {i}: {label}", use_container_width=True, key=f"ev_{ev['id']}_{state['quarter']}_{i}"):
                apply_effects(state, effects)
                end_check(state)
                win_check(state)

                state["headlines"] = [f"🧩 {nm} chose: {label}"] + state["headlines"]
                state["pending_event"] = None

                st.session_state.state = state
                st.rerun()

        st.info("This is the ‘choose-your-own-adventure’ moment—your choice has immediate and downstream effects.")
        st.stop()

    # Briefing
    state["briefing"] = quarter_briefing(state)
    st.markdown(state["briefing"])

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Make your decisions")

    # Core levers (simple)
    growth = st.slider("Growth Target", 0, 100, 65, key=f"growth_{state['quarter']}")
    st.caption("Higher growth boosts valuation now—at the cost of higher risk and scrutiny.")

    gov_budget = st.slider("Governance Budget", 0, 100, 55, key=f"gov_{state['quarter']}")
    st.caption("Funds monitoring, audits, testing, and safer deployment practices.")

    counterfactual_yes = st.toggle("Counterfactual Checks (YES/NO)", value=True, key=f"cf_{state['quarter']}")
    st.caption("YES reduces compounding hidden risk. NO increases speed now—but invites shocks later.")

    expansion = st.radio("Expansion Scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True, key=f"exp_{state['quarter']}")
    st.caption("Wide scales faster but increases failure surface area.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### AI & Strategy levers")

    c1, c2 = st.columns(2)
    with c1:
        product_focus = st.selectbox(
            "Product Focus",
            ["Credit", "Fraud", "Advisory"],
            index=["Credit", "Fraud", "Advisory"].index(state["product_line"]),
            key=f"prod_{state['quarter']}"
        )
        st.caption("Determines what operational + ethical risks dominate your quarter.")

        model_strategy = st.selectbox(
            "Model Strategy",
            ["Open", "Hybrid", "Closed"],
            index=1,
            key=f"model_{state['quarter']}"
        )
        st.caption("Open is faster/cheaper; Closed is controlled; Hybrid balances speed and control.")

    with c2:
        data_policy = st.selectbox(
            "Data Policy",
            ["Minimal", "Balanced", "Aggressive"],
            index=1,
            key=f"data_{state['quarter']}"
        )
        st.caption("Aggressive improves performance but raises privacy/compliance risk.")

        pr_posture = st.selectbox(
            "PR Posture",
            ["Transparent", "Quiet", "Defensive"],
            index=1,
            key=f"pr_{state['quarter']}"
        )
        st.caption("Transparent stabilizes trust; Defensive can backfire under scrutiny.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    run_col, stop_col = st.columns(2)

    with run_col:
        if st.button("✅ Commit Quarter", use_container_width=True, key=f"run_{state['quarter']}", disabled=state["game_over"]):
            before = {
                "valuation_m": state["valuation_m"],
                "trust": state["trust"],
                "governance": state["governance"],
            }

            decision = {
                "growth": growth,
                "gov_budget": gov_budget,
                "counterfactual_yes": bool(counterfactual_yes),
                "expansion": expansion,
                "product_focus": product_focus,
                "model_strategy": model_strategy,
                "data_policy": data_policy,
                "pr_posture": pr_posture,
            }

            # 1) Apply valuation gain (tuned)
            gain = compute_valuation_gain(state, decision)
            state["valuation_m"] = max(0.0, state["valuation_m"] + gain)

            # 2) Apply risk dynamics + possible incidents
            apply_risk_dynamics(state, decision)

            # 3) Burn runway
            update_runway(state, decision)

            # 4) Competitor acts
            comp_headlines = update_competitor(state, decision)

            # 5) Maybe trigger story event
            rng = get_rng(state)
            triggered = (rng.random() < event_probability(state, decision))
            save_rng(state, rng)
            if triggered and (not state["game_over"]):
                state["pending_event"] = choose_event(state, decision)

            # 6) End/win checks
            end_check(state)
            win_check(state)

            # 7) Log
            state["history"].append({
                "Quarter": state["quarter"],
                "Mode": state["mode"],
                "Growth": growth,
                "GovBudget": gov_budget,
                "Counterfactual": "YES" if counterfactual_yes else "NO",
                "Expansion": expansion,
                "Product": product_focus,
                "Model": model_strategy,
                "Data": data_policy,
                "PR": pr_posture,
                "Valuation($M)": round(state["valuation_m"], 1),
                "Trust": round(state["trust"], 1),
                "Governance": round(state["governance"], 1),
                "RegPressure": round(state["reg_pressure"], 1),
                "Crisis(%)": round(state["crisis_prob"], 1),
                "HiddenRisk": round(state["hidden_risk"], 1),
                "RunwayQ": round(state["runway_q"], 1),
                "MirrorAI_Strategy": state["comp_strategy"],
                "MirrorAI_Strength": round(state["comp_strength"], 1),
                "Violations": state["violations"],
            })

            # 8) Narrative
            state["debrief"] = quarter_debrief(state, before, comp_headlines, event_triggered=bool(state["pending_event"]))
            state["headlines"] = [state["debrief"]] + state["headlines"]

            # 9) Advance quarter rules
            if (not state["game_over"]) and (state["pending_event"] is None):
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

    with stop_col:
        if state["max_quarters"] is None:
            if st.button("⏸️ End run (Standard)", use_container_width=True, key="end_run_std"):
                state["game_over"] = True
                state["end_reason"] = "Run ended by player (Standard endless)."
                st.session_state.state = state
                st.rerun()

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Newsfeed")
    for h in state["headlines"][:8]:
        st.write("• " + h)

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Run Log")
    if state["history"]:
        st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
    else:
        st.info("Commit your first quarter to generate the log.")

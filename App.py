# App.py — MirrorWorld (Premium + Beginner-Friendly + Fun)
# --------------------------------------------------------
# ✅ Standard = Endless
# ✅ Advanced = 8 quarters
# ✅ Start valuation fixed at $200M
# ✅ Seed raise affects runway + visibility + scrutiny (NOT valuation)
# ✅ Counterfactual checks = YES/NO
# ✅ Clear “This Quarter’s Mission” (no confusing “first product line”)
# ✅ Visible choose-your-own-adventure decision events (decision trees)
# ✅ Detailed, beginner-friendly in-app instructions + glossary + examples
# ✅ Premium, readable HUD (no squished metric text)
#
# Run:
#   streamlit run App.py

import time
import streamlit as st
import numpy as np
import pandas as pd


# -----------------------------
# Page config + styling
# -----------------------------
st.set_page_config(page_title="MirrorWorld", layout="wide")

st.markdown(
    """
    <style>
      .mw-hero { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; }
      .mw-sub { font-size: 1.02rem; opacity: 0.92; }
      .mw-divider { height: 1px; background: rgba(255,255,255,0.12); margin: 0.95rem 0; }
      .mw-chip { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px;
                 background: rgba(255,255,255,0.08); margin-right: 0.4rem; font-size: 0.85rem; }
      .mw-muted { opacity: 0.88; }
      [data-testid="stMetricValue"] { font-size: 1.5rem; }
      [data-testid="stMetricLabel"] { font-size: 0.92rem; }
      .mw-card { padding: 1rem 1.1rem; border-radius: 18px;
                 border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.04); }
    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# Constants (tune here)
# -----------------------------
START_VALUATION_M = 200.0
GOAL_VALUATION_M = 1000.0
SHUTDOWN_VIOLATIONS = 3

# Growth pacing: fun + reachable
BASE_GROWTH = 20.0
MAX_GROWTH_ADD = 92.0
NOISE_SD = 4.0

# Advanced harshness
ADV_RISK_MULT = 1.12
ADV_REG_MULT = 1.10


# -----------------------------
# Helpers
# -----------------------------
def clamp(x, lo, hi):
    return float(max(lo, min(hi, x)))


def fmt_m(x):
    return f"${x:,.0f}M"


def risk_label(p):
    p = float(p)
    if p >= 70:
        return "Critical"
    if p >= 50:
        return "Elevated"
    if p >= 30:
        return "Moderate"
    return "Low"


def pressure_label(p):
    p = float(p)
    if p >= 80:
        return "Very High"
    if p >= 60:
        return "High"
    if p >= 40:
        return "Moderate"
    if p >= 20:
        return "Low"
    return "Very Low"


def arrow(delta):
    if delta > 1.2:
        return "▲"
    if delta < -1.2:
        return "▼"
    return "→"


# -----------------------------
# RNG + state
# -----------------------------
def init_state():
    seed = int(time.time() * 1000) % 2_000_000_000
    rng = np.random.default_rng(seed)

    return {
        "phase": "setup",

        # identity + mode
        "player_name": "",
        "mode": "Standard",        # Standard (Endless) / Advanced (8)
        "max_quarters": None,      # None=Endless, 8=Advanced
        "tutorial_on": True,
        "tutorial_step": 1,

        # time
        "quarter": 1,

        # metrics
        "valuation_m": START_VALUATION_M,
        "trust": 60.0,
        "governance": 58.0,
        "reg_pressure": 22.0,
        "crisis_prob": 10.0,
        "hidden_risk": 14.0,
        "violations": 0,
        "runway_q": 6.0,

        # seed
        "seed_m": 20.0,

        # competitor
        "comp_strength": 12.0,
        "comp_strategy": "Observing",
        "comp_memory": {"skip_checks": 0, "fast": 0, "transparent": 0},

        # status
        "game_over": False,
        "end_reason": "",
        "won": False,

        # events/log
        "pending_event": None,
        "headlines": ["Welcome to MirrorWorld."],
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
# Beginner Help Hub (instructions + glossary + examples)
# -----------------------------
MISSION_OPTIONS = [
    "Credit (underwriting)",
    "Fraud (detection)",
    "Advisory (GenAI)"
]


def mission_to_focus(mission_str: str) -> str:
    if mission_str.startswith("Credit"):
        return "Credit"
    if mission_str.startswith("Fraud"):
        return "Fraud"
    return "Advisory"


def player_help_hub(mode_label: str):
    with st.expander("🎮 How to Play (Beginner-Friendly Guide)", expanded=False):
        st.markdown(f"""
### What this is
**MirrorWorld is a leadership simulation.** Each quarter is one round of decisions.
You’re trying to **grow an AI FinTech** while avoiding ethics/compliance blowups.

### Your goal
✅ Reach **{fmt_m(GOAL_VALUATION_M)} valuation** AND keep **Trust ≥ 70**  
(Without getting shut down.)

### How you lose
❌ **{SHUTDOWN_VIOLATIONS} violations** → shutdown  
❌ Trust collapses while regulators are intense  
❌ Crisis probability gets too high

### Modes
- **Standard (Endless):** play as long as you want.
- **Advanced (8 quarters):** you get **8 rounds** to reach {fmt_m(GOAL_VALUATION_M)}.

### What you do each quarter (exact steps)
1) Pick **This Quarter’s Mission** (Credit / Fraud / Advisory)  
2) Set **Growth Target** (how aggressive you scale)  
3) Set **Governance Budget** (safety + controls)  
4) Set **Counterfactual Checks: YES/NO**  
5) Choose **Expansion** (Narrow / Balanced / Wide)  
6) Choose AI settings (Model, Data, PR)  
7) Click **Commit Quarter**  
8) If a **Story Decision** pops up, choose an option (that’s your decision tree)

### What seed raise means here
Seed affects **runway + visibility + scrutiny**. It does *not* directly change valuation.
Bigger raise = more oxygen… but more attention.
        """)

    with st.expander("🧠 Glossary (Plain English)", expanded=False):
        st.markdown(f"""
### Metrics (scoreboard)
- **Valuation:** simplified “company value.” Higher is better.
- **Trust:** customer/public confidence. Drops when you look unsafe, unfair, or misleading.
- **Governance:** your internal strength (testing, monitoring, audits, controls).
- **Reg Pressure:** how intensely regulators are watching you.
- **Hidden Risk:** risk building underneath (bias, drift, weak controls). It compounds quietly.
- **Crisis Probability:** chance of a major blow-up (investigation, incident, PR disaster).
- **Violations:** major incidents. **{SHUTDOWN_VIOLATIONS} = shutdown.**

### Your levers (what they really mean)
- **Growth Target:** faster valuation now, but higher risk and scrutiny.
- **Governance Budget:** reduces future blowups and stabilizes trust.
- **Counterfactual YES/NO:** “If one factor changes, is the model still fair/safe?”
  - **YES:** fewer future shocks
  - **NO:** faster now, riskier later
- **Expansion:**
  - **Narrow:** safer, slower
  - **Balanced:** best default
  - **Wide:** fastest, riskiest

### AI + Strategy
- **Model Strategy:** Open (fast/cheap), Hybrid (balanced), Closed (controlled)
- **Data Policy:** Minimal (privacy-friendly), Balanced (default), Aggressive (performance ↑, compliance risk ↑)
- **PR Posture:** Transparent (trust ↑), Quiet (neutral), Defensive (can backfire)
        """)

    with st.expander("🧩 If you don’t know what to pick — use these templates", expanded=False):
        df = pd.DataFrame(
            [
                ["Quick Start (recommended)", 60, 55, "YES", "Balanced", "Hybrid", "Balanced", "Transparent"],
                ["Play it Safe (stabilize)", 40, 70, "YES", "Narrow", "Closed", "Minimal", "Transparent"],
                ["Push Growth (riskier)", 80, 35, "NO", "Wide", "Open", "Aggressive", "Quiet"],
                ["Regulators are hot", 55, 75, "YES", "Narrow", "Closed", "Minimal", "Transparent"],
                ["Mirror AI attacks", 70, 60, "YES", "Balanced", "Hybrid", "Balanced", "Transparent"],
            ],
            columns=["Template", "Growth", "Governance", "Counterfactual", "Expansion", "Model", "Data", "PR"]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("These are starter builds so new players can jump in immediately—then learn by playing.")

    with st.expander("🔍 What happens if I choose… (practical shortcuts)", expanded=False):
        st.markdown("""
### Growth Target
- **0–40:** stabilize, fix issues, build trust
- **41–70:** healthy scaling (best default)
- **71–100:** sprint mode (valuation rises faster, but risk grows fast too)

### Governance Budget
- **0–40:** under-investing in safety → hidden risk compounds
- **41–70:** normal controls
- **71–100:** safety-first (slower now, fewer blowups)

### Counterfactual YES/NO
- **YES:** fewer violations + lower hidden risk over time
- **NO:** more speed now + higher chance of nasty surprises later

### Expansion
- **Narrow:** safer
- **Balanced:** consistent path
- **Wide:** faster but fragile
        """)


# -----------------------------
# Tutorial wizard (non-condescending)
# -----------------------------
def tutorial_panel(state):
    if not state.get("tutorial_on", False):
        return

    step = int(state.get("tutorial_step", 1))
    st.markdown("### 🧭 Optional Walkthrough")

    if step == 1:
        st.write("You’re running an AI FinTech while **Mirror AI** competes and regulators watch.")
        st.write("Each quarter: pick a mission, set Growth/Governance, choose Counterfactual YES/NO, then commit.")
        if st.button("Next → Levers", key="tut_next_1", use_container_width=True):
            state["tutorial_step"] = 2
            st.session_state.state = state
            st.rerun()

    elif step == 2:
        st.write("Levers, in plain English:")
        st.write("• **Growth Target**: more valuation now, more risk later.")
        st.write("• **Governance Budget**: fewer blowups, more trust.")
        st.write("• **Counterfactual YES/NO**: YES = safer, NO = faster.")
        if st.button("Next → How to win", key="tut_next_2", use_container_width=True):
            state["tutorial_step"] = 3
            st.session_state.state = state
            st.rerun()

    elif step == 3:
        st.write(f"Win by reaching **{fmt_m(GOAL_VALUATION_M)}** with **Trust ≥ 70** and no shutdown.")
        st.write("If Reg Pressure spikes, avoid Wide expansion. If Hidden Risk spikes, turn Counterfactuals YES.")
        if st.button("Done → Play", key="tut_next_3", use_container_width=True):
            state["tutorial_step"] = 4
            st.session_state.state = state
            st.rerun()
    else:
        if st.button("Hide walkthrough", key="tut_hide", use_container_width=True):
            state["tutorial_on"] = False
            st.session_state.state = state
            st.rerun()


# -----------------------------
# Events (decision trees)
# -----------------------------
def event_templates():
    return [
        {
            "id": "credit_fairness",
            "title": "Credit Fairness Storm",
            "setup": "A report alleges biased underwriting outcomes. It’s trending before markets open.",
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
            "setup": "A regulator requests traceability—decision logs and monitoring evidence, not marketing language.",
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
    p = 0.22
    p += 0.10 if state["hidden_risk"] >= 45 else 0.0
    p += 0.08 if state["reg_pressure"] >= 55 else 0.0
    p += 0.08 if state["comp_strength"] >= 45 else 0.0
    p += 0.10 if (decision["growth"] >= 70 and not decision["counterfactual_yes"]) else 0.0
    if state["mode"] == "Advanced":
        p += 0.05
    return clamp(p, 0.16, 0.62)


def choose_event(state, focus):
    rng = get_rng(state)
    templates = event_templates()

    weights = []
    for t in templates:
        w = 1.0
        if focus == "Credit" and t["id"] == "credit_fairness":
            w += 1.2
        if focus == "Fraud" and t["id"] == "fraud_wave":
            w += 1.2
        if focus == "Advisory" and t["id"] == "advisory_hallucination":
            w += 1.2
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
# Core mechanics (growth + risk)
# -----------------------------
def compute_valuation_gain(state, decision, focus):
    rng = get_rng(state)

    growth = decision["growth"] / 100.0
    base = BASE_GROWTH + growth * MAX_GROWTH_ADD

    # Expansion multiplier
    exp = decision["expansion"]
    if exp == "Wide":
        base *= 1.18
    elif exp == "Balanced":
        base *= 1.06
    else:
        base *= 0.93

    # Mission focus (light boost)
    if focus == "Fraud":
        base *= 1.10
    elif focus == "Advisory":
        base *= 1.06
    else:
        base *= 1.03

    # Model strategy
    model = decision["model_strategy"]
    if model == "Open":
        base *= 1.06
    elif model == "Hybrid":
        base *= 1.03
    else:
        base *= 0.99

    # Data policy
    data = decision["data_policy"]
    if data == "Aggressive":
        base *= 1.07
    elif data == "Minimal":
        base *= 0.96

    # PR posture
    pr = decision["pr_posture"]
    if pr == "Transparent":
        base *= 1.02
    elif pr == "Defensive":
        base *= 0.97

    # Health multipliers
    trust_factor = 0.86 + (state["trust"] / 100.0) * 0.28
    gov_factor = 0.86 + (state["governance"] / 100.0) * 0.22
    base *= trust_factor * gov_factor

    # Counterfactual YES/NO
    if decision["counterfactual_yes"]:
        base *= 0.94  # slower now, safer later
    else:
        base *= 1.02  # faster now, riskier later

    # Runway helps stability a bit
    base *= (0.98 + min(0.06, state["runway_q"] * 0.006))

    base += rng.normal(0, NOISE_SD)
    save_rng(state, rng)
    return max(0.0, float(base))


def apply_risk(state, decision, focus):
    rng = get_rng(state)

    growth = decision["growth"] / 100.0
    gov = decision["gov_budget"] / 100.0
    cf_yes = decision["counterfactual_yes"]
    exp = decision["expansion"]
    data = decision["data_policy"]
    pr = decision["pr_posture"]

    # Governance drift
    state["governance"] = clamp(state["governance"] + gov * 10.0 - growth * 3.2, 0, 100)

    # Trust drift
    trust_delta = (1.8 if cf_yes else -1.6)
    trust_delta += (0.8 if pr == "Transparent" else (-0.7 if pr == "Defensive" else 0.0))
    if data == "Minimal":
        trust_delta += 0.4
    if data == "Aggressive":
        trust_delta -= 0.6
    state["trust"] = clamp(state["trust"] + trust_delta + rng.normal(0, 0.4), 0, 100)

    # Hidden risk accumulation
    risk_add = 4.0 + growth * 7.0
    risk_add += 2.5 if exp == "Wide" else (1.0 if exp == "Balanced" else 0.2)
    risk_add += 2.8 if data == "Aggressive" else (0.0 if data == "Balanced" else -1.2)
    risk_add += 1.2 if pr == "Defensive" else 0.0
    risk_add += 1.8 if focus == "Credit" else (0.8 if focus == "Advisory" else 0.2)

    risk_add -= gov * 6.0
    risk_add *= (0.78 if cf_yes else 1.08)

    if state["mode"] == "Advanced":
        risk_add *= ADV_RISK_MULT

    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add + rng.normal(0, 1.0), 0, 100)

    # Regulatory pressure
    reg_add = max(0.0, (decision["growth"] - state["governance"])) / 100.0 * 9.0
    reg_add += 3.5 if data == "Aggressive" else 0.0
    reg_add -= 1.5 if pr == "Transparent" else 0.0
    if state["mode"] == "Advanced":
        reg_add *= ADV_REG_MULT

    state["reg_pressure"] = clamp(state["reg_pressure"] + reg_add + rng.normal(0, 0.8), 0, 100)

    # Crisis probability (smooth)
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

    # Incidents/violations probability
    incident_p = 0.02
    incident_p += 0.0012 * state["hidden_risk"]
    incident_p += 0.0007 * state["reg_pressure"]
    incident_p += 0.03 if not cf_yes else 0.0
    incident_p += 0.02 if data == "Aggressive" else 0.0
    incident_p += 0.02 if exp == "Wide" else 0.0
    if state["mode"] == "Advanced":
        incident_p += 0.02

    incident_p = clamp(incident_p, 0.02, 0.28)

    if rng.random() < incident_p:
        state["violations"] += 1
        state["trust"] = clamp(state["trust"] - rng.uniform(2.8, 6.8), 0, 100)

    save_rng(state, rng)


def burn_runway(state, decision):
    burn = 1.0
    burn += 0.30 if decision["expansion"] == "Wide" else (0.10 if decision["expansion"] == "Balanced" else -0.05)
    burn += 0.25 if decision["growth"] >= 75 else 0.0
    burn -= 0.25 if decision["gov_budget"] >= 65 else 0.0
    state["runway_q"] = max(0.0, state["runway_q"] - burn)


# -----------------------------
# Mirror AI competitor
# -----------------------------
def update_competitor(state, decision):
    rng = get_rng(state)
    mem = state["comp_memory"]

    if not decision["counterfactual_yes"]:
        mem["skip_checks"] += 1
    if decision["growth"] >= 70:
        mem["fast"] += 1
    if decision["pr_posture"] == "Transparent":
        mem["transparent"] += 1

    risky = (mem["skip_checks"] >= 2) or (decision["data_policy"] == "Aggressive") or (decision["pr_posture"] == "Defensive")
    disciplined = (decision["gov_budget"] >= 60) and decision["counterfactual_yes"] and (decision["pr_posture"] == "Transparent")

    if risky and state["reg_pressure"] >= 35:
        state["comp_strategy"] = "Regulatory Trap"
    elif disciplined and state["trust"] >= 60:
        state["comp_strategy"] = "Price War"
    elif disciplined:
        state["comp_strategy"] = "Safety-First"
    else:
        state["comp_strategy"] = "Copycat"

    visibility = min(1.0, state["valuation_m"] / 1000.0)
    opening = 0.8 + (2.7 if not decision["counterfactual_yes"] else 0.4)
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
        headlines.append("⚔️ Mirror AI opens a price war: margin pressure rises.")

    elif state["comp_strategy"] == "Safety-First":
        trust_hit = 0.8 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.0
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI markets 'safer by design': trust becomes a scoreboard.")

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
# End / win / score / narrative
# -----------------------------
def end_check(state):
    if state["violations"] >= SHUTDOWN_VIOLATIONS:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents/violations."
        return

    if state["trust"] < 25 and state["reg_pressure"] > 75:
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under high regulatory pressure."
        return

    cap = 70 if state["mode"] == "Advanced" else 78
    if state["crisis_prob"] > cap:
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."
        return


def win_check(state):
    if (state["valuation_m"] >= GOAL_VALUATION_M) and (state["trust"] >= 70) and (not state["game_over"]):
        state["won"] = True


def score(state):
    val_score = min(100.0, (state["valuation_m"] / GOAL_VALUATION_M) * 100.0)
    penalty = state["reg_pressure"] * 0.24 + state["crisis_prob"] * 0.58 + state["violations"] * 10.0
    total = val_score * 0.52 + state["trust"] * 0.20 + state["governance"] * 0.20 - penalty * 0.10
    return clamp(total, 0.0, 100.0)


def briefing(state):
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


def debrief(state, before, comp_headlines, event_triggered):
    dv = state["valuation_m"] - before["valuation_m"]
    dt = state["trust"] - before["trust"]
    dg = state["governance"] - before["governance"]

    line = (
        f"**Debrief:** Valuation {arrow(dv)} {fmt_m(state['valuation_m'])} ({dv:+.0f}M), "
        f"Trust {arrow(dt)} {state['trust']:.0f} ({dt:+.1f}), "
        f"Governance {arrow(dg)} {state['governance']:.0f} ({dg:+.1f})."
    )
    if event_triggered:
        line += " A story decision triggered—resolve it to continue."
    if comp_headlines:
        line += " " + " ".join(comp_headlines)
    return line


# -----------------------------
# Start screen
# -----------------------------
def start_screen(state):
    st.markdown('<div class="mw-hero">🪞 MirrorWorld — AI FinTech Leadership Simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="mw-sub mw-muted">Start at $200M. Choose seed for runway + scrutiny. Make decisions. Handle story events. Beat Mirror AI.</div>', unsafe_allow_html=True)

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    st.markdown("### Quick rules")
    st.markdown(
        f"""
- **Standard** = endless. **Advanced** = 8 quarters.  
- Start valuation: **{fmt_m(START_VALUATION_M)}**  
- Seed raise affects runway + visibility (not valuation).  
- **Shutdown at {SHUTDOWN_VIOLATIONS} violations.**  
- Goal: **{fmt_m(GOAL_VALUATION_M)}** with **Trust ≥ 70**.
        """
    )

    c1, c2 = st.columns([1.15, 0.85], gap="large")
    with c1:
        name = st.text_input("Your name (used in the story)", value=state.get("player_name", ""), key="setup_name")
        mode_choice = st.radio("Mode", ["Standard (Endless)", "Advanced (8 quarters)"], index=0, key="setup_mode")
        tutorial_on = st.checkbox("Optional walkthrough", value=True, key="setup_tutorial")

        st.markdown('<span class="mw-chip">Standard</span> Endless play', unsafe_allow_html=True)
        st.markdown('<span class="mw-chip">Advanced</span> 8 rounds only', unsafe_allow_html=True)

    with c2:
        seed_m = st.select_slider(
            "Seed raise ($M)",
            options=[5, 10, 20, 35, 50],
            value=20,
            key="setup_seed"
        )
        st.caption("More seed = more runway, but also more attention and scrutiny.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    if st.button("🚀 Start", use_container_width=True, key="setup_start"):
        rng = get_rng(state)

        # mode
        if mode_choice.startswith("Standard"):
            state["mode"] = "Standard"
            state["max_quarters"] = None
        else:
            state["mode"] = "Advanced"
            state["max_quarters"] = 8

        # identity + tutorial
        state["player_name"] = name.strip()
        state["tutorial_on"] = bool(tutorial_on)
        state["tutorial_step"] = 1

        # reset base metrics
        state["valuation_m"] = START_VALUATION_M
        state["seed_m"] = float(seed_m)

        # seed affects runway + scrutiny + competitor initial strength
        state["runway_q"] = clamp(5.5 + seed_m / 10.0 + rng.uniform(-0.3, 0.3), 4.5, 11.5)
        state["reg_pressure"] = clamp(rng.uniform(16, 26) + seed_m / 7.5, 0, 100)
        state["comp_strength"] = clamp(rng.uniform(10, 16) + seed_m / 12.0, 0, 100)

        # randomized but sensible start metrics
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

        # reset run
        state["quarter"] = 1
        state["violations"] = 0
        state["pending_event"] = None
        state["history"] = []
        state["game_over"] = False
        state["won"] = False
        state["end_reason"] = ""

        state["comp_strategy"] = "Observing"
        state["comp_memory"] = {"skip_checks": 0, "fast": 0, "transparent": 0}

        nm = state["player_name"] or "You"
        state["headlines"] = [
            f"🎬 {nm} steps in as CEO of a {fmt_m(START_VALUATION_M)} AI FinTech and raises {fmt_m(seed_m)}. The world starts watching."
        ]

        save_rng(state, rng)
        state["phase"] = "play"
        st.session_state.state = state
        st.rerun()


# -----------------------------
# App entry
# -----------------------------
if "state" not in st.session_state:
    st.session_state.state = init_state()

state = st.session_state.state

if state["phase"] == "setup":
    start_screen(state)
    st.stop()


# -----------------------------
# Sidebar settings
# -----------------------------
with st.sidebar:
    st.subheader("Settings")
    state["tutorial_on"] = st.toggle("Tutorial wizard", value=state.get("tutorial_on", True), key="sb_tutorial")
    show_coach = st.toggle("Strategy Coach", value=True, key="sb_coach")
    st.markdown("---")
    if st.button("🔄 New randomized run", use_container_width=True, key="sb_reset"):
        st.session_state.state = init_state()
        st.rerun()


# -----------------------------
# Layout: gameplay + HUD
# -----------------------------
left, right = st.columns([1.25, 0.75], gap="large")


# -----------------------------
# HUD (right)
# -----------------------------
with right:
    st.markdown("### Executive Dashboard")

    c1, c2, c3 = st.columns(3)
    c1.metric("Val", fmt_m(state["valuation_m"]))
    c2.metric("Trust", f"{state['trust']:.0f}/100")
    c3.metric("Gov", f"{state['governance']:.0f}/100")

    d1, d2 = st.columns(2)
    d1.metric("Crisis", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")
    d2.metric("Reg", pressure_label(state["reg_pressure"]))

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.progress(int(clamp(state["trust"], 0, 100)))
    st.caption(f"Trust: {state['trust']:.0f}/100")
    st.progress(int(clamp(state["governance"], 0, 100)))
    st.caption(f"Governance: {state['governance']:.0f}/100")
    st.progress(int(clamp(state["crisis_prob"], 0, 100)))
    st.caption(f"Crisis probability: {state['crisis_prob']:.0f}%")
    st.progress(int(clamp(state["reg_pressure"], 0, 100)))
    st.caption(f"Reg pressure: {pressure_label(state['reg_pressure'])}")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.metric("Mirror AI", f"{state['comp_strength']:.0f}/100")
    st.write(f"**Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden Risk:** {state['hidden_risk']:.0f}/100")
    st.write(f"**Runway:** {state['runway_q']:.1f} quarters")
    st.write(f"**Violations:** {state['violations']} / {SHUTDOWN_VIOLATIONS}")
    st.write(f"**Score:** {score(state):.1f}/100")

    if show_coach and not state["game_over"]:
        with st.expander("🧠 Strategy Coach (optional)", expanded=False):
            tips = []
            if state["hidden_risk"] >= 55:
                tips.append("Turn **Counterfactuals = YES** next quarter to stop compounding risk.")
            if state["reg_pressure"] >= 60:
                tips.append("Avoid **Wide** expansion while pressure is high.")
            if state["trust"] < 50:
                tips.append("Use **PR = Transparent** and raise governance to stabilize trust.")
            if state["runway_q"] <= 1.5:
                tips.append("Runway is tight—reduce expansion and avoid aggressive data policy.")
            if not tips:
                tips.append("Stable zone: you can push growth—just watch hidden risk.")
            for t in tips[:4]:
                st.write("• " + t)

    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
    elif state["won"]:
        st.success("🏆 You reached $1B with strong trust. In Standard mode you can keep playing.")


# -----------------------------
# Gameplay (left)
# -----------------------------
with left:
    mode_label = "Standard (Endless)" if state["max_quarters"] is None else "Advanced (8 quarters)"
    st.markdown(f"## Quarter {state['quarter']} — {mode_label}")

    # Full beginner-friendly instructions hub
    player_help_hub(mode_label)

    # Optional tutorial wizard
    tutorial_panel(state)

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # If a story event is pending: SHOW IT (this is the decision-tree moment)
    if state["pending_event"] and not state["game_over"]:
        ev = state["pending_event"]
        st.warning(f"🧩 Story Decision: {ev['title']}")
        st.write(ev["setup"])
        st.markdown("**Choose your move:**")

        for i, (label, effects) in enumerate(ev["choices"], start=1):
            if st.button(f"Option {i}: {label}", use_container_width=True, key=f"ev_{ev['id']}_{state['quarter']}_{i}"):
                apply_effects(state, effects)
                end_check(state)
                win_check(state)

                nm = state["player_name"] or "You"
                state["headlines"] = [f"🧩 {nm} chose: {label}"] + state["headlines"]
                state["pending_event"] = None

                st.session_state.state = state
                st.rerun()

        st.info("This is the choose-your-own-adventure moment. Your choice changes what happens next.")
        st.stop()

    # Briefing
    st.markdown(briefing(state))

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    # Decisions
    st.markdown("### 1) This Quarter’s Mission")
    mission = st.selectbox("Pick your mission", MISSION_OPTIONS, index=0, key=f"mission_{state['quarter']}")
    focus = mission_to_focus(mission)
    st.caption("Mission only affects what kinds of story events you may face this quarter. You can switch missions anytime.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 2) Core Decisions")

    growth = st.slider("Growth Target", 0, 100, 65, key=f"growth_{state['quarter']}")
    st.caption("Shortcut: 0–40 stabilize | 41–70 balanced | 71–100 sprint (risk rises fast).")

    gov_budget = st.slider("Governance Budget", 0, 100, 55, key=f"gov_{state['quarter']}")
    st.caption("More governance = fewer blowups + stronger trust over time.")

    counterfactual_yes = st.toggle("Counterfactual Checks (YES/NO)", value=True, key=f"cf_{state['quarter']}")
    st.caption("YES reduces compounding risk; NO speeds you up now but increases future incident odds.")

    expansion = st.radio("Expansion Scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True, key=f"exp_{state['quarter']}")
    st.caption("Balanced is best default. Wide is faster but fragile.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 3) AI + Strategy")

    cA, cB = st.columns(2)
    with cA:
        model_strategy = st.selectbox("Model Strategy", ["Open", "Hybrid", "Closed"], index=1, key=f"model_{state['quarter']}")
        st.caption("Hybrid is a safe default. Open is faster; Closed is more controlled.")
    with cB:
        data_policy = st.selectbox("Data Policy", ["Minimal", "Balanced", "Aggressive"], index=1, key=f"data_{state['quarter']}")
        st.caption("Aggressive can improve growth but increases privacy/compliance risk.")

    pr_posture = st.selectbox("PR Posture", ["Transparent", "Quiet", "Defensive"], index=1, key=f"pr_{state['quarter']}")
    st.caption("Transparent protects trust during shocks; Defensive can backfire under scrutiny.")

    st.markdown('<div class="mw-divider"></div>', unsafe_allow_html=True)

    run_col, end_col = st.columns(2)
    with run_col:
        if st.button("✅ Commit Quarter", use_container_width=True, key=f"run_{state['quarter']}", disabled=state["game_over"]):
            before = {
                "valuation_m": state["valuation_m"],
                "trust": state["trust"],
                "governance": state["governance"],
            }

            decision = {
                "growth": int(growth),
                "gov_budget": int(gov_budget),
                "counterfactual_yes": bool(counterfactual_yes),
                "expansion": expansion,
                "model_strategy": model_strategy,
                "data_policy": data_policy,
                "pr_posture": pr_posture,
            }

            # 1) valuation gain
            gain = compute_valuation_gain(state, decision, focus)
            state["valuation_m"] = max(0.0, state["valuation_m"] + gain)

            # 2) risk dynamics
            apply_risk(state, decision, focus)

            # 3) runway burn
            burn_runway(state, decision)

            # 4) competitor
            comp_headlines = update_competitor(state, decision)

            # 5) maybe trigger story event
            rng = get_rng(state)
            trig = (rng.random() < event_probability(state, decision))
            save_rng(state, rng)
            if trig and (not state["game_over"]):
                state["pending_event"] = choose_event(state, focus)

            # 6) end/win checks
            end_check(state)
            win_check(state)

            # 7) log row
            state["history"].append({
                "Quarter": state["quarter"],
                "Mode": state["mode"],
                "Mission": focus,
                "Growth": decision["growth"],
                "GovBudget": decision["gov_budget"],
                "Counterfactual": "YES" if decision["counterfactual_yes"] else "NO",
                "Expansion": decision["expansion"],
                "Model": decision["model_strategy"],
                "Data": decision["data_policy"],
                "PR": decision["pr_posture"],
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

            # 8) newsfeed narrative
            state["headlines"] = [debrief(state, before, comp_headlines, bool(state["pending_event"]))] + state["headlines"]

            # 9) advance quarter (ONLY if no pending event)
            if (not state["game_over"]) and (state["pending_event"] is None):
                if state["max_quarters"] is None:
                    state["quarter"] += 1  # endless
                else:
                    if state["quarter"] >= state["max_quarters"]:
                        state["game_over"] = True
                        state["end_reason"] = "Advanced run complete: 8 quarters executed."
                    else:
                        state["quarter"] += 1

            st.session_state.state = state
            st.rerun()

    with end_col:
        if state["max_quarters"] is None:
            if st.button("⏸️ End Run (Standard)", use_container_width=True, key="end_run_std"):
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

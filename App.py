import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="MirrorWorld", layout="wide")

# ---------- helpers ----------
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

# ---------- state ----------
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
        "pending_event": None,      # dict if awaiting decision
        "last_decisions": None,     # store last quarter decisions for events/competitor

        "rng_state": rng.bit_generator.state,
    }

def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# ---------- competitor agent ----------
def update_competitor_agent(state):
    """
    Mirror AI competitor adapts to player patterns.
    Outputs:
    - comp_strategy changes
    - comp_strength changes
    - valuation/trust/reg_pressure impacted (market share + narrative + complaints)
    """
    rng = get_rng(state)
    d = state.get("last_decisions") or {}

    growth = d.get("growth", 50)
    testing = d.get("testing", "Medium")
    pr = d.get("pr_posture", "Quiet")
    gov = d.get("gov_spend", 50)
    data_policy = d.get("data_policy", "Balanced")

    # Decide competitor strategy based on your profile (simple rule-based "agent")
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

    # Strength growth: competitor learns from your moves + market visibility (your valuation)
    visibility = min(1.0, state["valuation_m"] / 1000.0)  # 0..1
    learn_rate = 2.0 + 6.0 * visibility

    # If you are sloppy, competitor grows faster because you create openings
    opening = 0.0
    opening += 3.5 if testing in ["Low", "Skip"] else 0.5
    opening += 2.5 if pr == "Defensive" else 0.7
    opening += 2.0 if data_policy == "Aggressive" else 0.6

    comp_gain = learn_rate + opening + rng.normal(0, 1.0)
    state["comp_strength"] = clamp(state["comp_strength"] + comp_gain, 0, 100)

    # Apply competitor impact each quarter depending on strategy
    headlines = []
    s = state["comp_strength"]

    if state["comp_strategy"] == "Price War":
        # hurts valuation growth, slightly helps trust if you stay transparent
        hit = (0.03 + 0.0006 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        if pr == "Transparent":
            state["trust"] = clamp(state["trust"] + 0.8, 0, 100)
        headlines.append("⚔️ Mirror AI triggers a price war: margins compress, churn pressure rises.")

    elif state["comp_strategy"] == "Safety-First":
        # competitor markets “we are safer”, nudges trust dynamics against you if your governance is weak
        trust_hit = 1.0 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.0
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI runs a safety-first campaign: your trust is benchmarked in public.")

    elif state["comp_strategy"] == "Copycat":
        # steals some market share proportional to strength
        steal = (0.02 + 0.0004 * s) * state["valuation_m"]
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI clones your feature set: differentiation shrinks.")

    elif state["comp_strategy"] == "Regulatory Trap":
        # files complaints + pushes regulators
        add = 4.0 + 0.08 * s
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        # if you're already risky, increase violation risk
        if state["hidden_risk"] >= 50 or testing in ["Low", "Skip"]:
            if rng.random() < 0.35:
                state["violations"] += 1
                state["trust"] = clamp(state["trust"] - 4.0, 0, 100)
                headlines.append("📣 Mirror AI escalates: a complaint triggers an additional incident review (+1 violation).")
        headlines.append("🧾 Mirror AI sets a regulatory trap: complaints + scrutiny rise.")

    save_rng(state, rng)
    return headlines

# ---------- core mechanics ----------
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
    base = 18.0 + (growth / 100) * 55.0  # 18..73 baseline per quarter

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
    else:
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
    else:
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

# ---------- decision-tree mini-events ----------
def maybe_trigger_decision_event(state):
    """
    Trigger one mini-event after quarter simulation. It pauses the game and asks the user to choose.
    More likely when risk is rising or competitor is strong.
    """
    rng = get_rng(state)

    # probability
    p = 0.25
    p += 0.15 if state["hidden_risk"] >= 45 else 0.0
    p += 0.10 if state["reg_pressure"] >= 55 else 0.0
    p += 0.10 if state["comp_strength"] >= 45 else 0.0
    p = clamp(p, 0.15, 0.70)

    if rng.random() > p:
        save_rng(state, rng)
        return None

    # choose an event template
    templates = [
        {
            "id": "whistleblower",
            "title": "Whistleblower Email Leaks Internally",
            "setup": "A staff member claims your AI approvals are unfair and posts a thread that’s going viral inside the company.",
            "choices": [
                ("Launch an internal audit + publish preliminary findings",
                 {"trust": +2.0, "governance": +3.0, "reg_pressure": +2.0, "valuation_m": -12.0}),
                ("Quietly handle it through HR and legal",
                 {"trust": -2.0, "governance": +1.0, "reg_pressure": +3.0, "valuation_m": -5.0}),
                ("Blame the competitor and go defensive on comms",
                 {"trust": -5.0, "governance": -1.0, "reg_pressure": +5.0, "valuation_m": -8.0, "violations": +1}),
            ],
        },
        {
            "id": "model_drift",
            "title": "Silent Data Drift Detected",
            "setup": "Monitoring flags drift in one segment. It is not breaking yet, but it will compound fast if ignored.",
            "choices": [
                ("Freeze the affected model + rerun counterfactual tests",
                 {"trust": +1.0, "hidden_risk": -10.0, "valuation_m": -10.0, "governance": +2.0}),
                ("Hotfix with a quick patch and keep shipping",
                 {"hidden_risk": +6.0, "valuation_m": +6.0, "trust": -1.5}),
                ("Ignore for now and focus on growth targets",
                 {"hidden_risk": +10.0, "trust": -3.0, "reg_pressure": +4.0}),
            ],
        },
        {
            "id": "regulator_call",
            "title": "Regulator Requests an Explanation",
            "setup": "A regulator asks how your AI makes decisions. They want traceability, not marketing language.",
            "choices": [
                ("Provide a transparent model card + decision logs",
                 {"governance": +4.0, "trust": +1.0, "reg_pressure": -4.0, "valuation_m": -6.0}),
                ("Provide a high-level explanation without internals",
                 {"governance": +1.0, "reg_pressure": +2.0, "trust": -1.0}),
                ("Delay response and lawyer up",
                 {"reg_pressure": +6.0, "trust": -2.5, "violations": +1, "valuation_m": -5.0}),
            ],
        },
        {
            "id": "competitor_attack",
            "title": "Mirror AI Launches a Targeted Attack",
            "setup": "The competitor releases a feature that looks like yours, but positioned as safer and cheaper.",
            "choices": [
                ("Differentiate with transparency: publish safeguards + benchmarks",
                 {"trust": +2.0, "governance": +2.0, "valuation_m": -6.0, "comp_strength": -2.0}),
                ("Undercut pricing immediately",
                 {"valuation_m": +8.0, "trust": -1.0, "hidden_risk": +3.0}),
                ("File a complaint and escalate the narrative war",
                 {"reg_pressure": +3.0, "trust": -2.0, "comp_strength": -4.0}),
            ],
        },
    ]

    event = templates[int(rng.integers(0, len(templates)))]
    save_rng(state, rng)

    # store in state as pending
    return {
        "id": event["id"],
        "title": event["title"],
        "setup": event["setup"],
        "choices": event["choices"],
    }

def apply_event_choice(state, choice_effects):
    """
    Apply the chosen branch consequences.
    """
    for k, v in choice_effects.items():
        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + float(v))
        elif k == "violations":
            state["violations"] += int(v)
        else:
            state[k] = clamp(state.get(k, 0.0) + float(v), 0.0, 100.0)

# ---------- end conditions ----------
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

# ---------- UI ----------
st.title("🪞 MirrorWorld — AI FinTech Leadership Simulation (Prototype)")
st.caption("Decision-tree mini events + an adaptive Mirror AI competitor agent.")

if "state" not in st.session_state:
    st.session_state.state = init_state(seed=7)

state = st.session_state.state

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader(f"Quarter {state['quarter']} / 8")

    # ----- SETUP -----
    if state["phase"] == "setup":
        st.markdown("### Setup: Your First Strategic Commitment")
        seed = st.select_slider("Choose seed funding (sets starting momentum)", options=[5, 10, 20, 35, 50], value=20)
        product = st.radio("Choose your first product line", ["Credit", "Fraud", "Advisory"], horizontal=True)
        st.info("Seed funding gives you a starting valuation and visibility. Higher seed raises scrutiny.")
        if st.button("✅ Start Game", use_container_width=True):
            state["seed_m"] = float(seed)
            state["product_line"] = product
            state["valuation_m"] = float(seed) * 6.0  # seed -> operating valuation
            state["reg_pressure"] = clamp(state["reg_pressure"] + float(seed) / 5.0, 0, 100)
            state["phase"] = "play"
            state["last_headlines"] = [f"Seed round closed: ${seed}M. Product launched: {product}. The market is watching."]
            st.session_state.state = state
            st.rerun()

    # ----- PLAY -----
    else:
        # If a decision event is pending, show it FIRST and block running next quarter
        if state["pending_event"] and not state["game_over"]:
            ev = state["pending_event"]
            st.warning(f"🧩 Decision Event: {ev['title']}")
            st.write(ev["setup"])
            st.markdown("**Choose your move:**")

            for i, (label, effects) in enumerate(ev["choices"], start=1):
                if st.button(f"Option {i}: {label}", use_container_width=True):
                    apply_event_choice(state, effects)
                    bayesian_crisis_update(state)
                    end_check(state)
                    state["last_headlines"] = [f"🧩 You chose: {label}"] + state["last_headlines"]
                    state["pending_event"] = None
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
                product_focus = st.selectbox("Product focus", ["Credit", "Fraud", "Advisory"],
                                             index=["Credit","Fraud","Advisory"].index(state["product_line"]))
                model_strategy = st.selectbox("Model strategy", ["Open", "Hybrid", "Closed"], index=1)
            with c2:
                data_policy = st.selectbox("Data policy", ["Minimal", "Balanced", "Aggressive"], index=1)
                pr_posture = st.selectbox("PR posture", ["Transparent", "Quiet", "Defensive"], index=1)

            st.markdown("---")
            run_col, reset_col = st.columns(2)

            with run_col:
                if st.button("▶️ Run Quarter", use_container_width=True, disabled=state["game_over"]):
                    # store last decisions for competitor logic + events
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

                    # Apply your quarter choices
                    apply_decisions(state, growth, gov_spend, testing, expansion,
                                    product_focus, model_strategy, data_policy, pr_posture)

                    # Competitor acts every quarter (agent-based)
                    comp_headlines = update_competitor_agent(state)

                    # Update crisis probability
                    bayesian_crisis_update(state)

                    # Trigger a decision-tree mini event (pauses for your response)
                    ev = maybe_trigger_decision_event(state)
                    if ev:
                        state["pending_event"] = ev

                    # End checks
                    end_check(state)

                    # log
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
                    })

                    # headlines for this turn
                    base = ["Quarter executed. Market recalibrates."] + comp_headlines
                    if state["pending_event"]:
                        base = ["🧩 A decision event has been triggered. Resolve it to continue."] + base
                    state["last_headlines"] = base

                    # increment quarter ONLY if no pending event and not game over
                    if (not state["game_over"]) and (state["pending_event"] is None) and (state["quarter"] < 8):
                        state["quarter"] += 1
                    elif state["game_over"]:
                        if state["end_reason"] == "":
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

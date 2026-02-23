
import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="MirrorWorld", layout="wide")

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def pressure_label(p):
    if p >= 80: return "Very High"
    if p >= 60: return "High"
    if p >= 40: return "Moderate"
    if p >= 20: return "Low"
    return "Very Low"

def init_state(seed=7):
    rng = np.random.default_rng(seed)
    return {
        "quarter": 1,
        "valuation_m": 250.0,
        "trust": 62.0,
        "governance": 55.0,
        "reg_pressure": 35.0,
        "crisis_prob": 12.0,
        "hidden_risk": 18.0,
        "violations": 0,
        "history": [],
        "last_headlines": ["No major headlines yet. Run Quarter 1 to begin."],
        "game_over": False,
        "end_reason": "",
        "rng_state": rng.bit_generator.state,
    }

def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

def bayesian_crisis_update(state):
    prior = state["crisis_prob"] / 100.0
    signal = (
        0.45 * (state["hidden_risk"] / 100.0) +
        0.25 * (state["reg_pressure"] / 100.0) +
        0.20 * (max(0.0, 55.0 - state["trust"]) / 55.0) +
        0.10 * (max(0.0, 60.0 - state["governance"]) / 60.0)
    )
    signal = clamp(signal, 0.0, 1.0)
    posterior = 0.65 * prior + 0.35 * signal
    state["crisis_prob"] = clamp(posterior * 100.0, 1.0, 95.0)

def roll_events(state):
    rng = get_rng(state)

    p_reg = 0.04 + (max(0.0, 60.0 - state["governance"]) / 100.0) * 0.10 + (state["reg_pressure"] / 100.0) * 0.06
    p_backlash = 0.03 + (max(0.0, 55.0 - state["trust"]) / 100.0) * 0.10
    p_competitor = 0.04 + (state["valuation_m"] / 1000.0) * 0.06
    p_failure = 0.02 + (state["hidden_risk"] / 100.0) * 0.18

    events = []
    if rng.random() < p_reg:
        events.append("Regulatory Investigation")
    if rng.random() < p_backlash:
        events.append("Public Backlash")
    if rng.random() < p_competitor:
        events.append("AI Competitor Emerges")
    if rng.random() < p_failure:
        events.append("Model Failure Shock")

    rng.shuffle(events)
    events = events[:2]
    save_rng(state, rng)
    return events

def apply_events(state, events):
    rng = get_rng(state)
    headlines = []

    for e in events:
        if e == "Regulatory Investigation":
            hit = rng.uniform(0.03, 0.07)
            state["valuation_m"] *= (1.0 - hit)
            state["reg_pressure"] = clamp(state["reg_pressure"] + 18.0, 0, 100)
            state["trust"] = clamp(state["trust"] - 10.0, 0, 100)
            state["violations"] += 1
            headlines.append("🚨 Investigation opens: audits intensify and expansion slows.")
        elif e == "Public Backlash":
            state["trust"] = clamp(state["trust"] - rng.uniform(8, 14), 0, 100)
            state["valuation_m"] *= (1.0 - rng.uniform(0.02, 0.05))
            headlines.append("🗞️ Backlash spikes: confidence drops and acquisition costs rise.")
        elif e == "AI Competitor Emerges":
            state["valuation_m"] *= (1.0 - rng.uniform(0.01, 0.03))
            state["trust"] = clamp(state["trust"] - rng.uniform(2, 6), 0, 100)
            headlines.append("⚔️ Rival model launches: pricing tightens and churn risk rises.")
        elif e == "Model Failure Shock":
            state["trust"] = clamp(state["trust"] - rng.uniform(10, 18), 0, 100)
            state["hidden_risk"] = clamp(state["hidden_risk"] + rng.uniform(8, 14), 0, 100)
            state["reg_pressure"] = clamp(state["reg_pressure"] + rng.uniform(10, 16), 0, 100)
            state["violations"] += 1
            headlines.append("💥 Model failure: incident response activates and scrutiny increases.")

    save_rng(state, rng)
    return headlines

def apply_decisions(state, growth, gov_spend, testing, expansion):
    rng = get_rng(state)

    gov_gain = (gov_spend / 100) * 8.0
    governance_drag = (growth / 100) * 2.5
    state["governance"] = clamp(state["governance"] + gov_gain - governance_drag, 0, 100)

    growth_penalty = 0.0
    if testing == "High":
        state["hidden_risk"] = clamp(state["hidden_risk"] - 6.0, 0, 100)
        state["trust"] = clamp(state["trust"] + 2.0, 0, 100)
        growth_penalty = 0.06
    elif testing == "Medium":
        state["hidden_risk"] = clamp(state["hidden_risk"] - 3.5, 0, 100)
        state["trust"] = clamp(state["trust"] + 1.0, 0, 100)
        growth_penalty = 0.03
    elif testing == "Low":
        state["hidden_risk"] = clamp(state["hidden_risk"] - 1.5, 0, 100)
        growth_penalty = 0.01
    else:
        state["hidden_risk"] = clamp(state["hidden_risk"] + 4.5, 0, 100)
        state["trust"] = clamp(state["trust"] - 2.5, 0, 100)

    if expansion == "Wide":
        exp_boost = 1.10
        state["reg_pressure"] = clamp(state["reg_pressure"] + 6.0, 0, 100)
        state["trust"] = clamp(state["trust"] - 1.5, 0, 100)
    elif expansion == "Balanced":
        exp_boost = 1.00
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.5, 0, 100)
    else:
        exp_boost = 0.92
        state["reg_pressure"] = clamp(state["reg_pressure"] - 2.0, 0, 100)
        state["trust"] = clamp(state["trust"] + 0.8, 0, 100)

    base_growth_rate = (growth / 100) * 0.22
    noise = rng.normal(0, 0.01)
    effective_growth = max(0.0, base_growth_rate - growth_penalty + noise) * exp_boost

    trust_drag = 1.0 - max(0.0, (50.0 - state["trust"]) / 200.0)
    effective_growth *= trust_drag

    state["valuation_m"] *= (1.0 + effective_growth)

    risk_add = (growth / 100) * 5.5 + max(0.0, 60.0 - state["governance"]) / 100.0 * 4.0
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add - (gov_spend / 100) * 2.5, 0, 100)

    state["trust"] = clamp(state["trust"] - (growth / 100) * 1.3 + (state["governance"] / 100) * 0.6, 0, 100)
    state["reg_pressure"] = clamp(
        state["reg_pressure"] + max(0.0, (growth - state["governance"])) / 100.0 * 8.0,
        0, 100
    )

    save_rng(state, rng)

def end_check(state):
    if state["violations"] >= 3:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many violations/incidents."
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
    penalty = state["reg_pressure"] * 0.30 + state["crisis_prob"] * 0.50 + state["violations"] * 10.0
    total = valuation_score * 0.45 + state["trust"] * 0.20 + state["governance"] * 0.20 - penalty * 0.15
    return clamp(total, 0.0, 100.0)

def win_condition(state):
    return (state["valuation_m"] >= 1000.0) and (state["trust"] >= 70.0) and (state["violations"] < 3)

st.title("🪞 MirrorWorld — AI FinTech Leadership Simulation (Prototype)")
st.caption("Eight-quarter strategy loop with compounding risk, adaptive shocks, and leadership metrics.")

if "state" not in st.session_state:
    st.session_state.state = init_state(seed=7)

state = st.session_state.state

left, right = st.columns([1.15, 0.85], gap="large")

with left:
    st.subheader(f"Quarter {state['quarter']} / 8")

    st.markdown("### Decisions")
    growth = st.slider("Growth aggressiveness", 0, 100, 65)
    gov_spend = st.slider("Governance allocation", 0, 100, 55)
    testing = st.select_slider("Counterfactual testing", ["High", "Medium", "Low", "Skip"], value="Medium")
    expansion = st.radio("Expansion scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶️ Run Quarter", use_container_width=True, disabled=state["game_over"]):
            apply_decisions(state, growth, gov_spend, testing, expansion)

            events = roll_events(state)
            headlines = apply_events(state, events) if events else ["No major headlines this quarter."]

            bayesian_crisis_update(state)
            end_check(state)

            state["last_headlines"] = headlines
            state["history"].append({
                "Quarter": state["quarter"],
                "Growth": growth,
                "GovSpend": gov_spend,
                "Testing": testing,
                "Expansion": expansion,
                "Events": ", ".join(events) if events else "None",
                "Valuation($M)": round(state["valuation_m"], 1),
                "Trust": round(state["trust"], 1),
                "Governance": round(state["governance"], 1),
                "RegPressure": round(state["reg_pressure"], 1),
                "CrisisProb(%)": round(state["crisis_prob"], 1),
                "Violations": state["violations"],
            })

            if not state["game_over"] and state["quarter"] < 8:
                state["quarter"] += 1
            elif not state["game_over"] and state["quarter"] >= 8:
                state["game_over"] = True
                state["end_reason"] = "Completed 8 quarters."

            st.session_state.state = state
            st.rerun()

    with c2:
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
    a.metric("Valuation", f"${state['valuation_m']:.0f}M")
    b.metric("Trust Index", f"{state['trust']:.0f} / 100")
    c.metric("Governance", f"{state['governance']:.0f} / 100")

    d, e = st.columns(2)
    d.metric("Crisis Probability", f"{state['crisis_prob']:.0f}%")
    e.metric("Reg Pressure", pressure_label(state["reg_pressure"]))

    st.markdown("---")
    st.write(f"**Hidden Risk (latent):** {state['hidden_risk']:.0f} / 100")
    st.write(f"**Violations/Incidents:** {state['violations']} (shutdown at 3)")
    st.write(f"**Score:** {score(state):.1f} / 100")

    st.markdown("---")
    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f} / 100")
        st.success("✅ Win: unicorn + trust + no shutdown" if win_condition(state) else "❌ Did not meet win condition")
    else:
        st.info("Goal: reach **$1B valuation** in 8 quarters while maintaining trust and avoiding shutdown.")

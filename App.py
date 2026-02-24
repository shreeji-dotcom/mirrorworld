import streamlit as st
import numpy as np
import pandas as pd

# ============================================================
# MirrorWorld — AI FinTech Leadership Simulation (Prototype)
# - Random, risk-based decision-tree mini events (Stage 1 -> Stage 2)
# - Adaptive Mirror AI competitor agent
# - AI Copilot Mode (Off/Safe/Aggressive) + AI Briefings
# - Counterfactual testing (Yes/No)
# - Achievements panel (milestones + badges)
# - Mini decision-tree map (what chain you’re in + stage)
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
    if "credit" in event_id or "fairness" in event_id or "fair" in event_id:
        return "⚖️ Fairness"
    if "policy" in event_id or "reg" in event_id:
        return "🏛️ Regulatory"
    if "advice" in event_id or "halluc" in event_id:
        return "🧠 GenAI"
    return "🧩 Event"

def pretty_pct(x):
    return f"{x:.0f}%"

# ----------------------------
# RNG persistence (stable randomness)
# ----------------------------
def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# ============================================================
# Decision-tree event library (3 trees)
# ============================================================
GENAI_HALLUCINATION_TREE = [
    {
        "id": "advice_hallucination",
        "title": "GenAI Advisory Hallucination (Stage 1)",
        "setup": "Your generative advisory tool confidently recommends an ineligible product. A screenshot trends. Mirror AI reposts it: “This is why AI can’t be trusted in finance.”",
        "choices": [
            {
                "label": "Pause advisory + issue correction + launch incident review",
                "effects": {"trust": +2.0, "governance": +3.0, "valuation_m": -10.0, "hidden_risk": -4.0, "reg_pressure": -1.0},
                "next_event": "advice_hallucination_stage2_a",
            },
            {
                "label": "Patch guardrails fast and keep it live",
                "effects": {"valuation_m": +4.0, "trust": -1.0, "hidden_risk": +4.0, "governance": +1.0},
                "next_event": "advice_hallucination_stage2_b",
            },
            {
                "label": "Deny it’s advice, label it “education only”",
                "effects": {"trust": -3.0, "reg_pressure": +5.0, "hidden_risk": +6.0, "violations": +1},
                "next_event": "advice_hallucination_stage2_c",
            },
        ],
    },
    {
        "id": "advice_hallucination_stage2_a",
        "title": "GenAI Advisory Hallucination (Stage 2)",
        "setup": "Root cause: retrieval used an outdated policy doc. Fix requires tighter knowledge governance and monitoring.",
        "choices": [
            {"label": "Enforce approved sources + version control + audits",
             "effects": {"governance": +4.0, "hidden_risk": -6.0, "trust": +1.0, "valuation_m": -6.0}},
            {"label": "Add confidence scoring + refusal for uncertainty",
             "effects": {"trust": +1.5, "hidden_risk": -4.0, "valuation_m": -4.0}},
            {"label": "Quiet patch and move on",
             "effects": {"hidden_risk": +3.0, "trust": -1.0, "reg_pressure": +2.0}},
        ],
    },
    {
        "id": "advice_hallucination_stage2_b",
        "title": "GenAI Advisory Hallucination (Stage 2)",
        "setup": "A regulator asks whether customers can distinguish model outputs from human advice. Mirror AI pitches “HITL-certified advisory” to your clients.",
        "choices": [
            {"label": "Add human review for high-impact recommendations (HITL tier)",
             "effects": {"governance": +3.0, "trust": +1.5, "valuation_m": -7.0, "reg_pressure": -2.0}},
            {"label": "Add opt-in consent + strong disclosures",
             "effects": {"trust": +0.5, "governance": +2.0, "reg_pressure": -1.0}},
            {"label": "Keep as-is; compete on speed",
             "effects": {"valuation_m": +6.0, "trust": -2.5, "hidden_risk": +5.0, "comp_strength": +4.0}},
        ],
    },
    {
        "id": "advice_hallucination_stage2_c",
        "title": "GenAI Advisory Hallucination (Stage 2)",
        "setup": "The “education only” defense backfires. The narrative becomes: “They knew it was risky and shipped anyway.” Press requests incident metrics.",
        "choices": [
            {"label": "Reverse course: publish transparency report + corrective plan",
             "effects": {"trust": +1.0, "governance": +2.0, "valuation_m": -10.0, "reg_pressure": -1.0}},
            {"label": "Limit to beta users and go quiet",
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
        "setup": "Your audit flags approval-rate disparity for a protected class. Mirror AI launches “bias-safe underwriting.” Investors ask if you’re exposed.",
        "choices": [
            {"label": "Freeze impacted segment + run counterfactual fairness tests",
             "effects": {"governance": +3.0, "trust": +1.5, "valuation_m": -12.0, "hidden_risk": -5.0},
             "next_event": "credit_fairness_shock_stage2_a"},
            {"label": "Patch thresholds to hit parity this quarter",
             "effects": {"valuation_m": +5.0, "hidden_risk": +6.0, "trust": -1.5},
             "next_event": "credit_fairness_shock_stage2_b"},
            {"label": "Wait for external complaints before acting",
             "effects": {"trust": -2.5, "reg_pressure": +4.0, "hidden_risk": +8.0},
             "next_event": "credit_fairness_shock_stage2_c"},
        ],
    },
    {
        "id": "credit_fairness_shock_stage2_a",
        "title": "Fair Lending Shock (Stage 2)",
        "setup": "Counterfactual tests reveal a proxy feature driving disparities. Fixing it reduces short-term speed and accuracy.",
        "choices": [
            {"label": "Remove proxy + add adverse action explainability overlays",
             "effects": {"governance": +4.0, "trust": +2.0, "valuation_m": -10.0, "hidden_risk": -7.0}},
            {"label": "Keep proxy but cap influence and monitor tightly",
             "effects": {"valuation_m": +2.0, "hidden_risk": +4.0, "reg_pressure": +2.0}},
            {"label": "Switch to interpretable scorecard model",
             "effects": {"governance": +3.0, "trust": +1.0, "valuation_m": -14.0, "hidden_risk": -4.0}},
        ],
    },
    {
        "id": "credit_fairness_shock_stage2_b",
        "title": "Fair Lending Shock (Stage 2)",
        "setup": "Your parity patch works on the top line. Then an advocacy group asks for subgroup metrics and transparency. Mirror AI offers them a demo.",
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
        "setup": "Regulators request data lineage, monitoring logs, and explainability documentation. The deadline is tight.",
        "choices": [
            {"label": "Full cooperation + remediation plan + governance overhaul",
             "effects": {"governance": +4.0, "trust": +1.0, "reg_pressure": -4.0, "valuation_m": -8.0}},
            {"label": "Minimal response and delay details",
             "effects": {"reg_pressure": +4.0, "trust": -1.0}},
            {"label": "Miss the deadline",
             "effects": {"reg_pressure": +6.0, "trust": -2.5, "violations": +1}},
        ],
    },
]

REGULATORY_DRIFT_TREE = [
    {
        "id": "policy_whiplash",
        "title": "Regulatory Whiplash (Stage 1)",
        "setup": "New supervisory guidance reframes what counts as “explainable.” Your disclosures may now be insufficient.",
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
        "setup": "Your proactive package becomes a competitive asset, but slows launches. Mirror AI tries to beat you on speed.",
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
            {"label": "Provide partial logs; promise full package later",
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

def stage_from_event_id(event_id: str) -> int:
    return 2 if "stage2" in event_id else 1

def event_family(event_id: str) -> str:
    # family = first token(s) before stage2
    return event_id.split("_stage2")[0] if "_stage2" in event_id else event_id

def maybe_trigger_decision_event(state):
    """
    Random risk-based trigger for Stage 1 events only.
    Probability increases with hidden risk, regulatory pressure, and competitor strength.
    Also slightly higher when AI Copilot is Aggressive (more surface area).
    """
    rng = get_rng(state)

    p = 0.20
    p += 0.15 if state["hidden_risk"] >= 40 else 0.0
    p += 0.10 if state["reg_pressure"] >= 50 else 0.0
    p += 0.10 if state["comp_strength"] >= 45 else 0.0

    last = state.get("last_decisions") or {}
    if last.get("copilot_mode") == "Aggressive":
        p += 0.05

    p = clamp(p, 0.15, 0.70)

    if rng.random() > p:
        save_rng(state, rng)
        return None

    stage1 = [e for e in EVENTS if "stage2" not in e["id"]]
    event = stage1[int(rng.integers(0, len(stage1)))]
    save_rng(state, rng)
    return event

# ============================================================
# AI Copilot (game AI, no external API)
# ============================================================
def ai_copilot_brief(state):
    rng = get_rng(state)

    threats = []
    if state["hidden_risk"] >= 55: threats.append("latent model risk is spiking")
    if state["reg_pressure"] >= 60: threats.append("regulators are circling")
    if state["trust"] <= 45: threats.append("trust is fragile")
    if state["comp_strength"] >= 55: threats.append("Mirror AI is gaining ground fast")
    if not threats:
        threats.append("you have a clean runway—scale without getting sloppy")

    recs = []
    if state["hidden_risk"] >= 50:
        recs.append("turn counterfactual testing ON and increase governance")
    if state["reg_pressure"] >= 55:
        recs.append("prioritize audit trails, model cards, and clear disclosures")
    if state["trust"] <= 50:
        recs.append("switch PR posture to Transparent for stability")
    if state["comp_strength"] >= 55:
        recs.append("differentiate on safety + explainability, not speed alone")
    if not recs:
        recs.append("push growth, but keep one hand on risk controls")

    tone = rng.choice(["clinical", "wry", "urgent"])
    save_rng(state, rng)

    if tone == "urgent":
        return f"🚨 **AI Copilot Briefing:** {', '.join(threats)}. Recommended play: **{'; '.join(recs)}**."
    if tone == "wry":
        return f"🧠 **AI Copilot Briefing:** {', '.join(threats)}. If you want to win: **{'; '.join(recs)}**."
    return f"📌 **AI Copilot Briefing:** Signal check: {', '.join(threats)}. Strategy: **{'; '.join(recs)}**."

# ============================================================
# Achievements system
# ============================================================
ACHIEVEMENTS = [
    {
        "id": "first_launch",
        "name": "First Launch",
        "desc": "Start the game and ship your first product line.",
        "check": lambda s: s["phase"] == "play",
        "badge": "🚀",
    },
    {
        "id": "ai_guardrails",
        "name": "AI Guardrails Activated",
        "desc": "Run with counterfactual testing ON at least once.",
        "check": lambda s: any(h.get("Counterfactual") == "Yes" for h in s["history"]),
        "badge": "🧪",
    },
    {
        "id": "transparency_mode",
        "name": "Transparency Mode",
        "desc": "Choose Transparent PR at least once.",
        "check": lambda s: any(h.get("PR") == "Transparent" for h in s["history"]),
        "badge": "🔎",
    },
    {
        "id": "safe_copilot",
        "name": "Safe Copilot Operator",
        "desc": "Use AI Copilot Mode = Safe at least once.",
        "check": lambda s: any(h.get("CopilotMode") == "Safe" for h in s["history"]),
        "badge": "🛡️",
    },
    {
        "id": "survive_two_stage",
        "name": "Crisis Navigator",
        "desc": "Resolve a two-stage decision-tree event chain.",
        "check": lambda s: s.get("completed_chains", 0) >= 1,
        "badge": "🧭",
    },
    {
        "id": "keep_clean",
        "name": "Clean Compliance Streak",
        "desc": "Reach Quarter 4 with zero violations.",
        "check": lambda s: s["quarter"] >= 4 and s["violations"] == 0,
        "badge": "✅",
    },
    {
        "id": "trust_builder",
        "name": "Trust Builder",
        "desc": "Reach Trust ≥ 70 at any time.",
        "check": lambda s: s["trust"] >= 70,
        "badge": "🤝",
    },
    {
        "id": "unicorn_watch",
        "name": "Unicorn Watch",
        "desc": "Reach valuation ≥ $500M.",
        "check": lambda s: s["valuation_m"] >= 500,
        "badge": "🦄",
    },
]

def update_achievements(state):
    unlocked = state.get("achievements_unlocked", set())
    newly = []
    for a in ACHIEVEMENTS:
        if a["id"] in unlocked:
            continue
        if a["check"](state):
            unlocked.add(a["id"])
            newly.append(a)
    state["achievements_unlocked"] = unlocked
    return newly

# ============================================================
# State initialization
# ============================================================
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

        # competitor
        "comp_strength": 10.0,
        "comp_strategy": "Observing",

        # gameplay
        "product_line": None,
        "seed_m": 0.0,
        "history": [],
        "last_headlines": ["Welcome to MirrorWorld. Choose seed + product line to begin."],
        "game_over": False,
        "end_reason": "",

        # event system
        "pending_event": None,          # event dict awaiting decision
        "active_chain": None,           # family id while in stage1->stage2
        "chain_stage": 0,               # 0 none, 1 stage1, 2 stage2
        "completed_chains": 0,          # count completed two-stage chains
        "event_history": [],            # list of {quarter, event_id, stage, choice_label}

        # achievements
        "achievements_unlocked": set(),

        # last quarter decisions
        "last_decisions": None,

        "rng_state": rng.bit_generator.state,
    }

# ============================================================
# Competitor agent (Mirror AI)
# ============================================================
def update_competitor_agent(state):
    rng = get_rng(state)
    d = state.get("last_decisions") or {}

    growth = d.get("growth", 50)
    counterfactual = bool(d.get("counterfactual", True))
    pr = d.get("pr_posture", "Quiet")
    gov = d.get("gov_spend", 50)
    data_policy = d.get("data_policy", "Balanced")
    copilot_mode = d.get("copilot_mode", "Off")

    risky_fast = (growth >= 70 and (not counterfactual))
    disciplined = (gov >= 60 and counterfactual and pr == "Transparent")

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
    opening += 3.2 if not counterfactual else 0.6
    opening += 2.5 if pr == "Defensive" else 0.7
    opening += 2.0 if data_policy == "Aggressive" else 0.6
    opening += 1.0 if copilot_mode == "Aggressive" else 0.0

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
        if state["hidden_risk"] >= 50 or (not counterfactual):
            if rng.random() < 0.35:
                state["violations"] += 1
                state["trust"] = clamp(state["trust"] - 4.0, 0, 100)
                headlines.append("📣 Mirror AI escalates: a complaint triggers an incident review (+1 violation).")
        headlines.append("🧾 Mirror AI sets a regulatory trap: scrutiny rises overnight.")

    save_rng(state, rng)
    return headlines

# ============================================================
# Core mechanics
# ============================================================
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

def value_creation(growth, expansion, product_line, model_strategy):
    base = 18.0 + (growth / 100) * 55.0
    base *= 1.18 if expansion == "Wide" else (1.05 if expansion == "Balanced" else 0.92)
    base *= 1.10 if product_line == "Fraud" else (1.03 if product_line == "Credit" else 1.00)
    base *= 1.08 if model_strategy == "Open" else (1.03 if model_strategy == "Hybrid" else 0.98)
    return base

def apply_decisions(state, growth, gov_spend, counterfactual_yes, expansion,
                    product_focus, model_strategy, data_policy, pr_posture, copilot_mode):
    rng = get_rng(state)

    # Governance
    state["governance"] = clamp(
        state["governance"] + (gov_spend / 100) * 10.0 - (growth / 100) * 3.0,
        0, 100
    )

    # Counterfactual Yes/No
    if counterfactual_yes:
        state["hidden_risk"] = clamp(state["hidden_risk"] - 6.0, 0, 100)
        state["trust"] = clamp(state["trust"] + 1.5, 0, 100)
        test_cost = 0.07
    else:
        state["hidden_risk"] = clamp(state["hidden_risk"] + 6.5, 0, 100)
        state["trust"] = clamp(state["trust"] - 2.0, 0, 100)
        test_cost = 0.00

    # Data policy
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

    # PR posture
    if pr_posture == "Transparent":
        state["trust"] = clamp(state["trust"] + 1.2, 0, 100)
        pr_risk = 0.90
    elif pr_posture == "Defensive":
        state["trust"] = clamp(state["trust"] - 0.8, 0, 100)
        pr_risk = 1.05
    else:
        pr_risk = 1.00

    # Product risk
    if product_focus == "Credit":
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.5, 0, 100)
        product_risk = 1.10
    elif product_focus == "Fraud":
        product_risk = 1.00
    else:
        state["trust"] = clamp(state["trust"] - 0.8, 0, 100)
        product_risk = 1.05

    # AI Copilot Mode
    if copilot_mode == "Off":
        copilot_value = 1.00
        copilot_risk = 1.00
        copilot_trust = 0.0
    elif copilot_mode == "Safe":
        copilot_value = 1.04
        copilot_risk = 0.92
        copilot_trust = +0.8
        state["hidden_risk"] = clamp(state["hidden_risk"] - 2.0, 0, 100)
    else:
        copilot_value = 1.10
        copilot_risk = 1.20
        copilot_trust = -0.6
        state["reg_pressure"] = clamp(state["reg_pressure"] + 2.0, 0, 100)

    state["trust"] = clamp(state["trust"] + copilot_trust, 0, 100)

    # Valuation update
    trust_factor = 0.85 + (state["trust"] / 100) * 0.30
    gov_factor = 0.85 + (state["governance"] / 100) * 0.25

    created = value_creation(growth, expansion, product_focus, model_strategy)
    created *= trust_factor * gov_factor * data_boost * copilot_value
    created *= (1.0 - test_cost)
    created += rng.normal(0, 3.0)

    state["valuation_m"] = max(0.0, state["valuation_m"] + created)

    # Risk accumulation
    risk_add = (growth / 100) * 6.0
    risk_add += max(0.0, (70.0 - state["governance"])) / 100.0 * 4.0
    risk_add *= risk_boost * product_risk * pr_risk * copilot_risk
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add - (gov_spend / 100) * 3.0, 0, 100)

    # Regulatory pressure
    state["reg_pressure"] = clamp(
        state["reg_pressure"] + max(0.0, (growth - state["governance"])) / 100.0 * 9.0,
        0, 100
    )

    save_rng(state, rng)

# ============================================================
# Event effect application
# ============================================================
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

# ============================================================
# End conditions + scoring
# ============================================================
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

# ============================================================
# Sidebar directions
# ============================================================
with st.sidebar:
    st.header("🎮 MirrorWorld Directions")
    st.markdown(
        """
**You are the FinTech executive.** Every quarter, you decide how to scale AI under disruption.

**Your objective**: reach **$1B valuation** by Quarter 8 **without** triggering regulatory shutdown.

### Each Quarter
1) Set **Growth** and **Governance**  
2) Toggle **Counterfactual testing: Yes/No**  
3) Pick **Expansion scope**  
4) Choose **Product focus**, **Model strategy**, **Data policy**, and **PR posture**  
5) Choose **AI Copilot Mode** *(Off / Safe / Aggressive)*

### Random Decision-Tree Events
Events trigger randomly (risk-based).  
They unfold as: **Stage 1 → Stage 2 twist**.  
You must resolve them before continuing.

### Win / Lose
✅ Win: **$1B**, Trust ≥ 70, Violations < 3  
❌ Lose: Violations ≥ 3, Trust collapse + high pressure, or Crisis probability too high
"""
    )
    st.caption("Design tip: Safe Copilot is high-signal, low-drama. Aggressive Copilot can explode valuation—and scrutiny.")

# ============================================================
# Main UI
# ============================================================
st.title("🪞 MirrorWorld — AI FinTech Leadership Simulation (Prototype)")
st.caption("Decision trees + competitor agent + AI Copilot + achievements + event map.")

if "state" not in st.session_state:
    st.session_state.state = init_state(seed=7)

state = st.session_state.state

# Always keep achievements updated (for UI) even before actions
newly_unlocked = update_achievements(state)
if newly_unlocked:
    # show only the newest one prominently; others are in the panel
    st.toast(f"{newly_unlocked[0]['badge']} Achievement unlocked: {newly_unlocked[0]['name']}", icon="🏆")

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader(f"Quarter {state['quarter']} / 8")

    # ----------------------------
    # SETUP
    # ----------------------------
    if state["phase"] == "setup":
        st.markdown("### Setup: Start at Zero")
        seed = st.select_slider("Choose seed funding", options=[5, 10, 20, 35, 50], value=20)
        product = st.radio("Choose your first product line", ["Credit", "Fraud", "Advisory"], horizontal=True)
        st.info("Seed converts $0 into an operating valuation. Higher seed increases visibility and scrutiny.")
        if st.button("✅ Start Game", use_container_width=True):
            state["seed_m"] = float(seed)
            state["product_line"] = product
            state["valuation_m"] = float(seed) * 6.0
            state["reg_pressure"] = clamp(state["reg_pressure"] + float(seed) / 5.0, 0, 100)
            state["phase"] = "play"
            state["last_headlines"] = [f"Seed closed: ${seed}M. Product launched: {product}. Mirror AI begins tracking you."]
            # achievements update after start
            newly = update_achievements(state)
            if newly:
                state["last_headlines"] = [f"🏆 Achievement: {newly[0]['name']} unlocked."] + state["last_headlines"]
            st.session_state.state = state
            st.rerun()

    # ----------------------------
    # PLAY
    # ----------------------------
    else:
        # If an event is pending, resolve it first
        if state["pending_event"] and not state["game_over"]:
            ev = state["pending_event"]
            st.warning(f"{event_tag(ev['id'])} Decision Event: {ev['title']}")
            st.write(ev["setup"])

            # Mini decision-tree map (live)
            st.markdown("#### 🗺️ Decision-Tree Map")
            fam = state.get("active_chain")
            if fam:
                st.write(f"**Chain:** `{fam}`  |  **Stage:** {state.get('chain_stage', 0)} of 2")
                st.write("**Path:** Stage 1 → Stage 2 → Quarter continues")
            else:
                st.write("**Chain:** (starting now)  |  **Stage:** 1 of 2")

            st.markdown("**Choose your move:**")

            for i, ch in enumerate(ev["choices"], start=1):
                if st.button(f"Option {i}: {ch['label']}", use_container_width=True):
                    # Apply effects
                    apply_event_choice(state, ch["effects"])

                    # Track event chain state
                    fam_now = event_family(ev["id"])
                    if state["active_chain"] is None:
                        state["active_chain"] = fam_now
                    state["chain_stage"] = stage_from_event_id(ev["id"])

                    # Record event history
                    state["event_history"].append({
                        "Quarter": state["quarter"],
                        "EventID": ev["id"],
                        "Stage": state["chain_stage"],
                        "Choice": ch["label"],
                        "Tag": event_tag(ev["id"]),
                    })

                    next_id = ch.get("next_event")
                    if next_id:
                        # Advance to stage 2
                        state["pending_event"] = get_event_by_id(next_id)
                        state["chain_stage"] = 2
                        state["last_headlines"] = [f"🧩 You chose: {ch['label']} → twist unlocked."] + state["last_headlines"]
                    else:
                        # End chain
                        # If they made it through stage 2, count it
                        if state.get("active_chain") is not None and state.get("chain_stage") == 2:
                            state["completed_chains"] += 1

                        state["pending_event"] = None
                        state["last_headlines"] = [f"🧩 You chose: {ch['label']} → chain resolved."] + state["last_headlines"]
                        state["active_chain"] = None
                        state["chain_stage"] = 0

                    # Update risk + check end
                    bayesian_crisis_update(state)
                    end_check(state)

                    # Achievements update after resolution
                    newly = update_achievements(state)
                    if newly:
                        state["last_headlines"] = [f"🏆 Achievement: {newly[0]['name']} unlocked."] + state["last_headlines"]

                    # Advance quarter ONLY after the tree is fully resolved
                    if (not state["game_over"]) and (state["pending_event"] is None) and (state["quarter"] < 8):
                        state["quarter"] += 1

                    st.session_state.state = state
                    st.rerun()

        else:
            st.markdown("### Executive Controls (This Quarter)")

            growth = st.slider("Growth aggressiveness", 0, 100, 65)
            gov_spend = st.slider("Governance allocation", 0, 100, 55)
            counterfactual_yes = st.toggle("Counterfactual testing (Yes/No)", value=True)
            expansion = st.radio("Expansion scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True)

            st.markdown("### AI + Strategy Levers")
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

            st.markdown("### GenAI Deployment Lever")
            copilot_mode = st.radio("AI Copilot Mode", ["Off", "Safe", "Aggressive"], index=1, horizontal=True)
            st.caption("Safe = controlled automation. Aggressive = speed-first GenAI with higher scrutiny risk.")

            st.markdown("---")
            run_col, reset_col = st.columns(2)

            with run_col:
                if st.button("▶️ Run Quarter", use_container_width=True, disabled=state["game_over"]):
                    state["last_decisions"] = {
                        "growth": growth,
                        "gov_spend": gov_spend,
                        "counterfactual": counterfactual_yes,
                        "expansion": expansion,
                        "product_focus": product_focus,
                        "model_strategy": model_strategy,
                        "data_policy": data_policy,
                        "pr_posture": pr_posture,
                        "copilot_mode": copilot_mode,
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
                        pr_posture=pr_posture,
                        copilot_mode=copilot_mode,
                    )

                    # Competitor acts
                    comp_headlines = update_competitor_agent(state)

                    # Update crisis probability
                    bayesian_crisis_update(state)

                    # Maybe trigger a decision-tree event
                    ev = maybe_trigger_decision_event(state)
                    if ev:
                        state["pending_event"] = ev
                        # start chain tracking
                        state["active_chain"] = event_family(ev["id"])
                        state["chain_stage"] = 1

                    # End checks
                    end_check(state)

                    # AI briefing
                    briefing = ai_copilot_brief(state)

                    # Achievements after quarter action
                    newly = update_achievements(state)

                    # Log quarter
                    state["history"].append({
                        "Quarter": state["quarter"],
                        "Growth": growth,
                        "GovSpend": gov_spend,
                        "Counterfactual": "Yes" if counterfactual_yes else "No",
                        "Expansion": expansion,
                        "Product": product_focus,
                        "Model": model_strategy,
                        "DataPolicy": data_policy,
                        "PR": pr_posture,
                        "CopilotMode": copilot_mode,
                        "CompetitorStrategy": state["comp_strategy"],
                        "CompetitorStrength": round(state["comp_strength"], 1),
                        "Valuation($M)": round(state["valuation_m"], 1),
                        "Trust": round(state["trust"], 1),
                        "Governance": round(state["governance"], 1),
                        "RegPressure": round(state["reg_pressure"], 1),
                        "CrisisProb(%)": round(state["crisis_prob"], 1),
                        "HiddenRisk": round(state["hidden_risk"], 1),
                        "Violations": state["violations"],
                        "EventTriggered": ev["id"] if ev else "None",
                    })

                    # Headlines
                    base = ["Quarter executed. Market recalibrates."] + comp_headlines
                    if state["pending_event"]:
                        base = ["🧩 A decision-tree event triggered. Resolve it to continue."] + base
                    if newly:
                        base = [f"🏆 Achievement unlocked: {newly[0]['name']}"] + base

                    state["last_headlines"] = [briefing] + base

                    # Advance quarter only if no pending event and not game over
                    if (not state["game_over"]) and (state["pending_event"] is None) and (state["quarter"] < 8):
                        state["quarter"] += 1

                    st.session_state.state = state
                    st.rerun()

            with reset_col:
                if st.button("🔄 Reset", use_container_width=True):
                    st.session_state.state = init_state(seed=7)
                    st.rerun()

            # Headlines + briefings
            st.markdown("### Headlines + AI Briefing")
            for h in state["last_headlines"]:
                st.write(f"- {h}")

            # Logs
            st.markdown("### Run Log")
            if state["history"]:
                st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
            else:
                st.info("Run Quarter 1 to generate the log.")

            # Event history (optional but impressive)
            with st.expander("🗂️ Event History (for your video walkthrough)"):
                if state["event_history"]:
                    st.dataframe(pd.DataFrame(state["event_history"]), use_container_width=True, hide_index=True)
                else:
                    st.write("No events yet. (They trigger randomly based on risk.)")

with right:
    st.subheader("Real-Time Metrics")

    a, b, c = st.columns(3)
    a.metric("Valuation", fmt_m(state["valuation_m"]))
    b.metric("Trust", f"{state['trust']:.0f}/100")
    c.metric("Governance", f"{state['governance']:.0f}/100")

    d, e = st.columns(2)
    d.metric("Crisis Probability", f"{pretty_pct(state['crisis_prob'])} ({risk_label(state['crisis_prob'])})")
    e.metric("Reg Pressure", f"{pressure_label(state['reg_pressure'])}")

    st.markdown("---")
    st.metric("Mirror AI Strength", f"{state['comp_strength']:.0f}/100")
    st.write(f"**Mirror AI Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden Risk (latent):** {state['hidden_risk']:.0f}/100")
    st.write(f"**Violations/Incidents:** {state['violations']} (shutdown at 3)")
    st.write(f"**Score:** {score(state):.1f}/100")

    # ----------------------------
    # Achievements panel
    # ----------------------------
    st.markdown("---")
    st.subheader("🏆 Achievements")
    unlocked_ids = state.get("achievements_unlocked", set())

    # Show progress summary
    st.write(f"Unlocked: **{len(unlocked_ids)} / {len(ACHIEVEMENTS)}**")

    # Render achievements list
    for a in ACHIEVEMENTS:
        unlocked = a["id"] in unlocked_ids
        icon = a["badge"] if unlocked else "⬜"
        status = "Unlocked" if unlocked else "Locked"
        st.write(f"{icon} **{a['name']}** — {status}")
        st.caption(a["desc"])

    # ----------------------------
    # Mini decision-tree map (always visible)
    # ----------------------------
    st.markdown("---")
    st.subheader("🗺️ Decision-Tree Map")
    if state["pending_event"]:
        fam = state.get("active_chain") or event_family(state["pending_event"]["id"])
        st.write(f"**Active chain:** `{fam}`")
        st.write(f"**Current stage:** {stage_from_event_id(state['pending_event']['id'])} of 2")
        st.write("**Flow:** Stage 1 decision → Twist (Stage 2) → Quarter continues")
    else:
        st.write("No active chain right now.")
        st.write("Events trigger randomly after a quarter, based on risk + competitor pressure.")

    st.markdown("---")
    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
        st.success("✅ Win: unicorn + trust + no shutdown" if win_condition(state) else "❌ Did not meet win condition")
    else:
        st.info("Goal: reach **$1B valuation** in 8 quarters while keeping trust high and avoiding shutdown.")

import streamlit as st
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

# ============================================================
# MirrorWorld — ADVANCED (Lax + More Events + Sandbox Win)
# What’s new vs prior version:
# ✅ "Advanced Mode" (sandbox): play beyond 8 quarters until you hit $1B
# ✅ Difficulty lever: Market Leniency (Laxness) — makes the world easier
# ✅ More decision trees (6 total) with Stage 1 -> Stage 2 twists
# ✅ Still masters-level: fairness, regulation, GenAI boundaries, incident response, resilience
# ✅ Clear tooltips + recommended move + how-to-win hints (strategy, not spoilers)
# ============================================================

st.set_page_config(page_title="MirrorWorld (Advanced)", layout="wide")

# ----------------------------
# Helpers
# ----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def fmt_m(x):
    return f"${x:.0f}M"

def risk_label(p):
    if p >= 70: return "Critical"
    if p >= 50: return "Elevated"
    if p >= 30: return "Moderate"
    return "Low"

def pressure_label(p):
    if p >= 80: return "Very High"
    if p >= 60: return "High"
    if p >= 40: return "Moderate"
    if p >= 20: return "Low"
    return "Very Low"

def safe_name(name: str) -> str:
    n = (name or "").strip()
    return n if n else "CEO"

def event_domain(event_id: str) -> str:
    if event_id.startswith("advice_"):
        return "🧠 GenAI"
    if event_id.startswith("credit_"):
        return "⚖️ Fairness"
    if event_id.startswith("policy_"):
        return "🏛️ Regulatory"
    if event_id.startswith("fraud_"):
        return "🕵️ Fraud"
    if event_id.startswith("data_"):
        return "🔐 Privacy"
    if event_id.startswith("ops_"):
        return "🛠️ Resilience"
    return "🧩 Event"

def stage_from_id(event_id: str) -> int:
    return 2 if "stage2" in event_id else 1

def family_from_id(event_id: str) -> str:
    return event_id.split("_stage2")[0] if "_stage2" in event_id else event_id

# ----------------------------
# RNG persistence
# ----------------------------
def get_rng(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state["rng_state"]
    return rng

def save_rng(state, rng):
    state["rng_state"] = rng.bit_generator.state

# ============================================================
# Lever Descriptions
# ============================================================
LEVER_HELP = {
    "growth": "How hard you push scaling this quarter. Higher growth boosts valuation but increases risk + regulatory attention.",
    "gov": "Oversight investment: audits, monitoring, model cards, documentation, controls, and risk governance.",
    "counterfactual": "YES/NO safety check. YES tests 'what if this applicant were different?' to detect bias & brittle rules. NO ships faster but increases blind spots.",
    "expansion": "Where you expand. Narrow = safer. Wide = faster, but more complexity and higher surprise risk.",
    "product": "Priority product: Credit (high scrutiny), Fraud (high ROI), Advisory (GenAI excitement + hallucination/compliance risk).",
    "model": "How you build: Open (fast/flexible), Hybrid (balanced), Closed (controlled/slower).",
    "data_policy": "How aggressively you collect/use data. Minimal reduces privacy risk. Aggressive can boost growth but increases scrutiny.",
    "pr": "Your communications posture. Transparent builds trust and reduces backlash; Defensive can amplify scrutiny after shocks.",
    "copilot": "How much GenAI automation runs inside workflows. Safe = guardrails + approvals. Aggressive = speed-first, higher surprise risk.",
    "leniency": "How forgiving the world is (Advanced). Higher leniency reduces regulatory pressure, lowers risk growth, and increases recovery after shocks."
}

# ============================================================
# Decision Trees (6 trees total, Stage 1 -> Stage 2)
# ============================================================
EVENTS: Dict[str, Dict[str, Any]] = {}

def register_event(e: Dict[str, Any]):
    EVENTS[e["id"]] = e

# ----------------------------
# Tree 1: GenAI advisory hallucination
# ----------------------------
register_event({
    "id": "advice_hallucination",
    "title": "GenAI Advisory Hallucination (Stage 1)",
    "setup": "Your advisory AI confidently recommends an ineligible product. A screenshot trends. Mirror AI reposts it: “This is why AI can’t be trusted in finance.”",
    "choices": [
        {"label": "Pause advisory, correct publicly, open an incident review",
         "effects": {"trust": +2, "governance": +3, "valuation_m": -8, "hidden_risk": -4, "reg_pressure": -1},
         "next_event": "advice_hallucination_stage2_a"},
        {"label": "Patch guardrails fast and keep it live",
         "effects": {"valuation_m": +5, "trust": -1, "hidden_risk": +4, "governance": +1},
         "next_event": "advice_hallucination_stage2_b"},
        {"label": "Call it “education only” and deny it is advice",
         "effects": {"trust": -3, "reg_pressure": +4, "hidden_risk": +6, "violations": +1},
         "next_event": "advice_hallucination_stage2_c"},
    ]
})
register_event({
    "id": "advice_hallucination_stage2_a",
    "title": "GenAI Advisory Hallucination (Stage 2)",
    "setup": "Root cause: retrieval pulled an outdated policy doc. Fix requires knowledge governance and monitoring.",
    "choices": [
        {"label": "Approved sources + version control + weekly audits",
         "effects": {"governance": +4, "hidden_risk": -6, "trust": +1, "valuation_m": -5}},
        {"label": "Confidence scoring + refusal when uncertain",
         "effects": {"trust": +1.5, "hidden_risk": -4, "valuation_m": -3}},
        {"label": "Quiet patch and move on",
         "effects": {"hidden_risk": +3, "trust": -1, "reg_pressure": +2}},
    ]
})
register_event({
    "id": "advice_hallucination_stage2_b",
    "title": "GenAI Advisory Hallucination (Stage 2)",
    "setup": "A regulator asks: can users distinguish model output from human advice? Mirror AI sells “HITL-certified advisory.”",
    "choices": [
        {"label": "Human-in-the-loop for high-impact recommendations",
         "effects": {"governance": +3, "trust": +1.5, "valuation_m": -6, "reg_pressure": -2}},
        {"label": "Opt-in consent + stronger disclosures",
         "effects": {"trust": +0.8, "governance": +2, "reg_pressure": -1}},
        {"label": "Compete on speed: keep as-is",
         "effects": {"valuation_m": +7, "trust": -2.5, "hidden_risk": +5, "comp_strength": +3}},
    ]
})
register_event({
    "id": "advice_hallucination_stage2_c",
    "title": "GenAI Advisory Hallucination (Stage 2)",
    "setup": "The defense backfires. Press requests incident metrics and asks about your GenAI governance.",
    "choices": [
        {"label": "Publish transparency report + corrective plan",
         "effects": {"trust": +1, "governance": +2, "valuation_m": -8, "reg_pressure": -1}},
        {"label": "Limit to beta users and go quiet",
         "effects": {"valuation_m": -2, "trust": -2, "reg_pressure": +2}},
        {"label": "Ship new features to drown the story",
         "effects": {"valuation_m": +9, "trust": -2.5, "hidden_risk": +4}},
    ]
})

# ----------------------------
# Tree 2: Fair lending / credit
# ----------------------------
register_event({
    "id": "credit_fairness_shock",
    "title": "Fair Lending Shock (Stage 1)",
    "setup": "Your audit flags approval-rate disparity for a protected class. Investors ask if you’re exposed. Mirror AI launches “bias-safe underwriting.”",
    "choices": [
        {"label": "Freeze the segment + run fairness/counterfactual tests",
         "effects": {"governance": +3, "trust": +1.5, "valuation_m": -10, "hidden_risk": -6},
         "next_event": "credit_fairness_shock_stage2_a"},
        {"label": "Patch thresholds to hit parity this quarter",
         "effects": {"valuation_m": +6, "hidden_risk": +6, "trust": -1.5},
         "next_event": "credit_fairness_shock_stage2_b"},
        {"label": "Wait until complaints arrive",
         "effects": {"trust": -2.5, "reg_pressure": +4, "hidden_risk": +8},
         "next_event": "credit_fairness_shock_stage2_c"},
    ]
})
register_event({
    "id": "credit_fairness_shock_stage2_a",
    "title": "Fair Lending Shock (Stage 2)",
    "setup": "Tests reveal a proxy feature drives disparity. Fixing it reduces speed and accuracy short-term.",
    "choices": [
        {"label": "Remove proxy + add adverse-action explainability overlays",
         "effects": {"governance": +4, "trust": +2, "valuation_m": -9, "hidden_risk": -7}},
        {"label": "Cap proxy influence + monitor tightly",
         "effects": {"valuation_m": +3, "hidden_risk": +3, "reg_pressure": +2}},
        {"label": "Switch to interpretable scorecard model",
         "effects": {"governance": +3, "trust": +1, "valuation_m": -12, "hidden_risk": -4}},
    ]
})
register_event({
    "id": "credit_fairness_shock_stage2_b",
    "title": "Fair Lending Shock (Stage 2)",
    "setup": "Your parity patch works, then an advocacy group requests subgroup metrics and transparency.",
    "choices": [
        {"label": "Publish subgroup metrics + methodology summary",
         "effects": {"trust": +1.5, "governance": +2, "reg_pressure": -2, "valuation_m": -3}},
        {"label": "Refuse disclosure citing IP protection",
         "effects": {"trust": -2, "reg_pressure": +4, "comp_strength": +2}},
        {"label": "Commission an independent fairness assessment",
         "effects": {"governance": +3, "valuation_m": -6, "reg_pressure": -1}},
    ]
})
register_event({
    "id": "credit_fairness_shock_stage2_c",
    "title": "Fair Lending Shock (Stage 2)",
    "setup": "Regulators request data lineage, monitoring logs, and explainability documentation. Deadline is tight.",
    "choices": [
        {"label": "Full cooperation + remediation plan + governance overhaul",
         "effects": {"governance": +4, "trust": +1, "reg_pressure": -4, "valuation_m": -7}},
        {"label": "Minimal response and delay details",
         "effects": {"reg_pressure": +3, "trust": -1}},
        {"label": "Miss the deadline",
         "effects": {"reg_pressure": +5, "trust": -2.5, "violations": +1}},
    ]
})

# ----------------------------
# Tree 3: Regulatory whiplash
# ----------------------------
register_event({
    "id": "policy_whiplash",
    "title": "Regulatory Whiplash (Stage 1)",
    "setup": "New guidance redefines what qualifies as “explainable.” Your disclosures may now be insufficient.",
    "choices": [
        {"label": "Upgrade compliance: model cards + logs + audit trails",
         "effects": {"governance": +4, "reg_pressure": -3, "valuation_m": -7, "hidden_risk": -3},
         "next_event": "policy_whiplash_stage2_a"},
        {"label": "Wait and watch enforcement signals",
         "effects": {"valuation_m": +4, "hidden_risk": +5, "reg_pressure": +2},
         "next_event": "policy_whiplash_stage2_b"},
        {"label": "Lobby hard and keep scaling",
         "effects": {"valuation_m": +7, "trust": -1.5, "reg_pressure": +4, "hidden_risk": +4},
         "next_event": "policy_whiplash_stage2_c"},
    ]
})
register_event({
    "id": "policy_whiplash_stage2_a",
    "title": "Regulatory Whiplash (Stage 2)",
    "setup": "Your governance becomes a competitive asset, but slows launches. Mirror AI tries to beat you on speed.",
    "choices": [
        {"label": "Hold discipline: governance as brand strategy",
         "effects": {"trust": +2, "governance": +2, "valuation_m": -3, "comp_strength": +2}},
        {"label": "Automate compliance (policy-as-code)",
         "effects": {"governance": +2, "valuation_m": +3, "hidden_risk": -2}},
        {"label": "Cut corners to match competitor velocity",
         "effects": {"valuation_m": +7, "trust": -2, "hidden_risk": +5}},
    ]
})
register_event({
    "id": "policy_whiplash_stage2_b",
    "title": "Regulatory Whiplash (Stage 2)",
    "setup": "Enforcement ramps quickly. An inquiry requests audit logs and explainability documentation.",
    "choices": [
        {"label": "Rapid compliance sprint + third-party audit",
         "effects": {"governance": +3, "reg_pressure": -2, "valuation_m": -6}},
        {"label": "Partial logs now, full package later",
         "effects": {"reg_pressure": +3, "trust": -1, "hidden_risk": +3}},
        {"label": "Ignore inquiry and focus on growth",
         "effects": {"reg_pressure": +5, "trust": -2, "violations": +1}},
    ]
})
register_event({
    "id": "policy_whiplash_stage2_c",
    "title": "Regulatory Whiplash (Stage 2)",
    "setup": "Lobbying leaks. Headlines say you’re “fighting transparency.” Mirror AI positions itself as “compliance-first.”",
    "choices": [
        {"label": "Publish transparency commitments and roadmap",
         "effects": {"trust": +1.5, "governance": +2, "valuation_m": -5}},
        {"label": "Double down: speed at all costs",
         "effects": {"valuation_m": +9, "trust": -3, "hidden_risk": +6, "reg_pressure": +2}},
        {"label": "Quietly build compliance while staying silent",
         "effects": {"governance": +2, "trust": -1, "reg_pressure": +1}},
    ]
})

# ----------------------------
# Tree 4: Fraud surge (modern market risk)
# ----------------------------
register_event({
    "id": "fraud_surge",
    "title": "Synthetic Identity Fraud Surge (Stage 1)",
    "setup": "A wave of synthetic identities hits the ecosystem. Losses climb. Mirror AI claims it can stop them with a new model.",
    "choices": [
        {"label": "Tighten controls + step-up verification",
         "effects": {"governance": +2, "trust": +1, "valuation_m": -4, "hidden_risk": -4},
         "next_event": "fraud_surge_stage2_a"},
        {"label": "Ship an aggressive fraud model fast",
         "effects": {"valuation_m": +7, "hidden_risk": +5, "trust": -1},
         "next_event": "fraud_surge_stage2_b"},
        {"label": "Absorb losses short-term and keep growth",
         "effects": {"valuation_m": +5, "hidden_risk": +6, "reg_pressure": +2},
         "next_event": "fraud_surge_stage2_c"},
    ]
})
register_event({
    "id": "fraud_surge_stage2_a",
    "title": "Synthetic Identity Fraud Surge (Stage 2)",
    "setup": "Customer friction rises. Growth slows. You need a smart mitigation that doesn’t destroy UX.",
    "choices": [
        {"label": "Risk-based step-up (only for suspicious cases)",
         "effects": {"valuation_m": +4, "hidden_risk": -3, "trust": +0.8}},
        {"label": "Partnership: external verification vendor + audits",
         "effects": {"governance": +3, "valuation_m": -3, "hidden_risk": -4}},
        {"label": "Keep strict verification for everyone",
         "effects": {"trust": -0.8, "valuation_m": -2, "hidden_risk": -5}},
    ]
})
register_event({
    "id": "fraud_surge_stage2_b",
    "title": "Synthetic Identity Fraud Surge (Stage 2)",
    "setup": "False positives spike. Real customers get blocked. Social media turns on you.",
    "choices": [
        {"label": "Add human review for edge cases + publish metrics",
         "effects": {"governance": +2, "trust": +1.5, "valuation_m": -4, "hidden_risk": -2}},
        {"label": "Lower thresholds to reduce false positives",
         "effects": {"valuation_m": +2, "hidden_risk": +3, "trust": +0.2}},
        {"label": "Stay the course and blame “bad actors”",
         "effects": {"trust": -2, "reg_pressure": +2, "hidden_risk": +2}},
    ]
})
register_event({
    "id": "fraud_surge_stage2_c",
    "title": "Synthetic Identity Fraud Surge (Stage 2)",
    "setup": "Losses trigger a board meeting. They demand a plan in one quarter.",
    "choices": [
        {"label": "Pivot to fraud focus for 1–2 quarters",
         "effects": {"valuation_m": +4, "hidden_risk": -3, "governance": +1}},
        {"label": "Raise prices/fees to cover losses",
         "effects": {"valuation_m": +3, "trust": -1.5}},
        {"label": "Do nothing and hope it passes",
         "effects": {"hidden_risk": +5, "reg_pressure": +2, "violations": +1}},
    ]
})

# ----------------------------
# Tree 5: Data privacy incident
# ----------------------------
register_event({
    "id": "data_privacy_breach",
    "title": "Third-Party Data Exposure (Stage 1)",
    "setup": "A vendor misconfiguration exposes limited customer metadata. It’s not catastrophic, but regulators and press notice.",
    "choices": [
        {"label": "Disclose quickly + rotate keys + commission an audit",
         "effects": {"trust": +1.5, "governance": +3, "valuation_m": -4, "reg_pressure": -1},
         "next_event": "data_privacy_breach_stage2_a"},
        {"label": "Fix quietly and monitor",
         "effects": {"valuation_m": +2, "trust": -1, "reg_pressure": +2},
         "next_event": "data_privacy_breach_stage2_b"},
        {"label": "Blame the vendor publicly",
         "effects": {"trust": -1.5, "reg_pressure": +3, "valuation_m": +1},
         "next_event": "data_privacy_breach_stage2_c"},
    ]
})
register_event({
    "id": "data_privacy_breach_stage2_a",
    "title": "Third-Party Data Exposure (Stage 2)",
    "setup": "Your transparency calms regulators. But customers want guarantees going forward.",
    "choices": [
        {"label": "Adopt 'privacy by design' + data minimization",
         "effects": {"trust": +1.2, "reg_pressure": -2, "hidden_risk": -2, "valuation_m": -2}},
        {"label": "Vendor governance playbook + quarterly reviews",
         "effects": {"governance": +3, "hidden_risk": -2, "valuation_m": -1}},
        {"label": "Offer customer credits and move on",
         "effects": {"trust": +0.5, "valuation_m": -3}},
    ]
})
register_event({
    "id": "data_privacy_breach_stage2_b",
    "title": "Third-Party Data Exposure (Stage 2)",
    "setup": "A journalist uncovers the incident. Now it looks like you tried to hide it.",
    "choices": [
        {"label": "Own it + publish a corrective timeline",
         "effects": {"trust": +0.8, "governance": +2, "reg_pressure": -1, "valuation_m": -3}},
        {"label": "Refuse to comment",
         "effects": {"trust": -2, "reg_pressure": +3}},
        {"label": "Release a vague statement",
         "effects": {"trust": -1, "reg_pressure": +2}},
    ]
})
register_event({
    "id": "data_privacy_breach_stage2_c",
    "title": "Third-Party Data Exposure (Stage 2)",
    "setup": "Vendor threatens litigation over your public blame. Your legal and PR costs rise.",
    "choices": [
        {"label": "Settle quietly + strengthen vendor controls",
         "effects": {"valuation_m": -3, "governance": +2, "hidden_risk": -1}},
        {"label": "Fight publicly",
         "effects": {"valuation_m": -2, "trust": -1.5, "reg_pressure": +2}},
        {"label": "Apologize and take shared responsibility",
         "effects": {"trust": +0.8, "valuation_m": -2, "reg_pressure": -1}},
    ]
})

# ----------------------------
# Tree 6: Operational resilience outage (FinTech reality)
# ----------------------------
register_event({
    "id": "ops_outage",
    "title": "Critical Outage During Peak Volume (Stage 1)",
    "setup": "Your scoring API degrades during a peak volume event. Partners complain. Mirror AI offers a “reliable alternative.”",
    "choices": [
        {"label": "Freeze new features + fix reliability (SRE sprint)",
         "effects": {"governance": +2, "trust": +1.2, "valuation_m": -3, "hidden_risk": -3},
         "next_event": "ops_outage_stage2_a"},
        {"label": "Scale infra quickly without deep fixes",
         "effects": {"valuation_m": +3, "hidden_risk": +4},
         "next_event": "ops_outage_stage2_b"},
        {"label": "Blame traffic and push partners to “wait it out”",
         "effects": {"trust": -2, "reg_pressure": +1, "valuation_m": +1},
         "next_event": "ops_outage_stage2_c"},
    ]
})
register_event({
    "id": "ops_outage_stage2_a",
    "title": "Critical Outage (Stage 2)",
    "setup": "Partners are calmer, but want an SLA and proof you can handle the next spike.",
    "choices": [
        {"label": "Add observability + chaos testing + incident runbooks",
         "effects": {"governance": +3, "hidden_risk": -3, "trust": +0.8, "valuation_m": -2}},
        {"label": "Offer SLA credits to protect relationships",
         "effects": {"trust": +0.6, "valuation_m": -3}},
        {"label": "Do the minimum and move on",
         "effects": {"hidden_risk": +2, "trust": -0.8}},
    ]
})
register_event({
    "id": "ops_outage_stage2_b",
    "title": "Critical Outage (Stage 2)",
    "setup": "You scaled, but the root cause returns. Now it looks like technical debt. Mirror AI pitches your partners.",
    "choices": [
        {"label": "Refactor core pipeline + reliability roadmap",
         "effects": {"valuation_m": -4, "hidden_risk": -4, "trust": +0.6}},
        {"label": "Hire an SRE lead and keep shipping",
         "effects": {"governance": +2, "valuation_m": -1, "hidden_risk": -2}},
        {"label": "Pretend it’s solved",
         "effects": {"trust": -1.5, "hidden_risk": +3, "comp_strength": +3}},
    ]
})
register_event({
    "id": "ops_outage_stage2_c",
    "title": "Critical Outage (Stage 2)",
    "setup": "Partners threaten churn. You must choose: rebuild trust or chase new logos.",
    "choices": [
        {"label": "Executive apology + reliability commitments",
         "effects": {"trust": +1.2, "valuation_m": -2, "governance": +1}},
        {"label": "Replace partners with new ones",
         "effects": {"valuation_m": +4, "trust": -1, "hidden_risk": +2}},
        {"label": "Offer pricing discounts to keep partners",
         "effects": {"valuation_m": +2, "trust": +0.2}},
    ]
})

STAGE1_IDS = [eid for eid in EVENTS.keys() if "stage2" not in eid]

# ============================================================
# Recommended Move + Hints
# ============================================================
def recommend_move(state: Dict[str, Any]) -> Dict[str, Any]:
    trust = state["trust"]
    reg = state["reg_pressure"]
    risk = state["hidden_risk"]
    comp = state["comp_strength"]
    val = state["valuation_m"]

    if (risk >= 55) or (reg >= 60) or (trust <= 45) or (state["violations"] >= 1):
        posture = "Safe"
    elif (val < 250 and state["quarter"] <= 4) and (trust >= 55) and (reg < 55) and (risk < 50):
        posture = "Bold"
    else:
        posture = "Balanced"

    if posture == "Safe":
        rec = {
            "Growth aggressiveness": "35–55",
            "Governance allocation": "70–90",
            "Counterfactual testing": "YES",
            "Expansion scope": "Narrow or Balanced",
            "PR posture": "Transparent",
            "Data policy": "Minimal or Balanced",
            "AI Copilot Mode": "Safe",
        }
        why = ("You’re in a high-scrutiny zone. The fastest path back to stability is to "
               "**buy down risk**: governance + counterfactuals + transparency.")
        tradeoff = "Tradeoff: slower growth this quarter, but sharply reduces shutdown probability."
    elif posture == "Bold":
        rec = {
            "Growth aggressiveness": "70–85",
            "Governance allocation": "55–70",
            "Counterfactual testing": "YES",
            "Expansion scope": "Balanced or Wide",
            "PR posture": "Transparent or Quiet",
            "Data policy": "Balanced",
            "AI Copilot Mode": "Safe (Aggressive only if trust/reg are very healthy)",
        }
        why = ("You have runway. Mirror AI is learning fast, so the board wants controlled scale. "
               "Push growth **without turning off safety checks**.")
        tradeoff = "Tradeoff: more complexity invites competitor attacks and surprise events."
    else:
        rec = {
            "Growth aggressiveness": "55–70",
            "Governance allocation": "55–75",
            "Counterfactual testing": "YES",
            "Expansion scope": "Balanced",
            "PR posture": "Transparent",
            "Data policy": "Balanced",
            "AI Copilot Mode": "Safe",
        }
        why = ("You’re in the middle game. Balanced growth with strong governance "
               "keeps you resilient to shocks while still compounding valuation.")
        tradeoff = "Tradeoff: fewer spikes, but dramatically fewer collapses."

    note_bits = []
    if comp >= 55:
        note_bits.append("Mirror AI is strong: it can copy features, but trust/governance are harder to copy.")
    if reg >= 60:
        note_bits.append("Reg pressure is high: documentation, logs, and explainability matter more than speed.")
    if risk >= 55:
        note_bits.append("Hidden risk is high: avoid wide expansion and Aggressive copilot.")
    if trust <= 45:
        note_bits.append("Trust is fragile: Transparent PR has the highest ROI right now.")
    if val < 150 and state["quarter"] >= 4:
        note_bits.append("Valuation is lagging: consider Fraud focus or controlled expansion with counterfactuals ON.")

    return {
        "posture": posture,
        "recommended_settings": rec,
        "rationale": why,
        "tradeoff": tradeoff,
        "context_notes": note_bits
    }

def win_hints(state: Dict[str, Any], sandbox: bool) -> List[str]:
    hints = []
    if sandbox:
        hints.append("🏁 Sandbox win: reach **$1B valuation** (no quarter limit). Keep Trust high and avoid 3 violations.")
    else:
        hints.append("🏁 Standard win: reach **$1B valuation** by Quarter 8, keep **Trust ≥ 70**, avoid 3 violations.")

    if state["trust"] < 55:
        hints.append("🤝 Trust is low: Transparent PR + Counterfactual YES + avoid Aggressive Copilot.")
    if state["reg_pressure"] >= 55:
        hints.append("🏛️ Reg pressure is high: increase Governance and keep documentation tight.")
    if state["hidden_risk"] >= 55:
        hints.append("⚠️ Hidden risk is high: slow growth temporarily and keep counterfactuals ON.")
    if state["comp_strength"] >= 55:
        hints.append("🪞 Mirror AI is strong: win on trust/safety (they copy features; they struggle to copy legitimacy).")

    hints.append("🎯 Simple rule: never chase growth with Counterfactual = NO for multiple quarters.")
    return hints

# ============================================================
# Story Engine
# ============================================================
def narrate_opening(name: str, seed_m: float, product: str) -> str:
    n = safe_name(name)
    return (
        f"🎬 **Opening Scene**\n\n"
        f"{n}, you step into MirrorWorld as the new FinTech executive. Your board wires **${seed_m:.0f}M** and says one line:\n"
        f"“Build something revolutionary. Don’t get us shut down.”\n\n"
        f"You launch **{product}** first. Across the street, your rival is already watching: **Mirror AI**."
    )

def narrate_quarter(name: str, state: Dict[str, Any], d: Dict[str, Any]) -> str:
    n = safe_name(name)
    tone = []
    tone.append("you slam the accelerator" if d["growth"] >= 75 else ("you play it cautious" if d["growth"] <= 35 else "you scale with intent"))
    tone.append("and build serious guardrails" if d["gov"] >= 70 else ("and keep governance thin" if d["gov"] <= 35 else "with balanced oversight"))

    cf_line = "Counterfactual testing is **ON** — you stress-test fairness and edge cases." if d["counterfactual"] else \
              "Counterfactual testing is **OFF** — you ship faster, but blind spots can grow."
    pr_line = f"Your public posture is **{d['pr']}**."
    cop_line = f"AI Copilot is **{d['copilot']}** inside workflows."

    risk = state["hidden_risk"]
    reg = state["reg_pressure"]
    trust = state["trust"]
    vibe = "The market feels calm." if (risk < 35 and reg < 40 and trust > 55) else \
           "The air is tense. One bad headline could cascade." if (risk > 55 or reg > 60 or trust < 45) else \
           "You can feel the balance shifting quarter by quarter."

    return (
        f"📆 **Quarter {state['quarter']} Story Beat**\n\n"
        f"{n}, {', '.join(tone)}. You prioritize **{d['product']}**.\n"
        f"{cf_line} {pr_line} {cop_line}\n\n"
        f"{vibe}"
    )

def narrate_event_intro(name: str, ev: Dict[str, Any]) -> str:
    n = safe_name(name)
    return (
        f"🧩 **Choose-Your-Own-Adventure Moment** ({event_domain(ev['id'])})\n\n"
        f"{n}, a new situation hits your desk:\n\n"
        f"**{ev['title']}**\n{ev['setup']}"
    )

def narrate_event_choice(name: str, choice_label: str, stage: int) -> str:
    n = safe_name(name)
    twist = "Now the twist lands." if stage == 1 else "The dust settles—for now."
    return f"🎭 {n}, you choose: **{choice_label}**. {twist}"

def narrate_end(name: str, state: Dict[str, Any]) -> str:
    n = safe_name(name)
    return f"🏁 **Victory Scene**\n\n{n}, you reached **{fmt_m(state['valuation_m'])}** and proved you can scale AI under disruption."

# ============================================================
# Core Mechanics (with Leniency)
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
    state["crisis_prob"] = clamp((0.62 * prior + 0.38 * signal) * 100.0, 1.0, 95.0)

def value_creation(growth, expansion, product, model):
    base = 18.0 + (growth / 100) * 55.0
    base *= 1.18 if expansion == "Wide" else (1.05 if expansion == "Balanced" else 0.92)
    base *= 1.10 if product == "Fraud" else (1.03 if product == "Credit" else 1.00)
    base *= 1.08 if model == "Open" else (1.03 if model == "Hybrid" else 0.98)
    return base

def apply_quarter(state, d: Dict[str, Any], leniency: int, sandbox: bool):
    """
    leniency: 0..100. Higher leniency = easier world.
    Effects:
      - boosts valuation creation slightly
      - reduces risk accumulation
      - reduces reg pressure growth
      - gives small trust recovery
    """
    rng = get_rng(state)

    growth = d["growth"]
    gov = d["gov"]
    counterfactual = d["counterfactual"]
    expansion = d["expansion"]
    product = d["product"]
    model = d["model"]
    data_policy = d["data_policy"]
    pr = d["pr"]
    copilot = d["copilot"]

    # leniency multipliers
    L = clamp(leniency / 100.0, 0.0, 1.0)
    val_boost = 1.00 + 0.10 * L         # up to +10% value creation
    risk_dampen = 1.00 - 0.20 * L       # up to -20% risk accumulation
    reg_dampen = 1.00 - 0.25 * L        # up to -25% reg growth
    trust_relief = 0.30 * L             # up to +0.30 trust per quarter baseline

    # governance dynamics
    state["governance"] = clamp(state["governance"] + (gov/100)*10.0 - (growth/100)*3.0, 0, 100)

    # Counterfactual YES/NO
    if counterfactual:
        state["hidden_risk"] = clamp(state["hidden_risk"] - (6.0 + 2.0*L), 0, 100)
        state["trust"] = clamp(state["trust"] + (1.5 + 0.5*L), 0, 100)
        test_cost = 0.07
    else:
        state["hidden_risk"] = clamp(state["hidden_risk"] + (6.5 - 1.5*L), 0, 100)
        state["trust"] = clamp(state["trust"] - (2.0 - 0.5*L), 0, 100)
        test_cost = 0.00

    # Data policy
    if data_policy == "Minimal":
        state["trust"] = clamp(state["trust"] + (1.5 + 0.3*L), 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] - (2.0 + 0.5*L), 0, 100)
        data_boost, risk_boost = 0.95, 0.85
    elif data_policy == "Balanced":
        data_boost, risk_boost = 1.00, 1.00
    else:
        state["trust"] = clamp(state["trust"] - (2.0 - 0.4*L), 0, 100)
        state["reg_pressure"] = clamp(state["reg_pressure"] + (4.0 - 1.0*L), 0, 100)
        data_boost, risk_boost = 1.08, 1.20

    # PR posture
    if pr == "Transparent":
        state["trust"] = clamp(state["trust"] + (1.2 + 0.3*L), 0, 100)
        pr_risk = 0.90
    elif pr == "Defensive":
        state["trust"] = clamp(state["trust"] - (0.8 - 0.2*L), 0, 100)
        pr_risk = 1.05
    else:
        pr_risk = 1.00

    # Product risk
    if product == "Credit":
        state["reg_pressure"] = clamp(state["reg_pressure"] + (2.5 - 0.6*L), 0, 100)
        product_risk = 1.10
    elif product == "Fraud":
        product_risk = 1.00
    else:
        state["trust"] = clamp(state["trust"] - (0.8 - 0.2*L), 0, 100)
        product_risk = 1.05

    # Copilot mode
    if copilot == "Off":
        cop_value, cop_risk, cop_trust = 1.00, 1.00, 0.0
    elif copilot == "Safe":
        cop_value, cop_risk, cop_trust = 1.04, 0.92, +0.8
        state["hidden_risk"] = clamp(state["hidden_risk"] - (2.0 + 0.5*L), 0, 100)
    else:
        cop_value, cop_risk, cop_trust = 1.10, 1.20, -0.6
        state["reg_pressure"] = clamp(state["reg_pressure"] + (2.0 - 0.6*L), 0, 100)

    # baseline trust relief in lenient world
    state["trust"] = clamp(state["trust"] + cop_trust + trust_relief, 0, 100)

    # valuation creation
    trust_factor = 0.85 + (state["trust"]/100)*0.30
    gov_factor = 0.85 + (state["governance"]/100)*0.25

    created = value_creation(growth, expansion, product, model)
    created *= trust_factor * gov_factor * data_boost * cop_value * val_boost
    created *= (1.0 - test_cost)
    created += rng.normal(0, 3.0)

    # Sandbox slight boost so it feels rewarding
    if sandbox:
        created *= 1.05

    state["valuation_m"] = max(0.0, state["valuation_m"] + created)

    # hidden risk accumulation (dampened by leniency)
    risk_add = (growth/100)*6.0
    risk_add += max(0.0, (70.0 - state["governance"])) / 100.0 * 4.0
    risk_add *= risk_boost * product_risk * pr_risk * cop_risk * risk_dampen
    state["hidden_risk"] = clamp(state["hidden_risk"] + risk_add - (gov/100)*3.0, 0, 100)

    # regulatory pressure responds to imbalance (dampened)
    reg_add = max(0.0, (growth - state["governance"])) / 100.0 * 9.0
    reg_add *= reg_dampen
    state["reg_pressure"] = clamp(state["reg_pressure"] + reg_add, 0, 100)

    save_rng(state, rng)

def competitor_step(state, d: Dict[str, Any], leniency: int, sandbox: bool) -> List[str]:
    rng = get_rng(state)
    L = clamp(leniency / 100.0, 0.0, 1.0)

    growth = d["growth"]
    counterfactual = d["counterfactual"]
    pr = d["pr"]
    gov = d["gov"]
    data_policy = d["data_policy"]
    copilot = d["copilot"]

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
    opening += 2.3 if pr == "Defensive" else 0.7
    opening += 1.8 if data_policy == "Aggressive" else 0.6
    opening += 1.0 if copilot == "Aggressive" else 0.0

    # Leniency reduces competitor compounding a bit (easier)
    comp_dampen = 1.00 - 0.15 * L
    if sandbox:
        comp_dampen *= 0.95

    state["comp_strength"] = clamp(state["comp_strength"] + (learn_rate + opening + rng.normal(0, 1.0)) * comp_dampen, 0, 100)

    headlines = []
    s = state["comp_strength"]

    # Leniency reduces negative impacts
    harm = 1.00 - 0.20 * L
    if sandbox:
        harm *= 0.90

    if state["comp_strategy"] == "Price War":
        hit = (0.03 + 0.0006 * s) * state["valuation_m"] * harm
        state["valuation_m"] = max(0.0, state["valuation_m"] - hit)
        headlines.append("⚔️ Mirror AI starts a price war. Your margins tighten.")
    elif state["comp_strategy"] == "Safety-First":
        trust_hit = (1.0 + (max(0.0, 60 - state["governance"]) / 40.0) * 2.0) * harm
        state["trust"] = clamp(state["trust"] - trust_hit, 0, 100)
        headlines.append("🛡️ Mirror AI runs a safety-first campaign. Your trust score gets compared publicly.")
    elif state["comp_strategy"] == "Copycat":
        steal = (0.02 + 0.0004 * s) * state["valuation_m"] * harm
        state["valuation_m"] = max(0.0, state["valuation_m"] - steal)
        headlines.append("🪞 Mirror AI clones your features. Differentiation shrinks.")
    else:
        add = (4.0 + 0.08 * s) * harm
        state["reg_pressure"] = clamp(state["reg_pressure"] + add, 0, 100)
        if state["hidden_risk"] >= 50 or (not counterfactual):
            if rng.random() < (0.35 * harm):
                state["violations"] += 1
                state["trust"] = clamp(state["trust"] - (4.0 * harm), 0, 100)
                headlines.append("📣 Mirror AI pushes a complaint. You take an incident hit (+1 violation).")
        headlines.append("🧾 Mirror AI tries a regulatory trap. Scrutiny rises.")

    save_rng(state, rng)
    return headlines

# ============================================================
# Event Chain Functions
# ============================================================
def apply_effects(state, effects: Dict[str, float], leniency: int, sandbox: bool):
    """
    In Advanced Lax worlds:
      - negative effects are softened
      - positive effects are slightly amplified
    """
    L = clamp(leniency / 100.0, 0.0, 1.0)
    soften = 1.00 - 0.25 * L
    boost = 1.00 + 0.10 * L
    if sandbox:
        soften *= 0.90
        boost *= 1.05

    for k, v in effects.items():
        v = float(v)
        adj = v * (boost if v >= 0 else soften)

        if k == "valuation_m":
            state["valuation_m"] = max(0.0, state["valuation_m"] + adj)
        elif k == "violations":
            # violations softened slightly in lenient mode
            addv = int(round(adj))
            if addv > 0 and L >= 0.6:
                addv = max(0, addv - 1)  # sometimes “warning instead of violation”
            state["violations"] += addv
        elif k == "comp_strength":
            state["comp_strength"] = clamp(state["comp_strength"] + adj, 0, 100)
        else:
            state[k] = clamp(state.get(k, 0.0) + adj, 0.0, 100.0)

def start_chain(state, event_id: str):
    state["chain"] = {
        "family": family_from_id(event_id),
        "stage": stage_from_id(event_id),
        "current_event_id": event_id,
    }

def advance_chain(state, next_event_id: Optional[str]):
    if next_event_id:
        state["chain"]["current_event_id"] = next_event_id
        state["chain"]["stage"] = stage_from_id(next_event_id)
    else:
        state["chain"] = None

def current_event(state) -> Optional[Dict[str, Any]]:
    if not state["chain"]:
        return None
    return EVENTS.get(state["chain"]["current_event_id"])

def maybe_trigger_stage1_event(state, mode: str, base_odds: float, d: Dict[str, Any], sandbox: bool) -> Optional[str]:
    """
    Demo: always trigger
    Normal: probabilistic
    In sandbox, frequency is slightly higher (more fun).
    """
    if state["chain"] is not None:
        return None

    rng = get_rng(state)

    if mode == "Demo":
        eid = STAGE1_IDS[int(rng.integers(0, len(STAGE1_IDS)))]
        save_rng(state, rng)
        return eid

    p = base_odds
    p += 0.10 if state["hidden_risk"] >= 40 else 0.0
    p += 0.08 if state["reg_pressure"] >= 50 else 0.0
    p += 0.08 if state["comp_strength"] >= 45 else 0.0
    if d["copilot"] == "Aggressive":
        p += 0.05
    if sandbox:
        p += 0.05

    p = clamp(p, 0.05, 0.95)

    if rng.random() <= p:
        eid = STAGE1_IDS[int(rng.integers(0, len(STAGE1_IDS)))]
        save_rng(state, rng)
        return eid

    save_rng(state, rng)
    return None

# ============================================================
# End + Score
# ============================================================
def end_check(state, sandbox: bool):
    # Sandbox keeps failure states, but still ends if shutdown occurs (3 violations) unless player continues toggled later.
    if state["violations"] >= 3:
        state["game_over"] = True
        state["end_reason"] = "Regulatory shutdown: too many incidents/violations."
    elif state["trust"] < 20 and state["reg_pressure"] > 80:
        state["game_over"] = True
        state["end_reason"] = "Trust collapse under extreme regulatory pressure."
    elif state["crisis_prob"] > 80:
        state["game_over"] = True
        state["end_reason"] = "Systemic crisis: risk exceeded survivable threshold."
    else:
        state["game_over"] = False
        state["end_reason"] = ""

def score(state):
    valuation_score = min(100.0, (state["valuation_m"] / 1000.0) * 100.0)
    penalty = state["reg_pressure"] * 0.25 + state["crisis_prob"] * 0.55 + state["violations"] * 10.0
    total = valuation_score * 0.50 + state["trust"] * 0.20 + state["governance"] * 0.20 - penalty * 0.10
    return clamp(total, 0.0, 100.0)

def win_condition(state) -> bool:
    return state["valuation_m"] >= 1000.0

# ============================================================
# State Init
# ============================================================
def init_state(seed=7):
    rng = np.random.default_rng(seed)
    return {
        "phase": "setup",
        "player_name": "",
        "quarter": 1,
        "valuation_m": 0.0,
        "trust": 55.0,
        "governance": 50.0,
        "reg_pressure": 20.0,
        "crisis_prob": 8.0,
        "hidden_risk": 10.0,
        "violations": 0,

        "comp_strength": 10.0,
        "comp_strategy": "Observing",

        "product_line": None,
        "seed_m": 0.0,

        "story": [],
        "headlines": [],
        "history": [],

        "chain": None,

        "game_over": False,
        "end_reason": "",

        "rng_state": rng.bit_generator.state,
    }

# ============================================================
# Sidebar (Advanced + Standard)
# ============================================================
with st.sidebar:
    st.header("🧪 MirrorWorld Settings")

    mode = st.radio(
        "Play Mode",
        ["Standard (8 quarters, harder)", "Advanced Sandbox (lax + keep playing until $1B)"],
        index=1
    )
    sandbox = mode.startswith("Advanced")

    st.markdown("### Difficulty Lever (Advanced)")
    leniency = st.slider("Market Leniency (Laxness)", 0, 100, 70 if sandbox else 30, 5, help=LEVER_HELP["leniency"])
    st.caption("Higher leniency = easier recovery + lower penalties (Advanced).")

    st.markdown("### Decision Tree Settings")
    event_mode = st.radio("Event Mode", ["Normal", "Demo"], index=0)
    base_odds = st.slider("Event Frequency", 0.05, 0.90, 0.45 if sandbox else 0.35, 0.05)

    st.markdown("### How it’s graded (rubric alignment)")
    st.write("- Disruption & competition: adaptive Mirror AI")
    st.write("- GenAI governance: advisory boundaries, hallucination risk, HITL")
    st.write("- Ethics & fairness: counterfactual testing, explainability, adverse action")
    st.write("- Risk/compliance: logs, audits, transparency, regulatory whiplash")
    st.write("- Operational resilience: outages, SLAs, incident response")

# ============================================================
# App Start
# ============================================================
st.title("🪞 MirrorWorld — Advanced (Sandbox + Lax World)")
st.caption("More events, easier world, and you can keep playing until you hit $1B (Advanced Sandbox).")

if "state" not in st.session_state:
    st.session_state.state = init_state(seed=7)

state = st.session_state.state

left, right = st.columns([1.25, 0.75], gap="large")

# ============================================================
# LEFT: Gameplay + Story
# ============================================================
with left:
    limit_txt = "∞" if sandbox else "8"
    st.subheader(f"Quarter {state['quarter']} / {limit_txt}")

    # ---------- Setup ----------
    if state["phase"] == "setup":
        st.markdown("### 1) Create your CEO avatar")
        player_name = st.text_input("Your name (personalizes the story)", value=state["player_name"], placeholder="e.g., Shreeja")
        seed = st.select_slider("2) Choose seed funding", options=[5, 10, 20, 35, 50], value=20)
        product = st.radio("3) Choose your first product line", ["Credit", "Fraud", "Advisory"], horizontal=True)

        st.info("Seed converts your idea into operating momentum. Higher seed raises visibility and scrutiny.")

        if st.button("✅ Start My Story", use_container_width=True):
            state["player_name"] = (player_name or "").strip()
            state["seed_m"] = float(seed)
            state["product_line"] = product
            state["valuation_m"] = float(seed) * 6.0
            state["reg_pressure"] = clamp(state["reg_pressure"] + float(seed) / 5.0, 0, 100)
            state["phase"] = "play"

            state["story"] = [narrate_opening(state["player_name"], state["seed_m"], state["product_line"])]
            state["headlines"] = [f"Seed closed: ${seed}M. Product launched: {product}. Mirror AI begins shadowing you."]

            st.session_state.state = state
            st.rerun()

    else:
        # ---------- If already won in sandbox ----------
        if sandbox and win_condition(state):
            st.success(narrate_end(state["player_name"], state))
            st.info("You can keep playing for fun (try pushing risk and seeing if you can still survive), or hit Reset to start a new run.")

        # ---------- Event chain active ----------
        ev = current_event(state)
        if ev and not state["game_over"]:
            st.warning(f"{event_domain(ev['id'])} — {ev['title']}")
            st.markdown(narrate_event_intro(state["player_name"], ev))

            st.markdown("#### 🗺️ Decision Tree Map")
            st.write(f"**Chain:** `{state['chain']['family']}`")
            st.write(f"**Stage:** {state['chain']['stage']} of 2")
            st.info("Stage 2 is the twist. Resolve it to continue.")

            st.markdown("#### Choose your move")
            for i, ch in enumerate(ev["choices"], start=1):
                with st.container(border=True):
                    st.write(f"**Option {i}: {ch['label']}**")

                    eff = ch["effects"]
                    impact_bits = []
                    for key in ["valuation_m", "trust", "governance", "reg_pressure", "hidden_risk", "violations"]:
                        if key in eff:
                            sign = "+" if eff[key] >= 0 else ""
                            label = "Valuation" if key == "valuation_m" else key.replace("_", " ").title()
                            impact_bits.append(f"{label} {sign}{eff[key]}")
                    if impact_bits:
                        st.caption("Impact preview (pre-leniency): " + " | ".join(impact_bits))

                    if st.button(f"Select Option {i}", key=f"event_{ev['id']}_{i}", use_container_width=True):
                        state["story"].append(narrate_event_choice(state["player_name"], ch["label"], state["chain"]["stage"]))
                        apply_effects(state, ch["effects"], leniency=leniency, sandbox=sandbox)

                        next_id = ch.get("next_event")
                        advance_chain(state, next_id)

                        bayesian_crisis_update(state)
                        end_check(state, sandbox=sandbox)

                        # advance quarter when chain finishes
                        if (not state["game_over"]) and (state["chain"] is None):
                            state["quarter"] += 1

                        st.session_state.state = state
                        st.rerun()

        else:
            # ---------- Recommended move + hints ----------
            st.markdown("### 🧠 Recommended Move + Hints")
            rec = recommend_move(state)
            with st.container(border=True):
                st.markdown(f"#### 🧭 Recommended Move: **{rec['posture']} posture**")
                st.write(rec["rationale"])
                st.caption(rec["tradeoff"])
                st.markdown("**Suggested settings (not mandatory):**")
                for k, v in rec["recommended_settings"].items():
                    st.write(f"- **{k}:** {v}")
                if rec["context_notes"]:
                    st.markdown("**Why this fits your current situation:**")
                    for n in rec["context_notes"]:
                        st.write(f"- {n}")

            with st.expander("💡 Hints: How to win (strategy, not spoilers)"):
                for h in win_hints(state, sandbox=sandbox):
                    st.write(f"- {h}")

            st.markdown("---")
            st.markdown("### 1) Choose your quarter strategy (simple + explained)")

            with st.expander("📘 What do these controls mean? (quick explainer)"):
                for key in ["growth","gov","counterfactual","expansion","product","model","data_policy","pr","copilot","leniency"]:
                    st.write(f"**{key.replace('_',' ').title()}:** {LEVER_HELP[key]}")

            growth = st.slider("Growth aggressiveness", 0, 100, 65, help=LEVER_HELP["growth"])
            gov = st.slider("Governance allocation", 0, 100, 55, help=LEVER_HELP["gov"])
            counterfactual_yes = st.toggle("Counterfactual testing (Yes/No)", value=True, help=LEVER_HELP["counterfactual"])
            expansion = st.radio("Expansion scope", ["Narrow", "Balanced", "Wide"], index=1, horizontal=True, help=LEVER_HELP["expansion"])

            st.markdown("### 2) AI & Strategy Levers")
            c1, c2 = st.columns(2)
            with c1:
                product = st.selectbox(
                    "Product focus",
                    ["Credit", "Fraud", "Advisory"],
                    index=["Credit", "Fraud", "Advisory"].index(state["product_line"]),
                    help=LEVER_HELP["product"]
                )
                model_choice = st.selectbox("Model strategy", ["Open", "Hybrid", "Closed"], index=1, help=LEVER_HELP["model"])
            with c2:
                data_policy = st.selectbox("Data policy", ["Minimal", "Balanced", "Aggressive"], index=1, help=LEVER_HELP["data_policy"])
                pr = st.selectbox("PR posture", ["Transparent", "Quiet", "Defensive"], index=1, help=LEVER_HELP["pr"])

            st.markdown("### 3) GenAI inside the business (how bold are you?)")
            copilot = st.radio("AI Copilot Mode", ["Off", "Safe", "Aggressive"], index=1, horizontal=True, help=LEVER_HELP["copilot"])

            d = {
                "growth": growth,
                "gov": gov,
                "counterfactual": counterfactual_yes,
                "expansion": expansion,
                "product": product,
                "model": model_choice,
                "data_policy": data_policy,
                "pr": pr,
                "copilot": copilot,
            }

            st.markdown("---")
            run_col, reset_col = st.columns(2)

            with run_col:
                if st.button("▶️ Run Quarter", use_container_width=True, disabled=state["game_over"]):
                    state["story"].append(narrate_quarter(state["player_name"], state, d))

                    apply_quarter(state, d, leniency=leniency, sandbox=sandbox)
                    comp_news = competitor_step(state, d, leniency=leniency, sandbox=sandbox)
                    bayesian_crisis_update(state)

                    triggered = maybe_trigger_stage1_event(state, event_mode, base_odds, d, sandbox=sandbox)
                    if triggered:
                        start_chain(state, triggered)

                    end_check(state, sandbox=sandbox)

                    # Standard mode ends at 8 quarters (even if not won)
                    if (not sandbox) and (state["chain"] is None) and (not state["game_over"]) and (state["quarter"] >= 8):
                        state["game_over"] = True
                        state["end_reason"] = "Standard mode ended at Quarter 8."
                    elif (not state["game_over"]) and (state["chain"] is None):
                        state["quarter"] += 1

                    state["history"].append({
                        "Quarter": state["quarter"],
                        "Mode": "Advanced Sandbox" if sandbox else "Standard",
                        "Leniency": leniency,
                        "Growth": growth,
                        "Gov": gov,
                        "Counterfactual": "Yes" if counterfactual_yes else "No",
                        "Expansion": expansion,
                        "Product": product,
                        "Model": model_choice,
                        "DataPolicy": data_policy,
                        "PR": pr,
                        "CopilotMode": copilot,
                        "CompetitorStrategy": state["comp_strategy"],
                        "CompetitorStrength": round(state["comp_strength"], 1),
                        "Valuation($M)": round(state["valuation_m"], 1),
                        "Trust": round(state["trust"], 1),
                        "Governance": round(state["governance"], 1),
                        "RegPressure": round(state["reg_pressure"], 1),
                        "CrisisProb(%)": round(state["crisis_prob"], 1),
                        "HiddenRisk": round(state["hidden_risk"], 1),
                        "Violations": state["violations"],
                        "EventTriggered": triggered if triggered else "None",
                    })

                    base = ["Quarter executed. The market reacts."] + comp_news
                    if triggered:
                        base = ["🧩 A choose-your-own-adventure event triggers. Decide to continue."] + base
                    state["headlines"] = base

                    st.session_state.state = state
                    st.rerun()

            with reset_col:
                if st.button("🔄 Reset", use_container_width=True):
                    st.session_state.state = init_state(seed=7)
                    st.rerun()

            st.markdown("### Headlines")
            for h in state["headlines"]:
                st.write(f"- {h}")

            st.markdown("### Run Log")
            if state["history"]:
                st.dataframe(pd.DataFrame(state["history"]), use_container_width=True, hide_index=True)
            else:
                st.info("Run Quarter 1 to generate the log.")

    # ---------- Story Transcript ----------
    st.markdown("---")
    st.markdown("## 📖 Story Transcript (Narration)")
    if state["story"]:
        recent = state["story"][-6:]
        for beat in recent:
            st.markdown(beat)
            st.markdown("")
        with st.expander("See full story transcript"):
            for beat in state["story"]:
                st.markdown(beat)
                st.markdown("")
    else:
        st.info("Your story will appear here after you start the game.")

# ============================================================
# RIGHT: Metrics + Tree Map
# ============================================================
with right:
    st.subheader("Real-Time Metrics")

    a, b, c = st.columns(3)
    a.metric("Valuation", fmt_m(state["valuation_m"]))
    b.metric("Trust", f"{state['trust']:.0f}/100")
    c.metric("Governance", f"{state['governance']:.0f}/100")

    dcol, ecol = st.columns(2)
    dcol.metric("Crisis Probability", f"{state['crisis_prob']:.0f}% ({risk_label(state['crisis_prob'])})")
    ecol.metric("Reg Pressure", f"{pressure_label(state['reg_pressure'])}")

    st.markdown("---")
    st.metric("Mirror AI Strength", f"{state['comp_strength']:.0f}/100")
    st.write(f"**Mirror AI Strategy:** {state['comp_strategy']}")
    st.write(f"**Hidden Risk:** {state['hidden_risk']:.0f}/100")
    st.write(f"**Violations:** {state['violations']} (shutdown at 3)")
    st.write(f"**Score:** {score(state):.1f}/100")

    st.markdown("---")
    st.subheader("🗺️ Decision Tree Map")
    if state["chain"] is None:
        st.write("No active decision tree right now.")
        st.caption("Want guaranteed decision trees for your demo? Switch Event Mode to **Demo**.")
    else:
        ev = current_event(state)
        st.write(f"**Active chain:** `{state['chain']['family']}`")
        st.write(f"**Stage:** {state['chain']['stage']} of 2")
        if ev:
            st.write(f"**Current node:** {ev['title']}")

    st.markdown("---")
    if state["game_over"]:
        st.error(f"Game Over: {state['end_reason']}")
        st.write("**Final Score:**", f"{score(state):.1f}/100")
    else:
        if sandbox:
            st.info("Advanced Sandbox: keep playing until you hit **$1B valuation**.")
        else:
            st.info("Standard: 8 quarters. Try to hit $1B by Quarter 8 while staying trustworthy.")

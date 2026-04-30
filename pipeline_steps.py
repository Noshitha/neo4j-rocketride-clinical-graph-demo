import json
import os
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI
from graph_service import get_graph_service_from_env

PROMPTS_DIR = Path("prompts")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def call_gmi(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    api_key = os.getenv("GMI_API_KEY")
    base_url = os.getenv("GMI_BASE_URL", "https://api.gmi-serving.com/v1")
    model = os.getenv("GMI_MODEL")
    timeout_seconds = float(os.getenv("GMI_TIMEOUT_SECONDS", "60"))

    if not api_key:
        raise ValueError("Set GMI_API_KEY in your environment.")
    if not model:
        raise ValueError("Set GMI_MODEL in your environment.")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        max_retries=0,
    )

    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = completion.choices[0].message.content
    if content is None:
        raise ValueError("GMI returned empty content.")

    return parse_json_response(content)


def build_guideline_user_prompt(payload: Dict[str, Any]) -> str:
    return (
        "Review this patient from a guideline-alignment perspective.\n\n"
        f"Patient payload:\n{json.dumps(payload, indent=2)}\n\n"
        "Task:\n"
        "Assess whether the patient's current management appears aligned with the "
        "recommendation-oriented CKD/diabetes context. Highlight likely management "
        "review opportunities and decide whether monitoring, review, escalation, or "
        "urgent review is most appropriate.\n\n"
        "Return JSON with exactly these keys:\n"
        "agent_name\nsummary\nrecommendation\nconfidence\nkey_reasons\n"
        "guideline_alignment\nrisk_flags\nrecommended_next_steps\n\n"
        "guideline_alignment must be an object with exactly:\n"
        '{ "appears_aligned": boolean, "gaps_or_tensions": [string, ...] }'
    )


def build_kidney_risk_user_prompt(payload: Dict[str, Any]) -> str:
    return (
        "Review this patient from a kidney-risk and safety perspective.\n\n"
        f"Patient payload:\n{json.dumps(payload, indent=2)}\n\n"
        "Task:\n"
        "Assess kidney progression risk, medication safety constraints, and whether "
        "the patient appears higher risk than a simple guideline-only interpretation "
        "would suggest. Emphasize hyperkalemia, advanced CKD, contraindications, "
        "trends, and need for closer review.\n\n"
        "Return JSON with exactly these keys:\n"
        "agent_name\nsummary\nrecommendation\nconfidence\nkey_reasons\n"
        "guideline_alignment\nrisk_flags\nrecommended_next_steps\n\n"
        "guideline_alignment must be an object with exactly:\n"
        '{ "appears_aligned": boolean, "gaps_or_tensions": [string, ...] }'
    )


def build_synthesizer_user_prompt(
    full_context: Dict[str, Any],
    guideline_output: Dict[str, Any],
    kidney_output: Dict[str, Any],
) -> str:
    return (
        f"Patient context:\n{json.dumps(full_context, indent=2)}\n\n"
        f"Guideline agent output:\n{json.dumps(guideline_output, indent=2)}\n\n"
        f"Kidney risk agent output:\n{json.dumps(kidney_output, indent=2)}\n\n"
        "Return JSON with exactly these keys:\n"
        "final_recommendation\nagreement_status\nsummary\nwhy\nkey_drivers\n"
        "recommended_next_steps\n\n"
        "agreement_status must be exactly one of:\n"
        "agree, partial_agreement, disagree"
    )


def fetch_context(patient_id: str) -> Dict[str, Any]:
    service = get_graph_service_from_env()
    try:
        return service.get_agent_payloads(patient_id)
    finally:
        service.close()


def run_guideline_agent(guideline_agent_payload: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_text(PROMPTS_DIR / "guideline_agent_system.txt")
    user_prompt = build_guideline_user_prompt(guideline_agent_payload)
    return call_gmi(system_prompt, user_prompt)


def run_kidney_risk_agent(kidney_risk_payload: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_text(PROMPTS_DIR / "kidney_risk_agent_system.txt")
    user_prompt = build_kidney_risk_user_prompt(kidney_risk_payload)
    return call_gmi(system_prompt, user_prompt)


def run_synthesizer(
    full_context: Dict[str, Any],
    guideline_output: Dict[str, Any],
    kidney_output: Dict[str, Any],
) -> Dict[str, Any]:
    system_prompt = load_text(PROMPTS_DIR / "synthesizer_system.txt")
    user_prompt = build_synthesizer_user_prompt(
        full_context,
        guideline_output,
        kidney_output,
    )
    return call_gmi(system_prompt, user_prompt)

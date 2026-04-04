import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from openai import OpenAI
import os
from openai import OpenAI
from graph_service import get_graph_service_from_env

PROMPTS_DIR = Path("prompts")

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
        "guideline_alignment\nrisk_flags\nrecommended_next_steps"
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
        "guideline_alignment\nrisk_flags\nrecommended_next_steps"
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
        "recommended_next_steps"
    )


def call_model(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("GMI_API_KEY")
    base_url = os.getenv("GMI_BASE_URL", "https://api.gmi-serving.com/v1")
    model = os.getenv("GMI_MODEL")

    if not api_key:
        raise ValueError("Set GMI_API_KEY in your environment.")
    if not model:
        raise ValueError("Set GMI_MODEL in your environment.")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
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

    return content


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return json.loads(cleaned)


def run_patient(patient_id: str) -> Dict[str, Any]:
    service = get_graph_service_from_env()
    try:
        payloads = service.get_agent_payloads(patient_id)
    finally:
        service.close()

    guideline_system = load_text(PROMPTS_DIR / "guideline_agent_system.txt")
    kidney_system = load_text(PROMPTS_DIR / "kidney_risk_agent_system.txt")
    synthesizer_system = load_text(PROMPTS_DIR / "synthesizer_system.txt")

    guideline_user = build_guideline_user_prompt(payloads["guideline_agent_payload"])
    kidney_user = build_kidney_risk_user_prompt(payloads["kidney_risk_agent_payload"])

    guideline_raw = call_model(guideline_system, guideline_user)
    guideline_output = parse_json_response(guideline_raw)

    kidney_raw = call_model(kidney_system, kidney_user)
    kidney_output = parse_json_response(kidney_raw)

    synthesizer_user = build_synthesizer_user_prompt(
        payloads["full_context"],
        guideline_output,
        kidney_output,
    )

    synthesizer_raw = call_model(synthesizer_system, synthesizer_user)
    synthesizer_output = parse_json_response(synthesizer_raw)

    return {
        "patient_id": patient_id,
        "guideline_agent_output": guideline_output,
        "kidney_risk_agent_output": kidney_output,
        "synthesizer_output": synthesizer_output,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise ValueError("Usage: python agent_run.py <PATIENT_ID>")

    patient_id = sys.argv[1]
    result = run_patient(patient_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
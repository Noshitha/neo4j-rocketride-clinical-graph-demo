import json
import sys
from typing import Any, Dict

from pipeline_steps import (
    fetch_context,
    run_guideline_agent,
    run_kidney_risk_agent,
    run_synthesizer,
)


def run_pipeline(patient_id: str) -> Dict[str, Any]:
    context_bundle = fetch_context(patient_id)

    guideline_output = run_guideline_agent(
        context_bundle["guideline_agent_payload"]
    )

    kidney_output = run_kidney_risk_agent(
        context_bundle["kidney_risk_agent_payload"]
    )

    synthesizer_output = run_synthesizer(
        context_bundle["full_context"],
        guideline_output,
        kidney_output,
    )

    return {
        "patient_id": patient_id,
        "full_context": context_bundle["full_context"],
        "guideline_agent_output": guideline_output,
        "kidney_risk_agent_output": kidney_output,
        "synthesizer_output": synthesizer_output,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise ValueError("Usage: python rocketride_entry.py <PATIENT_ID>")

    patient_id = sys.argv[1]
    result = run_pipeline(patient_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
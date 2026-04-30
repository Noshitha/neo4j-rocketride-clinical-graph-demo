import json
import sys
from typing import Any, Dict

from rocketride_entry import run_pipeline


def run_patient(patient_id: str) -> Dict[str, Any]:
    return run_pipeline(patient_id)


def main() -> None:
    if len(sys.argv) < 2:
        raise ValueError("Usage: python agent_run.py <PATIENT_ID>")

    patient_id = sys.argv[1]
    result = run_patient(patient_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

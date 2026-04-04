import json
import sys

from graph_service import get_graph_service_from_env


def main() -> None:
    if len(sys.argv) < 2:
        raise ValueError("Usage: python build_agent_payloads.py <PATIENT_ID>")

    patient_id = sys.argv[1]

    service = get_graph_service_from_env()
    try:
        payloads = service.get_agent_payloads(patient_id)
        print(json.dumps(payloads, indent=2))
    finally:
        service.close()


if __name__ == "__main__":
    main()
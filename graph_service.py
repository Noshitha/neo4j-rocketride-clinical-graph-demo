import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from queries import FULL_CONTEXT_QUERY


def _clean_list(values: Optional[List[Any]]) -> List[Any]:
    if not values:
        return []
    cleaned = []
    for v in values:
        if v is None:
            continue
        if isinstance(v, dict):
            if all(x is None for x in v.values()):
                continue
        cleaned.append(v)
    return cleaned


def _normalize_context(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patient_id": record.get("patient_id"),
        "demographics": {
            "age": record.get("age"),
            "sex": record.get("sex"),
        },
        "conditions": {
            "diabetes_type": record.get("diabetes_type"),
            "ckd_stage": record.get("ckd_stage"),
            "albuminuria_stage": record.get("albuminuria_stage"),
            "hypertension": record.get("hypertension"),
            "heart_failure": record.get("heart_failure"),
            "ascvd": record.get("ascvd"),
        },
        "labs": {
            "eGFR": record.get("eGFR"),
            "uACR_mg_g": record.get("uACR_mg_g"),
            "hbA1c_percent": record.get("hbA1c_percent"),
            "serum_creatinine_mg_dL": record.get("serum_creatinine_mg_dL"),
            "potassium_mEq_L": record.get("potassium_mEq_L"),
            "systolic_bp": record.get("systolic_bp"),
            "diastolic_bp": record.get("diastolic_bp"),
        },
        "medications": _clean_list(record.get("medications")),
        "risk_markers": _clean_list(record.get("risk_markers")),
        "contraindications": _clean_list(record.get("contraindications")),
        "follow_up": {
            "date": record.get("follow_up_date"),
            "summary": record.get("follow_up_summary"),
            "trend_flags": _clean_list(record.get("trend_flags")),
        },
        "candidate_recommendations": _clean_list(record.get("candidate_recommendations")),
    }


def build_guideline_agent_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent": "guideline_agent",
        "patient_id": context["patient_id"],
        "clinical_focus": "guideline_alignment_for_diabetes_and_ckd",
        "demographics": context["demographics"],
        "conditions": {
            "diabetes_type": context["conditions"]["diabetes_type"],
            "ckd_stage": context["conditions"]["ckd_stage"],
            "albuminuria_stage": context["conditions"]["albuminuria_stage"],
            "hypertension": context["conditions"]["hypertension"],
        },
        "labs": {
            "hbA1c_percent": context["labs"]["hbA1c_percent"],
            "systolic_bp": context["labs"]["systolic_bp"],
            "diastolic_bp": context["labs"]["diastolic_bp"],
            "eGFR": context["labs"]["eGFR"],
            "uACR_mg_g": context["labs"]["uACR_mg_g"],
        },
        "medications": context["medications"],
        "candidate_recommendations": context["candidate_recommendations"],
        "task": (
            "Assess whether the patient's current management appears aligned with the "
            "guideline-oriented CKD and diabetes recommendation set. Highlight likely "
            "management review opportunities and state whether monitoring, review, or "
            "escalation seems most appropriate."
        ),
    }


def build_kidney_risk_agent_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent": "kidney_risk_agent",
        "patient_id": context["patient_id"],
        "clinical_focus": "patient_specific_kidney_and_safety_risk_review",
        "demographics": context["demographics"],
        "conditions": context["conditions"],
        "labs": {
            "eGFR": context["labs"]["eGFR"],
            "uACR_mg_g": context["labs"]["uACR_mg_g"],
            "potassium_mEq_L": context["labs"]["potassium_mEq_L"],
            "serum_creatinine_mg_dL": context["labs"]["serum_creatinine_mg_dL"],
        },
        "risk_markers": context["risk_markers"],
        "contraindications": context["contraindications"],
        "follow_up": context["follow_up"],
        "medications": context["medications"],
        "candidate_recommendations": context["candidate_recommendations"],
        "task": (
            "Assess kidney progression risk, medication safety constraints, and whether "
            "the patient appears higher risk than a simple guideline-only interpretation "
            "would suggest. Emphasize hyperkalemia, advanced CKD, contraindications, "
            "trends, and need for closer review."
        ),
    }


class Neo4jGraphService:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self) -> None:
        self.driver.close()

    def get_full_context(self, patient_id: str) -> Dict[str, Any]:
        with self.driver.session() as session:
            result = session.run(FULL_CONTEXT_QUERY, patient_id=patient_id)
            record = result.single()

            if record is None:
                raise ValueError(f"No patient found for patient_id={patient_id}")

            return _normalize_context(dict(record))

    def get_agent_payloads(self, patient_id: str) -> Dict[str, Any]:
        context = self.get_full_context(patient_id)
        return {
            "full_context": context,
            "guideline_agent_payload": build_guideline_agent_payload(context),
            "kidney_risk_agent_payload": build_kidney_risk_agent_payload(context),
        }


def get_graph_service_from_env() -> Neo4jGraphService:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("Set NEO4J_PASSWORD in your environment before running.")

    return Neo4jGraphService(uri=uri, username=username, password=password)
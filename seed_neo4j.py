import json
import os
from neo4j import GraphDatabase

DEFAULT_CANDIDATE_RECOMMENDATIONS = [
    {
        "rec_id": "ckd_diabetes_bp_review",
        "title": "Review blood pressure control",
        "action": "review",
        "rationale": (
            "Diabetes with CKD and hypertension may require blood pressure "
            "optimization and monitoring."
        ),
    },
    {
        "rec_id": "ckd_diabetes_kidney_protection",
        "title": "Assess kidney-protective therapy",
        "action": "review",
        "rationale": (
            "Persistent albuminuria or elevated progression risk may warrant "
            "clinician review of kidney-protective therapy options."
        ),
    },
    {
        "rec_id": "ckd_safety_monitoring",
        "title": "Monitor kidney safety markers",
        "action": "monitor",
        "rationale": (
            "CKD medication decisions should account for eGFR, potassium, "
            "contraindications, intolerance history, and follow-up trends."
        ),
    },
]


def clear_demo_graph(tx):
    tx.run(
        """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN [
            "Patient",
            "ConditionProfile",
            "LabSnapshot",
            "Medication",
            "RiskMarker",
            "Contraindication",
            "FollowUpEvent",
            "TrendFlag",
            "Recommendation"
        ])
        DETACH DELETE n
        """
    )


def get_driver_from_env():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("Set NEO4J_PASSWORD in your environment before seeding.")

    return GraphDatabase.driver(uri, auth=(username, password))


def seed_patient(tx, patient):
    tx.run(
        """
        MERGE (p:Patient {patient_id: $patient_id})
        SET p.age = $age,
            p.sex = $sex
        """,
        patient_id=patient["patient_id"],
        age=patient["demographics"]["age"],
        sex=patient["demographics"]["sex"],
    )

    tx.run(
        """
        MATCH (p:Patient {patient_id: $patient_id})
        MERGE (c:ConditionProfile {patient_id: $patient_id})
        SET c.diabetes_type = $diabetes_type,
            c.ckd = $ckd,
            c.ckd_stage = $ckd_stage,
            c.albuminuria_stage = $albuminuria_stage,
            c.hypertension = $hypertension,
            c.heart_failure = $heart_failure,
            c.ascvd = $ascvd
        MERGE (p)-[:HAS_CONDITION_PROFILE]->(c)
        """,
        patient_id=patient["patient_id"],
        diabetes_type=patient["conditions"]["diabetes_type"],
        ckd=patient["conditions"]["ckd"],
        ckd_stage=patient["conditions"]["ckd_stage"],
        albuminuria_stage=patient["conditions"]["albuminuria_stage"],
        hypertension=patient["conditions"]["hypertension"],
        heart_failure=patient["conditions"]["heart_failure"],
        ascvd=patient["conditions"]["ascvd"],
    )

    labs = patient["labs"]
    tx.run(
        """
        MATCH (p:Patient {patient_id: $patient_id})
        MERGE (l:LabSnapshot {patient_id: $patient_id})
        SET l.eGFR = $eGFR,
            l.uACR_mg_g = $uACR_mg_g,
            l.hbA1c_percent = $hbA1c_percent,
            l.serum_creatinine_mg_dL = $serum_creatinine_mg_dL,
            l.potassium_mEq_L = $potassium_mEq_L,
            l.systolic_bp = $systolic_bp,
            l.diastolic_bp = $diastolic_bp
        MERGE (p)-[:HAS_LAB_SNAPSHOT]->(l)
        """,
        patient_id=patient["patient_id"],
        **labs
    )

    for med in patient.get("medications", []):
        tx.run(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MERGE (m:Medication {
                patient_id: $patient_id,
                name: $name,
                class: $med_class,
                dose: $dose,
                status: $status
            })
            MERGE (p)-[:TAKES]->(m)
            """,
            patient_id=patient["patient_id"],
            name=med["name"],
            med_class=med["class"],
            dose=med["dose"],
            status=med["status"],
        )

    for risk in patient.get("risk_markers", []):
        tx.run(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MERGE (r:RiskMarker {name: $risk})
            MERGE (p)-[:HAS_RISK_MARKER]->(r)
            """,
            patient_id=patient["patient_id"],
            risk=risk,
        )

    for ci in patient.get("contraindications_or_intolerances", []):
        tx.run(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MERGE (c:Contraindication {name: $ci})
            MERGE (p)-[:HAS_CONTRAINDICATION]->(c)
            """,
            patient_id=patient["patient_id"],
            ci=ci,
        )

    follow_up = patient["follow_up_event"]
    tx.run(
        """
        MATCH (p:Patient {patient_id: $patient_id})
        MERGE (f:FollowUpEvent {patient_id: $patient_id})
        SET f.event_date = $event_date,
            f.summary = $summary
        MERGE (p)-[:HAS_FOLLOW_UP]->(f)
        """,
        patient_id=patient["patient_id"],
        event_date=follow_up["event_date"],
        summary=follow_up["summary"],
    )

    for flag in follow_up.get("trend_flags", []):
        tx.run(
            """
            MATCH (f:FollowUpEvent {patient_id: $patient_id})
            MERGE (t:TrendFlag {name: $flag})
            MERGE (f)-[:HAS_TREND_FLAG]->(t)
            """,
            patient_id=patient["patient_id"],
            flag=flag,
        )

    recommendations = patient.get(
        "candidate_recommendations",
        DEFAULT_CANDIDATE_RECOMMENDATIONS,
    )
    for rec in recommendations:
        tx.run(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MERGE (r:Recommendation {rec_id: $rec_id})
            SET r.title = $title,
                r.action = $action,
                r.rationale = $rationale
            MERGE (p)-[:CANDIDATE_RECOMMENDATION]->(r)
            """,
            patient_id=patient["patient_id"],
            rec_id=rec["rec_id"],
            title=rec["title"],
            action=rec["action"],
            rationale=rec["rationale"],
        )


def main():
    with open("patient-records.json", "r", encoding="utf-8") as f:
        patients = json.load(f)

    driver = get_driver_from_env()
    with driver.session() as session:
        session.execute_write(clear_demo_graph)
        for patient in patients:
            session.execute_write(seed_patient, patient)

    driver.close()
    print("Seeding complete.")


if __name__ == "__main__":
    main()

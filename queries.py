FULL_CONTEXT_QUERY = """
MATCH (p:Patient {patient_id: $patient_id})
OPTIONAL MATCH (p)-[:HAS_CONDITION_PROFILE]->(c:ConditionProfile)
OPTIONAL MATCH (p)-[:HAS_LAB_SNAPSHOT]->(l:LabSnapshot)
OPTIONAL MATCH (p)-[:TAKES]->(m:Medication)
OPTIONAL MATCH (p)-[:HAS_RISK_MARKER]->(rm:RiskMarker)
OPTIONAL MATCH (p)-[:HAS_CONTRAINDICATION]->(ci:Contraindication)
OPTIONAL MATCH (p)-[:HAS_FOLLOW_UP]->(f:FollowUpEvent)
OPTIONAL MATCH (f)-[:HAS_TREND_FLAG]->(tf:TrendFlag)
OPTIONAL MATCH (p)-[:CANDIDATE_RECOMMENDATION]->(rec:Recommendation)
RETURN
  p.patient_id AS patient_id,
  p.age AS age,
  p.sex AS sex,
  c.diabetes_type AS diabetes_type,
  c.ckd_stage AS ckd_stage,
  c.albuminuria_stage AS albuminuria_stage,
  c.hypertension AS hypertension,
  c.heart_failure AS heart_failure,
  c.ascvd AS ascvd,
  l.eGFR AS eGFR,
  l.uACR_mg_g AS uACR_mg_g,
  l.hbA1c_percent AS hbA1c_percent,
  l.serum_creatinine_mg_dL AS serum_creatinine_mg_dL,
  l.potassium_mEq_L AS potassium_mEq_L,
  l.systolic_bp AS systolic_bp,
  l.diastolic_bp AS diastolic_bp,
  collect(DISTINCT {
    name: m.name,
    class: m.class,
    dose: m.dose,
    status: m.status
  }) AS medications,
  collect(DISTINCT rm.name) AS risk_markers,
  collect(DISTINCT ci.name) AS contraindications,
  f.event_date AS follow_up_date,
  f.summary AS follow_up_summary,
  collect(DISTINCT tf.name) AS trend_flags,
  collect(DISTINCT {
    rec_id: rec.rec_id,
    title: rec.title,
    action: rec.action,
    rationale: rec.rationale
  }) AS candidate_recommendations
"""
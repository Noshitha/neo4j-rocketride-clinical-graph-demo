# Neo4j RocketRide Clinical Graph Demo

This is a graph-native clinical reasoning prototype for synthetic diabetes and chronic kidney disease follow-up scenarios.

The demo stores patient context in Neo4j, retrieves a patient-specific graph bundle, sends that context through two specialist LLM reasoning roles, and synthesizes the outputs into one structured recommendation.

## What It Does

- Seeds synthetic CKD/diabetes patient records into Neo4j.
- Retrieves demographics, conditions, labs, medications, risk markers, contraindications, follow-up trends, and candidate recommendations.
- Builds two focused payloads:
  - `guideline_agent_payload`: guideline-alignment and management-gap review.
  - `kidney_risk_agent_payload`: kidney progression and medication-safety review.
- Calls an OpenAI-compatible model endpoint through GMI.
- Produces a final synthesized recommendation: `monitor`, `review`, `escalate`, or `urgent_review`.
- Includes a RocketRide `.pipe` orchestration that can run the same clinical reasoning workflow through a webhook-triggered agent pipeline.

## Files

- `patient-records.json`: synthetic patient fixture data.
- `seed_neo4j.py`: loads the fixture data into Neo4j.
- `queries.py`: Cypher query for reconstructing patient context.
- `graph_service.py`: Neo4j access and agent payload builders.
- `pipeline_steps.py`: prompt construction and model calls.
- `rocketride_entry.py`: local Python entry point for the full pipeline.
- `agent_run.py`: compatibility wrapper around `rocketride_entry.py`.
- `prompts/`: system prompts for the guideline, kidney-risk, and synthesizer roles.
- `schema/`: expected JSON output schemas.
- `rocket-ride.pipe`: RocketRide orchestration for webhook-to-agent clinical reasoning.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment from the example:

```bash
cp env.example env.sh
```

Edit `env.sh` with your local credentials, then load it:

```bash
source env.sh
```

Expected variables:

- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `GMI_API_KEY`
- `GMI_BASE_URL`
- `GMI_MODEL`

## Run Locally

Seed Neo4j:

```bash
python seed_neo4j.py
```

Inspect graph-derived payloads:

```bash
python build_agent_payload.py P001
```

Run the full Python pipeline:

```bash
python rocketride_entry.py P001
```

## RocketRide

`rocket-ride.pipe` defines a webhook-triggered RocketRide pipeline:

```text
webhook -> question -> RocketRide agent -> response
                 agent uses DeepSeek LLM + memory + Neo4j tool
```

Send a patient id such as `P001`, `P002`, `P003`, or `P004` to the webhook. The agent is instructed to retrieve the graph context, perform the guideline and kidney-risk reviews, then return the synthesized recommendation JSON.

RocketRide variables use the `ROCKETRIDE_` prefix:

- `ROCKETRIDE_NEO4J_URI`
- `ROCKETRIDE_NEO4J_USERNAME`
- `ROCKETRIDE_NEO4J_PASSWORD`
- `ROCKETRIDE_DEEPSEEK_KEY`

## Safety Note

This project uses synthetic data and prototype prompts. It is not medical advice and should not be used for patient care.

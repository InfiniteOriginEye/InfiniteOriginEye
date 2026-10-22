# 🇮🇳 Swarm Command & Control (SC&C)

> **Disaster Management Drone Swarm System** — an AI-powered, multi-service platform for India's emergency response infrastructure, integrating ERSS/112, IMD, CWC, INCOIS, and NDRF/SDRF with autonomous drone swarms for search, rescue, and relief operations.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CITIZEN CHANNELS                             │
│   112 / ERSS │ 181 │ 1070 │ 1091 │ RailMadad │ SACHET │ SMS │ IoT │
└──────────┬──────────────────────────────────────────────────────────┘
           │ Kafka: incidents.created
           ▼
┌──────────────────────┐     ┌──────────────────────┐
│  S1 — Incident Intake │────▶│  S9 — AI/ML Pipeline  │
│  & Multi-Channel Triage│◀────│  Triage · Detection   │
└──────────┬───────────┘     └───────────────────────┘
           │ Kafka: incidents.ai_triaged
           ▼
┌──────────────────────┐
│  S2 — Professional    │  Human-in-the-loop review
│  Review Dashboard     │  (SEOC operators)
└──────────┬───────────┘
           │ Kafka: incidents.approved
           ▼
┌──────────────────────┐     ┌──────────────────────┐
│  S3 — Swarm Command   │◀───▶│  S4 — Rescue Team     │
│  & Control (gRPC)     │     │  Coordination         │
└──────────┬───────────┘     └──────────┬───────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐     ┌──────────────────────┐
│  Drone Swarms         │     │  NDRF / SDRF / Health │
│  (Ant·Bee·Medical)    │     │  Field Teams           │
└──────────────────────┘     └──────────────────────┘
           ▲
┌──────────┴───────────┐     ┌──────────────────────┐
│  S5 — Early Warning   │     │  S6 — ERSS/112        │
│  IMD·INCOIS·CWC·GFS   │     │  Connector (PSAP)     │
└──────────────────────┘     └──────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│  S7 — Data Handover   │     │  S8 — Platform Infra  │
│  & Reporting          │     │  K8s · Terraform      │
└──────────────────────┘     └──────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│  S10 — Citizen App    │     │  Telemetry Ingest     │
│  React Native         │     │  Go + MQTT + Kafka    │
└──────────────────────┘     └──────────────────────┘
```

---

## 📦 Services (S1–S10)

| Service | Owner | Tech Stack | Port | Description |
|---------|-------|------------|------|-------------|
| **S1** Incident Intake & Triage | SDMA/SEOC | Python FastAPI | :8001 | Multi-channel incident ingestion from 112, 181, 1070, 1091, RailMadad, SACHET, IoT, Social Media |
| **S2** Professional Review Dashboard | SDMA/SEOC | FastAPI + Next.js 14 + CesiumJS | :8002 | Human-in-the-loop incident review with 3D map & Deck.gl |
| **S3** Swarm Command & Control | C-DAC/NDRF | Go + gRPC + Next.js 14 + CesiumJS | :8003 | Real-time drone swarm deployment with adaptive formations |
| **S4** Rescue Team Coordination | NDRF/SDRF/Health | FastAPI + React Native | :8004 | Ground team dispatch, tracking & patient handover |
| **S5** Early-Warning Ingest | SDMA/SEOC | Python FastAPI | :8005 | IMD CAP/XML, INCOIS RSS, CWC flood, GFS weather feeds |
| **S6** ERSS/112 Connector | ERSS/PSAP/C-DAC | Python FastAPI | :8006 | State PSAP integration for emergency call routing |
| **S7** Data Handover & Reporting | NDMA/SDMA | Python FastAPI | :8007 | NDMA-format reports, inter-agency data handover |
| **S8** Platform Infrastructure | NIC/C-DAC | K8s + Terraform + Ansible | — | CI/CD, monitoring, secrets, infrastructure |
| **S9** AI/ML Pipeline | C-DAC | PyTorch → ONNX → Triton | :8000 | Triage, damage assessment, YOLO detection, Whisper STT |
| **S10** Citizen App | NDMA/SDMA | React Native + MapLibre GL | — | Mobile citizen reporting & alert reception |

---

## 🛰️ Drone Swarm Architecture

```
                ┌─────────────────────┐
                │    Mother Drone      │
                │  (Orchestrator)      │
                └──────┬──────────────┘
                       │ MQTT
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │  Legion A  │ │  Legion B  │ │  Legion M  │
   │  (Ant)     │ │  (Bee)     │ │  (Medical) │
   │  Search    │ │  Survey    │ │  AirDrops  │
   │  Pattern  │ │  Mapping   │ │  MedEvac   │
   └────────────┘ └────────────┘ └────────────┘
    25 drones      25 drones      25 drones
```

**Formation Patterns**: Grid · Line · Circle · Cone · Adaptive (AI-driven)

**Communication**: MAVLink ↔ MQTT 5.0 (EMQX) ↔ Kafka ↔ gRPC

---

## 📡 Indian Government Integrations

| System | Type | Direction | Data Format |
|--------|------|-----------|-------------|
| **ERSS/112** | Emergency calls | Inbound | JSON REST |
| **IMD** | Weather alerts | Inbound | CAP v1.2 XML |
| **INCOIS** | Ocean/tsunami alerts | Inbound | RSS/XML |
| **CWC** | Flood warnings | Inbound | PDF/Excel |
| **SACHET** | NDMA alerts | Inbound | JSON REST |
| **RailMadad** | Railway incidents | Inbound | JSON REST |
| **NDRF/SDRF** | Rescue ops | Bidirectional | gRPC + Kafka |
| **NDMA** | Reports/handover | Outbound | PDF/Excel |

**Pilot States**: Uttarakhand · Kerala · Tamil Nadu · Assam · Himachal Pradesh

---

## 🔄 Event Streaming (Kafka — 17 Topics)

**Incident Lifecycle**: `incidents.created` → `incidents.ai_triaged` → `incidents.approved` → `incidents.status_changed`

**Swarm Ops**: `swarm.deploy` · `swarm.recall` · `swarm.telemetry` · `swarm.status` · `swarm.digital_twin`

**Rescue Ops**: `teams.dispatched` · `teams.location_update` · `teams.patient_handover`

**Early Warning**: `alerts.early_warning` · `alerts.threshold_breach`

**Other**: `erss.incident_sync` · `ml.inference_request` · `ml.inference_result` · `audit.events` · `reports.generated`

---

## 🧠 AI/ML Pipeline (S9)

| Model | Purpose | Framework |
|-------|---------|-----------|
| YOLOv8/YOLO11 | Damage detection, survivor spotting | Ultralytics → ONNX → Triton |
| Whisper | Emergency call transcription | OpenAI Whisper → Triton |
| XGBoost/LightGBM | Incident triage priority scoring | sklearn → ONNX → Triton |
| SAM | Segmentation for damage assessment | PyTorch → ONNX → Triton |
| Custom NLP | Incident classification from free-text | Transformers → Triton |

**SLA Targets**:
- AI Triage: **≤ 30s**
- Human Review: **≤ 120s**
- Swarm Dispatch: **≤ 300s**
- Auto-approve on timeout

---

## 🔧 Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11 + FastAPI, Go 1.22 + gRPC |
| **Event Streaming** | Apache Kafka 7.6, MQTT 5.0 (EMQX), WebSocket |
| **Data** | PostgreSQL 16 + PostGIS 3.4 + TimescaleDB, Redis 7, MinIO, pgvector/Qdrant |
| **AI/ML** | PyTorch → ONNX → Triton, YOLO, Whisper, XGBoost, MLflow, CVAT |
| **Frontend** | Next.js 14 + CesiumJS + Deck.gl + MUI (S2), Next.js 14 + gRPC-Web (S3) |
| **Mobile** | React Native + MapLibre GL (S4, S10) |
| **Drone/Edge** | ArduPilot/PX4, ROS 2, MAVLink, Jetson Orin, TensorRT, WebRTC |
| **Infra** | Kubernetes, Docker, Terraform, Ansible, Prometheus + Grafana + Loki, Vault |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+, Go 1.22+, Node 20+
- Docker & Docker Compose
- Kafka 7.6+, EMQX 5.7+

### 1. Infrastructure

```bash
make dev-infra        # Start PostGIS, Kafka, Redis, MQTT, MinIO
```

### 2. Backend Services

```bash
make dev-backend      # Start S1-S7 FastAPI services (ports 8001-8007)
make dev-s3           # Start S3 Go gRPC server
```

### 3. Frontend

```bash
make dev-frontend     # Start S2 dashboard + S3 tactical view
```

### 4. Everything at once

```bash
make dev              # Full dev environment
```

### 5. Simulate

```bash
make simulate         # Drone telemetry + ERSS inbound simulators
make seed             # Seed reference data & test incidents
```

---

## 📁 Project Structure

```
swarm-command-control/
├── services/              # Core microservices (S1–S7)
│   ├── s1-incident-intake/   # Multi-channel ingestion + AI triage
│   ├── s2-review-dashboard/  # SEOC operator review
│   ├── s3-swarm-command/     # Go gRPC swarm control
│   ├── s4-rescue-coord/      # Ground team coordination
│   ├── s5-early-warning/     # IMD/INCOIS/CWC/GFS feeds
│   ├── s6-erss-connector/    # ERSS 112 PSAP integration
│   └── s7-data-handover/     # NDMA reporting
├── integration/           # External system connectors
│   ├── imd/               # India Meteorological Dept (CAP/XML)
│   ├── incois/            # Ocean information (RSS)
│   ├── cwc/               # Central Water Commission (PDF/Excel)
│   ├── erss/              # ERSS/112 PSAP
│   ├── sachet/            # NDMA SACHET alerts
│   └── railmadad/         # Indian Railways incidents
├── frontend/              # Next.js + React Native apps
│   ├── s2-dashboard/      # SEOC Review Dashboard
│   ├── s3-tactical/       # Tactical Swarm Command
│   ├── s4-field-app/      # Field team app
│   └── s10-citizen-app/   # Citizen reporting app
├── shared/                # Cross-service shared code
│   ├── constants/         # Shared constants
│   ├── types/             # Pydantic models & type definitions
│   ├── schemas/           # JSON/Avro schemas
│   ├── proto/             # Protobuf definitions
│   ├── utils/             # Kafka client, helpers
│   └── ui-kit/            # Shared UI components
├── simulators/            # Simulators for testing
│   ├── erss-inbound/      # ERSS 112 call simulator
│   ├── ndrf-teams/        # NDRF team movement
│   ├── sdrf-teams/        # SDRF team movement
│   ├── citizen-reports/   # Citizen report simulator
│   └── weather-feeds/     # Weather data simulator
├── drone-sim/             # Drone telemetry simulation
├── ai/                    # AI/ML training & serving
├── ai-ml/                 # AI/ML pipelines & models
├── telemetry/             # Go telemetry ingestion (MQTT→Kafka)
├── infra/                 # Infrastructure-as-code
│   ├── k8s/               # Kubernetes manifests
│   ├── terraform/         # Terraform configs
│   ├── ansible/           # Ansible playbooks
│   ├── monitoring/        # Prometheus + Grafana
│   ├── kafka-topics.yaml  # 17 Kafka topic definitions
│   └── vault/             # HashiCorp Vault
├── scripts/               # Utility scripts
├── docs/                  # Architecture, runbooks, onboarding
├── data/                  # Migrations & seed data
├── dashboards/            # npm workspace dashboards
├── docker-compose.yml     # Dev infrastructure
├── scc.config.toml        # Master system configuration
└── Makefile               # Development commands
```

---

## 🧪 Testing & Development

```bash
make test           # Run all tests (pytest + go test + npm test)
make lint           # Lint (ruff + golangci-lint)
make proto-gen      # Generate Go/Python/TS from .proto files
make migrate        # Run Alembic migrations for all services
make db-reset       # Destroy & recreate database
make seed           # Seed reference data & test incidents
```

---

## 📊 Monitoring

| Tool | URL | Purpose |
|------|-----|---------|
| Grafana | :3000 | Dashboards & alerting |
| Prometheus | :9090 | Metrics collection |
| EMQX Dashboard | :18083 | MQTT broker monitoring |
| MinIO Console | :9001 | Object storage management |
| Kafka UI | :9094 | Kafka topic inspection |

---

## 🤝 Agency Ownership

| Component | Primary Agency | Backup Agency |
|-----------|---------------|--------------|
| S1 Incident Intake | SDMA/SEOC | NDMA |
| S2 Review Dashboard | SDMA/SEOC | C-DAC |
| S3 Swarm Command | C-DAC/NDRF | SDRF |
| S4 Rescue Coord | NDRF/SDRF | Health |
| S5 Early Warning | SDMA/SEOC | IMD |
| S6 ERSS Connector | ERSS/PSAP | C-DAC |
| S7 Data Handover | NDMA | SDMA |
| S8 Infrastructure | NIC | C-DAC |
| S9 AI/ML | C-DAC | NIC |
| S10 Citizen App | NDMA | SDMA |

---

## 📄 License

Proprietary — Developed for Government of India disaster management infrastructure.

---

**Built with ❤️ for India's disaster resilience** 🇮🇳

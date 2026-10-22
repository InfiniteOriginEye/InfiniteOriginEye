# Agency Ownership Map - SC&C System

## Component → Agency Ownership

| Component | Name | Build Agency | Operate Agency | Key Personnel |
|-----------|------|-------------|----------------|---------------|
| S1 | Incident Intake & Triage | C-DAC | SDMA/SEOC | SEOC Duty Officer (reviews), Data Entry Operator (manual entry) |
| S2 | Professional Review Dashboard | C-DAC | SDMA/SEOC | SEOC Duty Officer (approves/rejects), SEOC Supervisor (oversight) |
| S3 | Swarm Command & Control | C-DAC | NDRF (national), SDRF/Fire (state) | Swarm Commander (NDRF Inspector), Drone Pilot (licensed), GIS Analyst |
| S4 | Rescue Team Coordination | C-DAC | NDRF/SDRF/Health | Team Leader (field ops), Medical Officer (patient handover), Comms Officer |
| S5 | Early-Warning Ingest | C-DAC | SDMA/SEOC | SEOC Watch Officer (monitors), IMD Liaison Officer (data feed) |
| S6 | ERSS/112 Connector | C-DAC | ERSS/PSAP | PSAP Supervisor (CAD ops), ERSS Technical Officer (integration) |
| S7 | Data Handover & Reporting | C-DAC | NDMA/SDMA | NDMA Compliance Officer, SDMA Data Manager |
| S8 | Platform Infrastructure | C-DAC | NIC | NIC System Administrator, NIC Network Engineer, Security Auditor |
| S9 | AI/ML Pipeline | C-DAC | C-DAC | C-DAC ML Engineer (training), C-DAC Data Scientist (evaluation) |
| S10 | Citizen App | C-DAC | NDMA/SDMA | NDMA Public Information Officer, SDMA App Coordinator |

## Personnel → Software Actions

### SEOC Duty Officer (SDMA)
- Reviews AI triage decisions in S2
- Approves/overrides severity, swarm deployment
- Authorizes dispatch of drone swarms and rescue teams
- Views real-time mission status in S2 dashboard

### Swarm Commander (NDRF/SDRF)
- Commands drone swarms via S3 tactical interface
- Sets mission areas and formation patterns
- Monitors 3D digital twin (Mother Drone map)
- Initiates swarm recall/abort

### Drone Pilot (Licensed)
- Monitors individual drone status in S3
- Can override autonomous drone commands
- Manages return-to-base and emergency landing

### Field Team Leader (NDRF/SDRF/Fire)
- Uses S4 mobile app for mission details
- Reports victim locations via app
- Coordinates patient handover with medical teams
- Receives drone-delivered supplies (Medical legion)

### IMD Liaison Officer
- Configures S5 feed ingestion parameters
- Sets threshold values for automated alerts
- Validates weather data accuracy

### PSAP Supervisor (ERSS)
- Manages S6 integration settings
- Views incident sync status
- Handles escalation from 112 to SC&C

### NIC System Administrator
- Deploys S8 on NIC MeghRaj cloud
- Manages Kubernetes clusters
- Handles monitoring and incident response

"""
Triage Pipeline - AI Incident Severity Classification

Input:  incident text, location, hazard_type, media
Output: severity_score, needs_swarm, swarm_config, confidence

Models:
  - XGBoost/LightGBM for structured feature triage
  - Fine-tuned BERT/IndicBERT for multilingual text (Hindi, Tamil, Malayalam, etc.)
  - Whisper for voice → text from 112 calls

Human-in-the-loop: All predictions go to S2 review queue.
Duty Officer must approve before any dispatch happens.
"""

"""
Damage Assessment Pipeline - Aerial Image Analysis

Models:
  - YOLOv8/YOLO11: Object detection (collapsed buildings, flooded areas, vehicles, people)
  - SAM (Segment Anything Model): Fine-grained damage segmentation
  - Classification: Damage grading (none, minor, moderate, major, destroyed)

Input:  Drone imagery (Mother Drone + Ant legion)
Output: Bounding boxes, segmentation masks, damage grades per structure

Served via: Triton Inference Server (ONNX/TensorRT optimized)
Annotation: CVAT for training data labeling
"""

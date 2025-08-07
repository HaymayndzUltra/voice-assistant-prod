# Affective Processing Center (APC)

## Overview

The Affective Processing Center is a unified, DAG-based service for real-time emotional context analysis and synthesis. It consolidates seven legacy emotion-related agents into a single, modular, high-performance system.

## Features

- **DAG-based Processing**: Modular emotion processing with dependency resolution
- **Real-time Analysis**: Sub-60ms p95 latency for emotional context vector generation
- **Multi-modal Input**: Supports both audio chunks and text transcripts
- **Fusion Engine**: Weighted ensemble of emotion processing modules
- **ZMQ Transport**: High-performance messaging for integration
- **GPU Optimized**: CUDA-accelerated ML models for emotion detection

## Architecture

### Core Components

- **DAG Executor**: Orchestrates parallel execution of emotion modules
- **Emotion Modules**: tone, mood, empathy, voice_profile, human_awareness, synthesis
- **Fusion Layer**: Combines module outputs into unified Emotional Context Vector
- **Feature Cache**: LRU cache for embedding reuse
- **Transport Layer**: ZMQ publisher/subscriber for real-time streaming

### Processing Pipeline

1. Input (AudioChunk or Transcript) → DAG Executor
2. Parallel module execution based on dependencies
3. Feature caching and reuse optimization
4. Fusion of module outputs
5. ECV broadcast via ZMQ

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

## Performance Targets

- **Latency**: p95 < 60ms end-to-end
- **Throughput**: 200 ECV/second sustained
- **GPU Utilization**: ≤ 60% under 100 RPS load
- **Accuracy**: r ≥ 0.85 correlation vs legacy system
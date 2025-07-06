# Voice Assistant System - Architecture Overview

This document provides a high-level overview of the voice assistant system architecture, showing the key subsystems and their interactions.

## System Architecture Diagram

```mermaid
flowchart TB
    subgraph mainPC[Main PC (192.168.1.27)]
        subgraph AudioPipeline[Audio Pipeline]
            direction TB
            mic([Microphone Input]) --> AudioCapture[Audio Capture]
            AudioCapture -->|Raw Audio\nPort 6575| NoiseReduction[Noise Reduction]
            NoiseReduction -->|Clean Audio\nPort 6578| VAD[Voice Activity Detection]
            VAD -->|VAD Events\nPort 6579| WakeWord[Wake Word Detection]
            VAD --> ASR[Speech Recognition]
            WakeWord -->|Wake Event\nPort 6577| ASR
            ASR -->|Transcript\nPort 5580| LangTranslation[Language & Translation]
        end

        subgraph TextPipeline[Text Pipeline]
            direction TB
            LangTranslation -->|English Text\nPort 5564| Coordinator[Coordinator Agent]
            Coordinator -->|Commands| CodeCmd[Code Command Handler]
            Coordinator -->|Questions| KnowledgeBase[Knowledge Base]
            Coordinator -->|Goals| Swarm[Multi-Agent Swarm]
            Coordinator -->|Chitchat\nPort 5573| Chitchat[Chitchat Agent]

            CodeCmd --> TextProcessor[Streaming Text Processor]
            TextProcessor -->|Code Generation\nPort 5556| MMA[Model Manager Agent]
        end

        subgraph MemorySystem1[Memory System (mainPC)]
            direction TB
            SessionMem[Session Memory\nPort 5574]
            KnowledgeBase --> MemoryClient[Memory Client]
            Coordinator <--> SessionMem
        end

        subgraph TTS[TTS System]
            TTSConnector[TTS Connector] --> SpeechSynth[Speech Synthesis]
            SpeechSynth --> Speaker([Speaker Output])
        end

        LangTranslation --> TTSConnector

        Bridge[ZMQ Bridge\nPort 5600] <--> PC2Connection
    end

    subgraph PC2[PC2 (192.168.1.2)]
        PC2Connection[PC2 Connection]

        subgraph ModelRouter[Model Router System]
            EnhancedRouter[Enhanced Model Router\nPort 5598]
            TinyLlama[TinyLlama Service\nPort 5615]
            ChainOfThought[Chain of Thought\nPort 5646]
            EnhancedRouter --> TinyLlama
            EnhancedRouter --> ChainOfThought
        end

        subgraph TranslationSystem[Translation System]
            Translator[Translator Agent\nPort 5563]
            NLLBAdapter[NLLB Adapter\nPort 5581]
            Translator --> NLLBAdapter
        end

        subgraph MemorySystem2[Memory System (PC2)]
            ContextualMem[Contextual Memory\nPort 5596]
            JarvisMem[Jarvis Memory\nPort 5598-PUB]
            ErrorMem[Error Pattern Memory\nPort 5611]
        end

        subgraph Infrastructure[Infrastructure]
            SelfHealing[Self-Healing Agent\nPort 5614]
            SelfHealing -->|Monitors| AllPC2([All PC2 Agents])
        end

        PC2Connection --> EnhancedRouter
        PC2Connection --> Translator
        EnhancedRouter <--> ContextualMem
        EnhancedRouter <--> JarvisMem
    end

    MMA <-->|Model Requests| Bridge
    LangTranslation <-->|Translation Requests| Bridge

    classDef audio fill:#bee6fe,stroke:#1c6ea4
    classDef text fill:#ffe2b8,stroke:#c77b00
    classDef memory fill:#d5ffd1,stroke:#3b7c3b
    classDef infra fill:#f9c8d4,stroke:#a8233c

    class AudioPipeline audio
    class TextPipeline text
    class MemorySystem1,MemorySystem2 memory
    class TTS audio
    class ModelRouter text
    class TranslationSystem text
    class Infrastructure infra
```

## Subsystem Descriptions

### Audio Pipeline (mainPC)

The audio pipeline handles all audio processing from microphone capture to speech recognition. Key components include noise reduction, voice activity detection, wake word detection, and speech recognition.

### Text Pipeline (mainPC)

The text pipeline processes transcribed speech, classifies it by intent, and routes it to appropriate handlers for commands, questions, goals, or casual conversation.

### Memory System (mainPC & PC2)

Distributed across both machines, the memory system maintains short-term session context and long-term knowledge. SessionMemoryAgent operates on mainPC while more complex memory services run on PC2.

### PC2 Integration

Communication between mainPC and PC2 happens via the ZMQ Bridge on port 5600. PC2 hosts advanced AI models and services including the Enhanced Model Router, translation services, and specialized memory components.

## Key Cross-System Flows

1. **Voice Input to Response**: Audio → ASR → Language & Translation → Coordinator → Handler → TTS → Speaker
2. **Code Generation**: Coordinator → Text Processor → MMA → Bridge → PC2 Model Router → LLM → Bridge → MMA → Coordinator
3. **Translation**: Language & Translation → Bridge → Translator Agent → NLLB Adapter → Translator Agent → Bridge → Language & Translation
4. **Memory Retrieval**: Coordinator → Session Memory (local) or Bridge → PC2 Memory System → Bridge → Coordinator

## PC2 Agents

- Unified Memory Reasoning Agent (port 5596)
- DreamWorld Agent (port 5598-PUB)
- Other PC2 memory services

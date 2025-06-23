# Audio Preprocessing Features: AEC and AGC

## Overview

This document describes the implementation of Acoustic Echo Cancellation (AEC) and Automatic Gain Control (AGC) features in the FusedAudioPreprocessor. These features enhance the quality of audio input before it is processed by the speech recognition system.

## Audio Processing Pipeline

The complete audio processing pipeline now consists of the following steps:

1. **Acoustic Echo Cancellation (AEC)** - Removes echo from the audio input
2. **Noise Reduction** - Removes background noise
3. **Voice Activity Detection (VAD)** - Detects when someone is speaking
4. **Automatic Gain Control (AGC)** - Normalizes the volume level

## Acoustic Echo Cancellation (AEC)

### Purpose

Echo cancellation removes acoustic feedback that occurs when microphone picks up sound from speakers. This is especially important in voice assistant systems where the system's own audio output can be captured by the microphone.

### Implementation

The AEC implementation uses an adaptive filtering approach:

- **Algorithm**: Normalized Least Mean Square (NLMS) adaptive filter
- **Filter Length**: Configurable (default: 512 samples)
- **Step Size**: Controls adaptation speed (default: 0.05)
- **Leak Factor**: Prevents filter divergence (default: 0.9)

### Configuration Options

AEC can be configured through the `config/audio_preprocessing.json` file:

```json
{
    "AEC_ENABLED": true,
    "AEC_FILTER_LENGTH": 512,
    "AEC_STEP_SIZE": 0.05,
    "AEC_LEAK_FACTOR": 0.9,
    "AEC_REFERENCE_DELAY": 0
}
```

## Automatic Gain Control (AGC)

### Purpose

AGC dynamically adjusts the volume of audio input to maintain a consistent level. This ensures that:
- Quiet speech is amplified to be audible
- Loud speech is attenuated to prevent clipping
- The overall volume remains consistent across different speakers and environments

### Implementation

The AGC implementation uses an envelope follower with separate attack and release times:

- **Target Level**: The desired RMS level for the output (default: 0.5)
- **Attack Time**: How quickly gain increases for quiet signals (default: 0.01s)
- **Release Time**: How quickly gain decreases for loud signals (default: 0.1s)
- **Min/Max Gain**: Limits to prevent excessive amplification or attenuation

### Configuration Options

AGC can be configured through the `config/audio_preprocessing.json` file:

```json
{
    "AGC_ENABLED": true,
    "AGC_TARGET_LEVEL": 0.5,
    "AGC_MAX_GAIN": 10.0,
    "AGC_MIN_GAIN": 0.1,
    "AGC_ATTACK_TIME": 0.01,
    "AGC_RELEASE_TIME": 0.1,
    "AGC_FRAME_SIZE_MS": 10
}
```

## Integration with Existing Pipeline

The new features are integrated into the existing audio processing pipeline in the following order:

1. Raw audio is received from the audio capture component
2. AEC is applied to remove echo
3. Noise reduction is applied to remove background noise
4. VAD is performed to detect speech segments
5. AGC is applied to normalize the volume (primarily on speech segments)
6. Processed audio is published for downstream components

## Performance Considerations

- Both AEC and AGC are computationally efficient and add minimal latency to the pipeline
- AEC requires more memory due to the reference buffer and filter coefficients
- Processing times are logged periodically to monitor performance
- Both features can be disabled via configuration if performance issues arise

## Future Improvements

- **Real Reference Signal**: Currently using a simulated reference signal for AEC; a real implementation would connect to the system's audio output
- **Frequency-Domain Implementation**: For better performance with longer filters
- **Multi-channel Support**: For systems with multiple microphones
- **Dynamic Parameter Adjustment**: Automatically adjust parameters based on acoustic environment 
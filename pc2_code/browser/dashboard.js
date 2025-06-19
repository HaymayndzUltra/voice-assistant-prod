// NEXUS-AI CONTROL CENTER DASHBOARD
// Advanced Animations and Interactive Elements

// DOM Elements
const systemClock = document.getElementById('system-clock');
const audioWaveform = document.getElementById('audio-waveform');
const particlesContainer = document.getElementById('particles-container');
const voiceOutput = document.getElementById('voice-output');
const agentsOutput = document.getElementById('agents-output');
const logsOutput = document.getElementById('logs-output');
const commandOutput = document.getElementById('command-output');

// System initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing NEXUS-AI Control Center...');
    
    // Initialize all systems
    initializeMatrixBackground();
    initializeParticles();
    initializeWaveform();
    initializeTerminalTyping();
    initializeCommandInterface();
    initializeSystemClock();
    
    // Random glitch effect
    setInterval(triggerRandomGlitch, 10000);
    
    // Add terminal lines dynamically
    setInterval(addRandomLogEntry, 5000);
    setInterval(addRandomAgentActivity, 8000);
    
    // Add some initial random data
    setTimeout(() => {
        addVoiceActivitySimulation();
    }, 2000);
});

// Matrix Background Animation
function initializeMatrixBackground() {
    // Already handled in CSS with advanced animations
    console.log('Matrix background initialized');
}

// Initialize audio waveform visualization
function initializeWaveform() {
    // Create waveform bars
    const waveformContainer = document.querySelector('.waveform-bars');
    const barCount = 50; // Number of bars
    
    for (let i = 0; i < barCount; i++) {
        const bar = document.createElement('div');
        bar.className = 'waveform-bar';
        // Set random initial height
        const height = Math.floor(Math.random() * 30) + 5;
        bar.style.height = `${height}px`;
        waveformContainer.appendChild(bar);
    }
    
    // Start the animation
    animateWaveform();
}

// Animate waveform with realistic audio-like pattern
function animateWaveform() {
    const bars = document.querySelectorAll('.waveform-bar');
    const barCount = bars.length;
    
    // Use sine waves to create realistic audio pattern
    let phase = 0;
    const animateFrame = () => {
        phase += 0.1;
        
        // Create a fluctuating pattern with multiple frequencies
        for (let i = 0; i < barCount; i++) {
            // Multiple sine waves with different frequencies
            const sinValue1 = Math.sin(phase + i * 0.2) * 0.5 + 0.5;
            const sinValue2 = Math.sin(phase * 1.5 + i * 0.3) * 0.3 + 0.5;
            const sinValue3 = Math.sin(phase * 0.8 + i * 0.7) * 0.2 + 0.5;
            
            // Combine waves for complex pattern
            let combinedValue = (sinValue1 + sinValue2 + sinValue3) / 3;
            
            // Add randomness for realism
            combinedValue += (Math.random() * 0.1) - 0.05;
            
            // Apply height with smoothing
            const height = Math.max(5, Math.floor(combinedValue * 50));
            bars[i].style.height = `${height}px`;
            
            // Dynamic color based on height
            const intensity = Math.min(255, 100 + height * 3);
            bars[i].style.backgroundColor = `rgb(0, ${intensity}, 0)`;
            bars[i].style.boxShadow = `0 0 ${height/5}px rgb(0, ${intensity}, 0)`;
        }
        
        requestAnimationFrame(animateFrame);
    };
    
    animateFrame();
}

// Initialize particles
function initializeParticles() {
    // Create floating particles
    for (let i = 0; i < 50; i++) {
        createParticle();
    }
}

// Create a single floating particle
function createParticle() {
    const particle = document.createElement('div');
    particle.className = 'particle';
    
    // Random size
    const size = Math.random() * 3 + 1;
    
    // Random position
    const posX = Math.random() * 100;
    const posY = Math.random() * 100;
    
    // Random opacity
    const opacity = Math.random() * 0.5 + 0.1;
    
    // Random animation duration
    const duration = Math.random() * 30 + 10;
    
    // Set styles
    particle.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        background-color: rgba(0, 255, 0, ${opacity});
        border-radius: 50%;
        top: ${posY}%;
        left: ${posX}%;
        box-shadow: 0 0 ${size*2}px rgba(0, 255, 0, ${opacity});
        pointer-events: none;
        animation: floatParticle ${duration}s linear infinite;
    `;
    
    // Add keyframe animation
    const style = document.createElement('style');
    const animName = `floatParticle${Math.floor(Math.random() * 1000)}`;
    particle.style.animationName = animName;
    
    style.textContent = `
        @keyframes ${animName} {
            0% {
                transform: translate(0, 0) rotate(0deg);
                opacity: ${opacity};
            }
            25% {
                transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px) rotate(${Math.random() * 360}deg);
                opacity: ${opacity * 0.7};
            }
            50% {
                transform: translate(${Math.random() * 200 - 100}px, ${Math.random() * 200 - 100}px) rotate(${Math.random() * 720}deg);
                opacity: ${opacity};
            }
            75% {
                transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px) rotate(${Math.random() * 360}deg);
                opacity: ${opacity * 0.7};
            }
            100% {
                transform: translate(0, 0) rotate(0deg);
                opacity: ${opacity};
            }
        }
    `;
    
    document.head.appendChild(style);
    particlesContainer.appendChild(particle);
}

// Initialize system clock
function initializeSystemClock() {
    updateClock();
    setInterval(updateClock, 1000);
}

// Update system clock with current time
function updateClock() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    systemClock.textContent = `${hours}:${minutes}:${seconds}`;
}

// Add random log entries to simulate activity
function addRandomLogEntry() {
    const logTypes = ['info', 'warning', 'error', 'info', 'info']; // More info than warnings/errors
    const logType = logTypes[Math.floor(Math.random() * logTypes.length)];
    
    const infoMessages = [
        'System monitoring active',
        'Voice recognition processing',
        'Network connection stable',
        'Memory usage optimal',
        'API requests successful',
        'Translation service running',
        'Model inference complete',
        'Cache updated successfully',
        'Background task completed',
        'Configuration validated'
    ];
    
    const warningMessages = [
        'High CPU usage detected',
        'Network latency increasing',
        'Memory usage at 85%',
        'Service response time degraded',
        'API rate limit approaching'
    ];
    
    const errorMessages = [
        'Failed to connect to external API',
        'Model inference timeout',
        'Database query error',
        'Authentication failed',
        'File system permission denied'
    ];
    
    let message;
    switch (logType) {
        case 'info':
            message = infoMessages[Math.floor(Math.random() * infoMessages.length)];
            break;
        case 'warning':
            message = warningMessages[Math.floor(Math.random() * warningMessages.length)];
            break;
        case 'error':
            message = errorMessages[Math.floor(Math.random() * errorMessages.length)];
            break;
    }
    
    // Format current time for log
    const now = new Date();
    const timestamp = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
    
    // Create log line
    const logLine = document.createElement('div');
    logLine.className = `terminal-line ${logType}`;
    logLine.innerHTML = `<span class="timestamp">${timestamp}</span> <span class="prefix">${logType.toUpperCase()}:</span> ${message}`;
    
    // Add to logs with animation
    logsOutput.appendChild(logLine);
    
    // Remove oldest log if too many
    if (logsOutput.children.length > 30) {
        logsOutput.removeChild(logsOutput.children[0]);
    }
    
    // Auto scroll to bottom
    logsOutput.scrollTop = logsOutput.scrollHeight;
}

// Add random agent activity
function addRandomAgentActivity() {
    const agents = ['TRANSLATOR', 'ROUTER', 'SPEECH', 'CODE_GEN'];
    const agent = agents[Math.floor(Math.random() * agents.length)];
    
    const activities = {
        'TRANSLATOR': [
            'Processing Taglish input',
            'Translation complete',
            'Context analysis running',
            'Optimizing translation result'
        ],
        'ROUTER': [
            'Routing request to appropriate model',
            'Request prioritization complete',
            'Load balancing active',
            'Service discovery running'
        ],
        'SPEECH': [
            'Voice pattern recognized',
            'Audio processing complete',
            'Noise filtering active',
            'Listening for commands'
        ],
        'CODE_GEN': [
            'Analyzing code request',
            'Code generation complete',
            'Running syntax validation',
            'Optimizing generated code'
        ]
    };
    
    const activity = activities[agent][Math.floor(Math.random() * activities[agent].length)];
    
    // Format current time
    const now = new Date();
    const timestamp = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
    
    // Create agent activity line
    const agentLine = document.createElement('div');
    agentLine.className = 'terminal-line';
    agentLine.innerHTML = `<span class="timestamp">${timestamp}</span> <span class="prefix">${agent}:</span> ${activity}`;
    
    // Add to agent output with animation
    agentsOutput.appendChild(agentLine);
    
    // Remove oldest entry if too many
    if (agentsOutput.children.length > 20) {
        agentsOutput.removeChild(agentsOutput.children[0]);
    }
    
    // Auto scroll to bottom
    agentsOutput.scrollTop = agentsOutput.scrollHeight;
}

// Simulate voice activity
function addVoiceActivitySimulation() {
    // Trigger "active" waveform for a period
    const waveformBars = document.querySelectorAll('.waveform-bar');
    
    // Amplify all bars
    waveformBars.forEach(bar => {
        const currentHeight = parseInt(bar.style.height, 10);
        bar.style.height = `${currentHeight * 1.5}px`;
        
        // Brighter color for active state
        bar.style.backgroundColor = 'rgb(50, 255, 100)';
        bar.style.boxShadow = '0 0 15px rgb(50, 255, 100)';
    });
    
    // Add voice recognition message
    const now = new Date();
    const timestamp = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
    
    const voiceMessages = [
        'Voice input detected',
        'Processing voice command',
        'Voice pattern matched',
        'Command recognized'
    ];
    
    const message = voiceMessages[Math.floor(Math.random() * voiceMessages.length)];
    
    const voiceLine = document.createElement('div');
    voiceLine.className = 'terminal-line';
    voiceLine.innerHTML = `<span class="timestamp">${timestamp}</span> <span class="prefix">VOICE:</span> ${message}`;
    
    voiceOutput.appendChild(voiceLine);
    
    // Auto scroll
    voiceOutput.scrollTop = voiceOutput.scrollHeight;
    
    // Return to normal state after a delay
    setTimeout(() => {
        waveformBars.forEach(bar => {
            // Return to normal size gradually
            const currentHeight = parseInt(bar.style.height, 10);
            bar.style.height = `${Math.max(5, currentHeight / 1.5)}px`;
            
            // Return to normal color
            bar.style.backgroundColor = '';
            bar.style.boxShadow = '';
        });
        
        // Add completion message
        const completionLine = document.createElement('div');
        completionLine.className = 'terminal-line';
        
        const completionTimestamp = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${(now.getSeconds() + 2).toString().padStart(2, '0')}]`;
        completionLine.innerHTML = `<span class="timestamp">${completionTimestamp}</span> <span class="prefix">SYS:</span> Command processing complete`;
        
        voiceOutput.appendChild(completionLine);
        voiceOutput.scrollTop = voiceOutput.scrollHeight;
        
    }, 3000);
    
    // Schedule next voice activity
    setTimeout(addVoiceActivitySimulation, Math.random() * 15000 + 10000);
}

// Terminal typing animation
function initializeTerminalTyping() {
    const commandLines = document.querySelectorAll('.terminal-input-line');
    
    commandLines.forEach(line => {
        if (!line.classList.contains('active')) {
            const inputText = line.querySelector('.input-text');
            const originalText = inputText.textContent;
            
            // Clear and then type
            inputText.textContent = '';
            let charIndex = 0;
            
            const typeInterval = setInterval(() => {
                if (charIndex < originalText.length) {
                    inputText.textContent += originalText.charAt(charIndex);
                    charIndex++;
                } else {
                    clearInterval(typeInterval);
                }
            }, 100);
        }
    });
}

// Command interface
function initializeCommandInterface() {
    const commandTerminal = document.getElementById('command-terminal');
    const inputLine = commandTerminal.querySelector('.terminal-input-line');
    const inputText = inputLine.querySelector('.input-text');
    const cursor = inputLine.querySelector('.blinking-cursor');
    
    // Command history
    const commandHistory = [];
    let historyIndex = -1;
    
    // Available commands
    const commands = {
        'help': 'Display available commands',
        'status': 'Show system status',
        'agents': 'List active agents',
        'clear': 'Clear terminal',
        'reboot': 'Reboot system',
        'voice': 'Voice commands info'
    };
    
    // Focus the command line when clicking anywhere in the terminal
    commandTerminal.addEventListener('click', () => {
        // Make cursor blink to indicate focus
        cursor.classList.add('active');
    });
    
    // Handle command input
    document.addEventListener('keydown', (e) => {
        // Only process when command terminal is active
        if (!cursor.classList.contains('active')) return;
        
        if (e.key === 'Enter') {
            // Process command
            const command = inputText.textContent.trim();
            
            if (command) {
                // Add to history
                commandHistory.push(command);
                historyIndex = commandHistory.length;
                
                // Process command
                processCommand(command);
                
                // Clear input
                inputText.textContent = '';
            }
        } else if (e.key === 'Backspace') {
            // Remove last character
            inputText.textContent = inputText.textContent.slice(0, -1);
        } else if (e.key === 'ArrowUp') {
            // Previous command in history
            if (historyIndex > 0) {
                historyIndex--;
                inputText.textContent = commandHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            // Next command in history
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                inputText.textContent = commandHistory[historyIndex];
            } else {
                historyIndex = commandHistory.length;
                inputText.textContent = '';
            }
        } else if (e.key.length === 1) {
            // Add character to input
            inputText.textContent += e.key;
        }
    });
    
    // Process commands
    function processCommand(cmd) {
        const now = new Date();
        const timestamp = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;
        
        // Add command to output
        const cmdLine = document.createElement('div');
        cmdLine.className = 'terminal-line';
        cmdLine.innerHTML = `<span class="timestamp">${timestamp}</span> <span class="prompt">root@nexus:~#</span> ${cmd}`;
        commandOutput.appendChild(cmdLine);
        
        // Process command
        let responseLine = document.createElement('div');
        responseLine.className = 'terminal-line';
        
        switch (cmd.toLowerCase()) {
            case 'help':
                let helpText = '<span class="prefix">SYS:</span> Available commands:<br>';
                for (const [cmd, desc] of Object.entries(commands)) {
                    helpText += `&nbsp;&nbsp;<span style="color:#00ff99">${cmd}</span> - ${desc}<br>`;
                }
                responseLine.innerHTML = helpText;
                break;
                
            case 'status':
                responseLine.innerHTML = `<span class="prefix">SYS:</span> System Status: ONLINE<br>&nbsp;&nbsp;CPU Usage: 42%<br>&nbsp;&nbsp;Memory: 2.4GB/8GB<br>&nbsp;&nbsp;Active Agents: 4<br>&nbsp;&nbsp;Voice Recognition: Active<br>&nbsp;&nbsp;Uptime: 14h 32m`;
                break;
                
            case 'agents':
                responseLine.innerHTML = `<span class="prefix">SYS:</span> Active Agents:<br>&nbsp;&nbsp;TRANSLATOR: Running (PID: 3421)<br>&nbsp;&nbsp;ROUTER: Warning (High Load)<br>&nbsp;&nbsp;SPEECH: Running (PID: 3422)<br>&nbsp;&nbsp;CODE_GEN: Running (PID: 3425)`;
                break;
                
            case 'clear':
                // Clear the output
                while (commandOutput.firstChild) {
                    commandOutput.removeChild(commandOutput.firstChild);
                }
                return; // Skip adding response
                
            case 'reboot':
                responseLine.innerHTML = `<span class="prefix">SYS:</span> System reboot initiated...`;
                // Simulate reboot with screen glitch
                setTimeout(triggerRandomGlitch, 500);
                break;
                
            case 'voice':
                responseLine.innerHTML = `<span class="prefix">SYS:</span> Voice System Information:<br>&nbsp;&nbsp;Engine: Neural TTS<br>&nbsp;&nbsp;Recognition: Active<br>&nbsp;&nbsp;Language Models: EN, TL (Taglish)<br>&nbsp;&nbsp;Processing: Real-time<br>&nbsp;&nbsp;Wake Words: Active`;
                break;
                
            default:
                responseLine.innerHTML = `<span class="prefix error">ERROR:</span> Command not recognized: '${cmd}'. Type 'help' for available commands.`;
                break;
        }
        
        commandOutput.appendChild(responseLine);
        
        // Auto scroll
        commandOutput.scrollTop = commandOutput.scrollHeight;
    }
}

// Random screen glitch effect
function triggerRandomGlitch() {
    if (Math.random() < 0.7) { // 70% chance of glitch
        const glitchElement = document.createElement('div');
        glitchElement.className = 'glitch-effect active';
        document.body.appendChild(glitchElement);
        
        // Remove after animation completes
        setTimeout(() => {
            document.body.removeChild(glitchElement);
        }, 500);
        
        // Also make some random bars in the waveform spike
        const bars = document.querySelectorAll('.waveform-bar');
        for (let i = 0; i < 10; i++) {
            const randomBar = bars[Math.floor(Math.random() * bars.length)];
            randomBar.style.height = `${Math.random() * 70 + 30}px`;
            randomBar.style.backgroundColor = '#50ff50';
            randomBar.style.boxShadow = '0 0 20px #50ff50';
            
            // Reset after a short delay
            setTimeout(() => {
                randomBar.style.height = '';
                randomBar.style.backgroundColor = '';
                randomBar.style.boxShadow = '';
            }, 300);
        }
    }
    
    // Schedule next random glitch
    setTimeout(triggerRandomGlitch, Math.random() * 15000 + 5000);
}

// Log filters functionality
document.querySelectorAll('.log-filter').forEach(filter => {
    filter.addEventListener('click', () => {
        // Remove active class from all filters
        document.querySelectorAll('.log-filter').forEach(f => f.classList.remove('active'));
        
        // Add active class to clicked filter
        filter.classList.add('active');
        
        // Filter logs
        const filterType = filter.getAttribute('data-filter');
        const logEntries = document.querySelectorAll('#logs-output .terminal-line');
        
        logEntries.forEach(entry => {
            if (filterType === 'all') {
                entry.style.display = '';
            } else {
                if (entry.classList.contains(filterType)) {
                    entry.style.display = '';
                } else {
                    entry.style.display = 'none';
                }
            }
        });
    });
});

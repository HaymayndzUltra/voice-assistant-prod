#!/usr/bin/env python3
import os

legacy_ports = ['5570', '5575', '5617', '7222']
results = []

for root, dirs, files in os.walk('.'):
    # Skip certain directories
    if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', 'models', 'cache']):
        continue
        
    for file in files:
        if file.endswith(('.py', '.yml', '.yaml', '.json', '.md')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        for port in legacy_ports:
                            if port in line:
                                results.append(f"{filepath}:{line_num},{port},7211")
            except Exception as e:
                continue

print("file:line,old_port,recommended_port")
for result in results:
    print(result) 
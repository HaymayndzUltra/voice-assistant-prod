#!/usr/bin/env python3
"""
Generate detailed security fixes report from audit findings.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).resolve().parent.parent
PHASE2_JSON = BASE_DIR / 'output' / 'phase2_classification.json'
OUTPUT_REPORT = BASE_DIR / 'output' / 'SECURITY_FIXES_REPORT.md'

REMEDIATION_TEMPLATES = {
    'api_key': {
        'title': 'API Key Exposure',
        'severity': 'HIGH',
        'fix': """
1. Remove hardcoded API key from source code
2. Store in environment variable: `os.environ.get('API_KEY_NAME')`
3. Add to `.env` file (ensure .env is in .gitignore)
4. Update deployment configs to inject secrets
""",
        'example': """
# Before:
api_key = "sk-1234567890abcdef"

# After:
import os
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
"""
    },
    'password': {
        'title': 'Hardcoded Password',
        'severity': 'CRITICAL',
        'fix': """
1. Remove hardcoded password immediately
2. Use environment variables or secure vault
3. Implement proper authentication mechanism
4. Rotate compromised credentials
""",
        'example': """
# Before:
password = "admin123"

# After:
import os
from getpass import getpass
password = os.environ.get('SERVICE_PASSWORD') or getpass("Enter password: ")
"""
    },
    'token': {
        'title': 'Token/Secret Exposure',
        'severity': 'HIGH',
        'fix': """
1. Remove hardcoded token/secret
2. Use secure configuration management
3. Implement token rotation mechanism
4. Audit access logs for potential misuse
""",
        'example': """
# Before:
auth_token = "Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# After:
import os
auth_token = os.environ.get('AUTH_TOKEN')
"""
    },
    'hardcoded_ip': {
        'title': 'Hardcoded IP Address',
        'severity': 'MEDIUM',
        'fix': """
1. Move IP addresses to configuration files
2. Use DNS names instead of IPs where possible
3. Implement service discovery for dynamic environments
""",
        'example': """
# Before:
server_url = "http://192.168.1.100:8080"

# After:
import os
server_host = os.environ.get('SERVER_HOST', 'localhost')
server_port = os.environ.get('SERVER_PORT', '8080')
server_url = f"http://{server_host}:{server_port}"
"""
    },
    'debug_mode': {
        'title': 'Debug Mode Enabled',
        'severity': 'MEDIUM',
        'fix': """
1. Disable debug mode in production
2. Use environment-based configuration
3. Implement proper logging instead of debug prints
""",
        'example': """
# Before:
DEBUG = True

# After:
import os
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
"""
    }
}

def load_security_data() -> List[Dict[str, Any]]:
    """Load Phase 2 data and extract security issues"""
    with open(PHASE2_JSON, 'r') as f:
        data = json.load(f)
    
    security_records = []
    for record in data:
        if record.get('security_issues') and record['classification'] in ['active', 'unused']:
            security_records.append({
                'file_path': record['file_path'],
                'classification': record['classification'],
                'issues': record['security_issues'],
                'resource_usage': record.get('resource_usage', 'unknown')
            })
    
    return security_records

def generate_executive_summary(security_records: List[Dict]) -> str:
    """Generate executive summary of security findings"""
    total_files = len(security_records)
    total_issues = sum(len(r['issues']) for r in security_records)
    
    # Count by severity
    severity_counts = Counter()
    issue_type_counts = Counter()
    
    for record in security_records:
        for issue in record['issues']:
            severity_counts[issue['risk_level']] += 1
            issue_type_counts[issue['type']] += 1
    
    active_files = sum(1 for r in security_records if r['classification'] == 'active')
    
    return f"""# SECURITY FIXES REPORT

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Branch:** sot/comprehensive-audit-cleanup-2025

## EXECUTIVE SUMMARY

### Critical Findings
- **Total files with security issues:** {total_files}
- **Active agents with issues:** {active_files}
- **Total security issues found:** {total_issues}

### Issue Breakdown by Severity
- **CRITICAL:** {severity_counts.get('critical', 0)}
- **HIGH:** {severity_counts.get('high', 0)}
- **MEDIUM:** {severity_counts.get('medium', 0)}

### Issue Types Found
{chr(10).join(f"- **{k}:** {v} occurrences" for k, v in issue_type_counts.most_common())}

### Immediate Action Required
1. Fix all CRITICAL and HIGH severity issues in active agents
2. Rotate all exposed credentials
3. Implement environment-based configuration
4. Set up security scanning in CI/CD pipeline

---
"""

def generate_detailed_fixes(security_records: List[Dict]) -> str:
    """Generate detailed fix instructions for each file"""
    # Group by issue type
    by_issue_type = defaultdict(list)
    
    for record in security_records:
        for issue in record['issues']:
            by_issue_type[issue['type']].append({
                'file': record['file_path'],
                'line': issue['line'],
                'classification': record['classification']
            })
    
    detailed = "## DETAILED REMEDIATION GUIDE\n\n"
    
    for issue_type, occurrences in by_issue_type.items():
        template = REMEDIATION_TEMPLATES.get(issue_type, {})
        
        detailed += f"### {template.get('title', issue_type.upper())}\n"
        detailed += f"**Severity:** {template.get('severity', 'UNKNOWN')}\n"
        detailed += f"**Occurrences:** {len(occurrences)}\n\n"
        
        # List affected files (top 10)
        detailed += "**Affected Files:**\n"
        for occ in sorted(occurrences, key=lambda x: x['classification'])[:10]:
            status = "🔴" if occ['classification'] == 'active' else "🟡"
            detailed += f"- {status} `{occ['file']}` (line {occ['line']})\n"
        
        if len(occurrences) > 10:
            detailed += f"- ... and {len(occurrences) - 10} more files\n"
        
        detailed += f"\n**Fix Instructions:**\n{template.get('fix', 'Manual review required')}\n"
        detailed += f"\n**Example:**\n```python{template.get('example', '# Review required')}\n```\n\n"
        detailed += "---\n\n"
    
    return detailed

def generate_priority_list(security_records: List[Dict]) -> str:
    """Generate prioritized list of files to fix"""
    priority = "## PRIORITY FIX LIST\n\n"
    priority += "Fix these files first (active agents with critical/high severity issues):\n\n"
    
    # Calculate priority score
    priority_files = []
    for record in security_records:
        if record['classification'] == 'active':
            high_severity_count = sum(1 for i in record['issues'] if i['risk_level'] in ['critical', 'high'])
            if high_severity_count > 0:
                priority_files.append({
                    'file': record['file_path'],
                    'score': high_severity_count * 10 + len(record['issues']),
                    'high_count': high_severity_count,
                    'total_count': len(record['issues'])
                })
    
    # Sort by priority score
    priority_files.sort(key=lambda x: x['score'], reverse=True)
    
    priority += "| Priority | File | High/Critical Issues | Total Issues | Action |\n"
    priority += "|----------|------|---------------------|--------------|--------|\n"
    
    for i, pf in enumerate(priority_files[:20], 1):
        priority += f"| {i} | `{pf['file']}` | {pf['high_count']} | {pf['total_count']} | Immediate fix required |\n"
    
    return priority

def generate_implementation_plan() -> str:
    """Generate step-by-step implementation plan"""
    return """
## IMPLEMENTATION PLAN

### Phase 1: Critical Fixes (Week 1)
1. **Day 1-2:** Fix all hardcoded passwords and API keys in active agents
   - Create `.env.template` file with all required environment variables
   - Update deployment documentation
   - Rotate all exposed credentials

2. **Day 3-4:** Fix authentication tokens and secrets
   - Implement secure token storage
   - Set up HashiCorp Vault or AWS Secrets Manager
   - Update agent initialization code

3. **Day 5:** Testing and validation
   - Test all modified agents
   - Verify no hardcoded secrets remain
   - Update health checks

### Phase 2: Infrastructure Updates (Week 2)
1. **Day 1-2:** Implement configuration management
   - Create centralized config service
   - Move all hardcoded IPs to config
   - Implement service discovery

2. **Day 3-4:** Set up security scanning
   - Add pre-commit hooks for secret detection
   - Integrate security scanning in CI/CD
   - Set up automated alerts

3. **Day 5:** Documentation and training
   - Update security guidelines
   - Train team on secure coding practices
   - Create security checklist

### Phase 3: Ongoing Security (Continuous)
1. Regular security audits (monthly)
2. Automated secret rotation (quarterly)
3. Security training updates (bi-annually)
4. Penetration testing (annually)

---

## PREVENTION MEASURES

### 1. Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit detect-secrets

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### 2. Environment Variable Template
Create `.env.template`:
```
# API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=
DB_PASSWORD=

# Services
REDIS_HOST=localhost
REDIS_PORT=6379
MAINPC_HOST=172.20.0.10
PC2_HOST=172.20.0.11
```

### 3. Secure Configuration Class
```python
import os
from typing import Optional

class SecureConfig:
    @staticmethod
    def get_required(key: str) -> str:
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Required environment variable {key} not set")
        return value
    
    @staticmethod
    def get_optional(key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)
```

---
"""

def main():
    """Generate comprehensive security fixes report"""
    security_records = load_security_data()
    
    if not security_records:
        print("No security issues found in the audit data.")
        return
    
    report = ""
    report += generate_executive_summary(security_records)
    report += generate_priority_list(security_records)
    report += generate_detailed_fixes(security_records)
    report += generate_implementation_plan()
    
    # Save report
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, 'w') as f:
        f.write(report)
    
    print(f"Security fixes report generated: {OUTPUT_REPORT}")
    print(f"\nSummary:")
    print(f"- Files with security issues: {len(security_records)}")
    print(f"- Total issues found: {sum(len(r['issues']) for r in security_records)}")
    print(f"- Active agents affected: {sum(1 for r in security_records if r['classification'] == 'active')}")

if __name__ == '__main__':
    main()
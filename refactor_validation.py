#!/usr/bin/env python3
"""Validation script for the refactored ActionItemExtractor.

Runs a suite of heterogeneous commands (simple, sequential, parallel, conditional, hierarchical)
and prints the decomposed plan for manual inspection.  The script exits with status 0 if all
cases yield at least one action, otherwise 1.
"""
from workflow_memory_intelligence_fixed import ActionItemExtractor
import json

extractor = ActionItemExtractor()

test_cases = [
    # Existing multilingual auth cases
    ("🇵🇭 PURONG FILIPINO", "Gawin natin ang bagong user authentication feature. Una sa lahat, i-update ang schema ng database para magkaroon ng 'users' table na may 'username' at 'password_hash' na mga column. Pagkatapos, bumuo ka ng isang API endpoint na '/login' na tumatanggap ng POST requests. Kung tama ang credentials, dapat itong magbalik ng isang JWT. Kung mali, dapat itong magbalik ng 401 Unauthorized error. Panghuli, gumawa ka ng isang simpleng login form sa frontend para i-test ang bagong endpoint."),
    ("🇺🇸 PURE ENGLISH", "Let's build the new user authentication feature. First of all, update the database schema to include a 'users' table with 'username' and 'password_hash' columns. Afterwards, create an API endpoint at '/login' that accepts POST requests. If the credentials are correct, it must return a JWT. If they are incorrect, it must return a 401 Unauthorized error. Finally, create a simple login form on the frontend to test the new endpoint."),
    ("🔀 TAGLISH", "I-build natin ang bagong user auth feature. First, i-update mo ang database schema, magdagdag ka ng 'users' table na may 'username' at 'password_hash' columns. Then, gawa ka ng API endpoint, sa '/login', na tatanggap ng POST requests. Kapag tama ang credentials, kailangan mag-return ito ng JWT. Kung mali naman, dapat 401 Unauthorized error ang i-return. Lastly, gawa ka ng simpleng login form sa frontend para ma-test natin yung endpoint."),
    # CI/CD Pipeline (parallel + sequential)
    ("CI/CD PIPELINE", "Configure a CI/CD pipeline: 1) Run unit tests, 2) Build Docker image, 3) Deploy to staging & production in parallel, then notify the team."),
    # Code Cleanup (simple list)
    ("CODE CLEANUP", "Please: - Remove unused imports, - Format the code, - Add missing docstrings."),
    # Database Migration (hierarchical with conditionals)
    ("DB MIGRATION", "Perform database migration steps: a) Backup current DB; b) Apply new schema changes; c) If migration succeeds, update version table; if it fails, restore from backup.")
]

print("🧪 Validation Run — Refactored ActionItemExtractor")
print("=" * 72)
all_ok = True
for name, text in test_cases:
    steps = extractor.extract_action_items(text)
    print(f"\n🎯 {name}")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s}")
    if not steps:
        print("⚠️  No steps extracted!")
        all_ok = False

print("\n" + "=" * 72)
print("✅ SUCCESS" if all_ok else "❌ FAILURE: Some test cases produced no output")
exit(0 if all_ok else 1)
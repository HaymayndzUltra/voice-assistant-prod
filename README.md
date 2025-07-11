
---
## CI/CD Performance Gate (TODO)

A CI job (e.g., in `.github/workflows/main.yml`) must be configured to perform the following on every Pull Request:
1. Run the baseline performance snapshot: `python scripts/bench_baseline.py`.
2. Store the results as a CI artifact.
3. Compare the new results against the baseline from the `main` branch.
4. Fail the CI check if the new performance is slower than the baseline by more than 15%. 
---
alwaysApply: false
---
---

### Archivo 3: Reglas de CI/CD (`rules/cicd_rules.md`)
*Úsalo cuando pidas configurar GitHub Actions, GitLab CI o Jenkins.*

```markdown
# TRYCORE CI/CD & Governance Policy

## Context
Design a CI/CD pipeline that acts as the "Iron Gate" for software quality. 
It must strictly enforce the SonarQube Quality Gate on NEW CODE.

## 1. Pipeline Failure Conditions (The Iron Gate)
- The pipeline MUST **FAIL** and block deployment if the Quality Gate is not met.
- **Quality Gate Metrics (New Code)**:
  - Security Rating: **A** (0 Vulnerabilities).
  - Reliability Rating: **A** (0 Bugs).
  - Maintainability Rating: **A** (Technical Debt < 5%).
  - Duplications: **< 3%**.
  - Coverage: **> 80%**.

## 2. SonarScanner Configuration
- **Leak Period**: Define "New Code" as code changed in the current PR or strictly follow the `sonar.leak.period` setting.
- **Exclusions (Smart Exclusions)**:
  - Configure `sonar.exclusions` to ignore:
    - `**/migrations/**`
    - `**/node_modules/**`
    - `**/dist/**`
    - `**/*_test.py` (Tests should not be analyzed as production code).

## 3. Implementation Details (GitHub Actions Example)
- Use strict versions for actions (avoid `@latest`).
- Include a step specifically to check the Quality Gate status.

## 4. False Positive Protocol
- If a rule requires exception, add a comment in the pipeline script or configuration explaining the "Won't Fix" rationale, referencing the "Leadership Review" requirement.

## Pipeline Snippet Requirement
Always include the `quality-gate-check` step.
Example for GitHub Actions:
```yaml
      - name: SonarQube Quality Gate Check
        uses: sonarsource/sonarqube-quality-gate-action@master
        timeout-minutes: 5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        # Force failure if Quality Gate is red
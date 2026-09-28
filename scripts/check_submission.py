#!/usr/bin/env python3
"""
CivicPulse Pre-Submission Verification Linter (§5.8)
Checks for mechanical failures and automatic deductions listed in §5.3.
"""

import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def log_pass(msg: str):
    print(f"{GREEN}[PASS]{RESET} {msg}")


def log_fail(msg: str):
    print(f"{RED}[FAIL]{RESET} {msg}")


def log_warn(msg: str):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def check_required_files():
    failures = 0
    required = [
        "README.md",
        "compose.yaml",
        "compose.prod.yaml",
        ".env.example",
        "load/k6-script.js",
        ".github/workflows/ci.yml",
        ".github/workflows/cd.yml",
        ".github/workflows/release.yml",
        "docs/ENGINEERING-NOTES.md",
        "docs/RUNBOOK.md",
        "docs/AI-USAGE.md",
        "docs/TRIAGE.md",
        "docs/adr/0001-provider-interface.md",
        "docs/adr/0002-frontend-runtime-config.md",
        "docs/adr/0003-docker-compose-networks-and-persistence.md",
        "docs/adr/0004-pii-and-data-governance.md",
        "k8s/base/namespace.yaml",
        "k8s/base/backend.yaml",
        "k8s/base/frontend.yaml",
        "k8s/base/postgres.yaml",
        "k8s/base/redis.yaml",
        "k8s/base/ingress.yaml",
        "k8s/base/configmap.yaml",
        "k8s/base/secret.yaml",
        "k8s/base/hpa.yaml",
        "k8s/base/vpa.yaml",
        "k8s/base/pdb.yaml",
        "k8s/base/kustomization.yaml",
        "k8s/overlays/dev/kustomization.yaml",
        "k8s/overlays/prod/kustomization.yaml",
    ]

    print("\n--- 1. Checking Required Repository Files (§5.7) ---")
    for rel_path in required:
        file_path = ROOT_DIR / rel_path
        if file_path.exists():
            log_pass(f"Found {rel_path}")
        else:
            log_fail(f"Missing required file: {rel_path}")
            failures += 1
    return failures


def check_secrets_and_env():
    failures = 0
    print("\n--- 2. Checking Secret Hygiene & .env Leaks (§5.3) ---")
    if (ROOT_DIR / ".env").exists():
        log_warn(".env file exists in working tree. Ensure it is NOT tracked by Git!")
    
    # Check .gitignore
    gitignore = ROOT_DIR / ".gitignore"
    if gitignore.exists() and ".env" in gitignore.read_text():
        log_pass(".env is included in .gitignore")
    else:
        log_fail(".env is missing from .gitignore!")
        failures += 1

    # Check Kubernetes secrets for plain keys
    secret_yaml = ROOT_DIR / "k8s/base/secret.yaml"
    if secret_yaml.exists():
        content = secret_yaml.read_text()
        if "sk-" in content or "gsk_" in content:
            log_fail("Live API key detected in k8s/base/secret.yaml! Manifests must carry placeholders only.")
            failures += 1
        else:
            log_pass("k8s/base/secret.yaml contains placeholders only.")
    return failures


def check_compose_security():
    failures = 0
    print("\n--- 3. Checking Docker Compose Security & Separation (§3.2, §5.3) ---")
    prod_compose = ROOT_DIR / "compose.prod.yaml"
    if prod_compose.exists():
        text = prod_compose.read_text()
        if "build:" in text:
            log_fail("compose.prod.yaml contains 'build:' keys! Must use pre-built immutable images.")
            failures += 1
        else:
            log_pass("compose.prod.yaml contains no 'build:' keys.")

        # Check published ports on db and cache in prod
        # Matches published ports under postgres/redis sections
        if "5432:5432" in text or "6379:6379" in text:
            log_fail("compose.prod.yaml publishes database or cache ports to host!")
            failures += 1
        else:
            log_pass("Database and cache ports are private in compose.prod.yaml.")
    return failures


def check_kubernetes_specs():
    failures = 0
    print("\n--- 4. Checking Kubernetes Architecture (§3.3, §5.3) ---")
    pg_file = ROOT_DIR / "k8s/base/postgres.yaml"
    if pg_file.exists():
        content = pg_file.read_text()
        if "kind: Deployment" in content and "postgres" in content:
            log_fail("PostgreSQL declared as Deployment! Must be a StatefulSet with volumeClaimTemplates.")
            failures += 1
        elif "kind: StatefulSet" in content and "volumeClaimTemplates" in content:
            log_pass("PostgreSQL declared as StatefulSet with volumeClaimTemplates.")
        else:
            log_fail("PostgreSQL StatefulSet missing volumeClaimTemplates.")
            failures += 1
    return failures


def main():
    print("=" * 60)
    print("CivicPulse Pre-Submission Verification Lint")
    print("=" * 60)

    total_failures = 0
    total_failures += check_required_files()
    total_failures += check_secrets_and_env()
    total_failures += check_compose_security()
    total_failures += check_kubernetes_specs()

    print("\n" + "=" * 60)
    if total_failures == 0:
        print(f"{GREEN}ALL MECHANICAL CHECKS PASSED! Ready for submission.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}FOUND {total_failures} ISSUE(S). Please resolve them before submitting.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

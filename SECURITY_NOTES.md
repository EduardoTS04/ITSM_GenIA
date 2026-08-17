# Security Notes & Incident Response

## Overview
This repository uses Gitleaks for automated secret detection in CI/CD pipelines.

## Configuration & Local Overrides
- Environment variables: `.env` (untracked, git-ignored).

## Automated Protection
- GitHub Actions workflow `.github/workflows/secret-scan.yml` scans every push and pull request.
- `.gitleaks.toml` maintains the secret detection rules.

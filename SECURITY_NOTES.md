# Security Notes

## Overview
This repository uses Gitleaks for automated secret detection in CI/CD pipelines.

## What stays local
- Environment variables: `.env` / `backend/.env` (untracked, git-ignored). Copy `backend/.env.example`.
- SQLite files (`*.db`, including `backend/data/itsm.db` and `data/itsm.db`) are git-ignored. Do not commit ticket databases.

## Automated Protection
- GitHub Actions workflow `.github/workflows/secret-scan.yml` scans every push and pull request.
- `.gitleaks.toml` maintains the secret detection rules.

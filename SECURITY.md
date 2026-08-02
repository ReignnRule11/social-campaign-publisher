# Security & Secret Management

## Overview

This guide covers secret management, security best practices, and how to keep sensitive data out of the repository.

## Secret Types & Storage

### Environment Variables (Development)

For local development, use a `.env` file (never commit):

```bash
# .env (NOT committed)
SECRET_KEY=your-32-byte-hex-key
WEBHOOK_SECRET=your-webhook-secret
DATABASE_URL=sqlite:///./dev.db
REDIS_URL=redis://localhost:6379/0
```

Load in Python:

```python
import os
from dotenv import load_dotenv

load_dotenv()
secret_key = os.getenv("SECRET_KEY")
```

### Docker Secrets (Production)

Docker Swarm and docker-compose support `secrets`:

```bash
# Create a secret
echo -n "my-secure-password" | docker secret create db_password -

# Use in docker-compose.yml
services:
  app:
    secrets:
      - db_password
    environment:
      DB_PASSWORD: /run/secrets/db_password
```

### Kubernetes Secrets (Production)

For Kubernetes deployments, use native secret objects:

```bash
kubectl create secret generic app-secrets \
  --from-literal=SECRET_KEY=my-secret-key \
  --from-literal=WEBHOOK_SECRET=my-webhook-secret
```

Mount in Pod spec:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: social-campaign-publisher
spec:
  containers:
    - name: app
      env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: SECRET_KEY
```

## Scanning for Secrets

### Pre-commit Local Scanning

Hooks run automatically before every commit:

```bash
# Install hooks
pip install pre-commit
pre-commit install

# Hooks will now run on `git commit` automatically

# Manual run:
pre-commit run --all-files
```

Hooks check for:
- Webhook URLs (Slack, Discord, Telegram)
- AWS access keys
- SSH keys
- High-entropy strings (likely tokens/passwords)
- Secrets detected by detect-secrets (Yelp)

Example output when secret detected:

```
detect-secrets.....FAILED
- hook id: detect-secrets
  exit code: 1

Secret detected:
  File: app/config.py
  Type: AWS Access Key
```

### CI/CD Secret Scanning

GitHub Actions runs on every push and PR:

```
Workflow: .github/workflows/secret-scan.yml
- Runs detect-secrets
- Runs heuristic scanner
- Posts comment on PRs
- Blocks merge if secrets found
```

### Manual Audit (detect-secrets)

```bash
# Generate baseline
detect-secrets scan > .secrets.baseline

# Audit interactively
detect-secrets audit .secrets.baseline

# Example session:
# Secret:      1 / 1
# Filename:    alertmanager.yml
# Type:        Base64 High Entropy String
# Value:       [redacted]
#
# Is this a valid secret? [y/n]: n
# Marked as invalid (false positive)

# Commit audited baseline
git add .secrets.baseline && git commit -m "Add audited baseline"
```

## Rotation & Remediation

### Discovered Secret in Repo?

1. **Rotate immediately** — regenerate the secret in the source system
2. **Remove from history** — use git-filter-branch or BFG Repo-Cleaner:

```bash
# Example: Remove API key from all history
bfg --replace-text secrets.txt --no-blob-protection

# Or with git-filter-branch
git filter-branch --tree-filter 'grep -r "SECRET_VALUE" . && sed -i "s/SECRET_VALUE/REDACTED/g" $(git ls-files) || true' HEAD
```

3. **Update baseline** — regenerate and audit `.secrets.baseline`
4. **Notify team** — ensure everyone pulls cleaned history

### Secret Rotation Schedule

Recommended rotation intervals:

```
API Keys / Tokens:      90 days
Database Passwords:    180 days
Webhook Secrets:        90 days
TLS Certificates:     365 days
```

## Best Practices

### ✅ DO

- Use `.env` files (add to `.gitignore`)
- Store secrets in environment variables
- Use Docker/Kubernetes native secret managers
- Rotate secrets regularly
- Audit pre-commit baseline annually
- Enable GitHub secret scanning in repo settings
- Use HTTPS for all external communication

### ❌ DON'T

- Commit `.env` files or `.env.local`
- Store secrets in code comments
- Use weak or reused passwords
- Commit test API keys (even fake ones — use placeholders)
- Store secrets in git history
- Share secrets via email/Slack
- Use same secret across environments

## Environment-Specific Secrets

### Development

```bash
# .env
SECRET_KEY=dev-32-byte-key-xxxxxxxxxxxxxxxxxxxxxxxx
WEBHOOK_SECRET=dev-webhook-secret
DATABASE_URL=sqlite:///./dev.db
DEBUG=True
```

### Staging

```bash
# Injected via CI/CD
SECRET_KEY=<vault-managed>
WEBHOOK_SECRET=<vault-managed>
DATABASE_URL=postgres://user:pass@staging-db:5432/app
DEBUG=False
```

### Production

```bash
# Injected via Kubernetes/Swarm secrets
SECRET_KEY=/run/secrets/prod_secret_key
WEBHOOK_SECRET=/run/secrets/prod_webhook_secret
DATABASE_URL=postgres://user:pass@prod-db:5432/app
REDIS_URL=redis://:pass@prod-redis:6379/0
DEBUG=False
```

## Monitoring for Leaks

### GitHub Secret Scanning

Enable in repo settings:

```
GitHub → Settings → Security → Secret scanning
→ Enable "Push protection"
```

This blocks commits containing:
- AWS keys
- GitHub tokens
- Generic API keys
- Database credentials

### External Monitoring

Consider services like:
- **GitGuardian** — scans GitHub for leaked secrets in real-time
- **TruffleHog** — finds high-entropy secrets in repos/commits
- **Spectral** — scans API keys, tokens, and credentials

Example GitHub Action (GitGuardian):

```yaml
name: GitGuardian Secret Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: GitGuardian/ggshield-action@v1
        with:
          api-key: ${{ secrets.GITGUARDIAN_API_KEY }}
```

## Incident Response

### If a Secret Leaks

1. **Assess impact** — which systems/accounts are affected?
2. **Rotate immediately** — change all passwords/keys
3. **Notify stakeholders** — security team, customers if needed
4. **Audit access logs** — check if secret was used maliciously
5. **Remove from history** — use git-filter-branch
6. **Monitor** — watch for unauthorized access for 30 days
7. **Update policy** — prevent recurrence

### Checklist

- [ ] Secret identified and classified
- [ ] Rotated in source system
- [ ] Removed from git history
- [ ] Baseline updated
- [ ] Team notified
- [ ] Access logs reviewed
- [ ] Incident documented
- [ ] Post-mortem scheduled (if critical)

## Further Reading

- [SETUP.md](./SETUP.md) — Development setup with examples
- [.pre-commit-config.yaml](./.pre-commit-config.yaml) — Pre-commit hook config
- [scripts/check_secrets.py](./scripts/check_secrets.py) — Heuristic scanner
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning)
- [Yelp/detect-secrets](https://github.com/Yelp/detect-secrets)

# Matchday Platform

AWS infrastructure, managed with Terraform, for a La Liga and Liga MX football data platform. It powers my Django API and React portfolio.

> 🚧 **Status:** In progress, Phase 1 (bootstrap)

## Tech stack

- **Terraform**: infrastructure as code
- **AWS**: cloud hosting
- **Docker**: containerized services
- **Supabase**: managed Postgres database

## Project structure

```
matchday-platform/
├── infra/
│   ├── bootstrap/   # One-time account setup (budget alerts)
│   ├── network/     # Networking (planned)
│   └── database/    # Database (planned)
└── services/        # Application services (planned)
```

## Roadmap

- [x] **Phase 1: Bootstrap**: monthly AWS budget with email alerts
- [ ] Remote Terraform state in S3
- [ ] Network
- [ ] Database
- [ ] Services

## Getting started

### Prerequisites

- Terraform >= 1.10
- AWS CLI with credentials configured

### Deploy the bootstrap stack

```bash
cd infra/bootstrap
echo 'alert_email = "you@example.com"' > terraform.tfvars
terraform init
terraform plan
terraform apply
```

`terraform.tfvars` is gitignored, so your email stays out of the repo.

## Cost control

A $20/month AWS budget sends an email when actual spend passes 80% or forecast spend passes 100%.

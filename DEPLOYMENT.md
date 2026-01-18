# Deploying LieSpy Backend to Coolify

This guide explains how to deploy the LieSpy backend to Coolify using **Nixpacks**.

## Configuration

When setting up the resource in Coolify, use the following settings:

| Setting           | Value                                                  |
|-------------------|--------------------------------------------------------|
| **Build Pack**    | Dockerfile                                             |
| **Base Directory**| `/backend`                                             |
| **Dockerfile Path**| `Dockerfile`                                          |
| **Ports Exposes** | `8000`                                                 |

## Environment Variables

You must add the following environment variables in the Coolify "Environment Variables" tab:

```ini
# Project
PROJECT_NAME="LieSpy API"
API_V1_STR="/api/v1"

# Database (Supabase / Postgres)
# Ensure this is the Transaction Pooler URL (usually port 6543) for asyncpg
DATABASE_URL="postgresql+asyncpg://user:password@host:6543/postgres"

# Supabase Auth/API
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-or-service-role-key"

# AI / LLM
OPENAI_API_KEY="your-key"
LLM_BASE_URL="https://api.perplexity.ai" # or other provider
LLM_MODEL="sonar-reasoning-pro" # or other model
```

## Troubleshooting

- **Health Checks**: If the deployment becomes unhealthy, ensure Coolify is checking the correct port (`8000`) and path (`/` or `/api/v1/openapi.json`).
- **Database Connection**: If using Supabase, make sure to use the **Session Mode** connection string for migrations (port 5432) if running locally, but the **Transaction Mode** (port 6543) is preferred for production apps with many connections, though `asyncpg` usually works fine with session mode if connection pooling is managed carefully. For simplicity, use the connection string that works with your local `alembic` setup, or the Transaction Pooler if available.

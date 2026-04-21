# AXION Serverless Migration Plan

Last updated: `2026-04-21`

## Goal

Migrate AXION away from VPS-centric hosting toward a serverless and managed-services architecture that:

- reduces origin CPU, RAM, disk, and bandwidth usage
- removes single-VPS dependency for public workloads
- keeps stateful and redesign-heavy services isolated until they can be replaced safely
- allows staged cutover without touching production DNS until explicitly approved

## Current Service Groups

The current workspace shows four broad classes of workloads:

1. Public web entrypoints
2. API and orchestration services
3. Stateful data and coordination services
4. Tenant and agent runtimes with persistent workspace state

## Target Architecture

### Cloudflare

- `Pages`
  For static and hybrid frontends:
  - `axionenterprise.cloud`
  - `www.axionenterprise.cloud`
  - public portions of `flow.axionenterprise.cloud`
  - public or operator-facing UX for `scan.axionenterprise.cloud`
  - lightweight admin dashboards

- `Workers`
  For:
  - API gateway and BFF endpoints
  - auth/session middleware
  - webhook receivers
  - signed upload/download URLs
  - cache-aware read APIs
  - redirect and edge security logic

- `R2`
  For:
  - uploads
  - generated files
  - PDFs
  - media
  - backup artifacts
  - tenant export bundles

- `Queues`
  For:
  - retries
  - async jobs
  - webhook fan-out
  - import/export processing
  - post-processing workloads previously buffered by NATS

- `Durable Objects`
  For:
  - tenant-scoped coordination
  - transient state
  - locks
  - presence/session maps
  - QR/session orchestration where state locality matters

- `KV`
  For:
  - config distribution
  - lightweight flags
  - cached lookups

- `D1`
  For:
  - lightweight relational metadata
  - low-to-medium volume control-plane tables
  - tenant registries and lightweight operational state

- `Hyperdrive`
  For:
  - connecting Workers to external Postgres while the data plane remains outside Cloudflare during transition

### Supabase

- `Postgres`
  Target for primary application relational state where full Postgres semantics are required.

- `Auth`
  Candidate target for user/admin authentication.

- `Storage`
  Secondary option for product-managed file workflows tightly coupled to Supabase auth and RLS.

- `Edge Functions`
  Candidate for HTTP functions that benefit from close coupling with Supabase auth/data.

- `Queues` and `pg_cron`
  Candidate replacements for some scheduled and background jobs that are data-centric.

### Other Low-Cost Services

- `Upstash`
  Candidate replacement for Redis/Valkey patterns that do not require local memory semantics.

- `Grafana Cloud` or `Better Stack`
  Candidate replacement for Grafana/Loki/Alloy/Uptime stack.

- `Railway` or `Fly.io`
  Candidate temporary home for workloads that are not realistically serverless yet, but can leave the main VPS.

## Service Classification

### Direct migration candidates

- `axionenterprise.cloud`
- `www.axionenterprise.cloud`
- public frontend of `flow.axionenterprise.cloud`
- lightweight `api.axionenterprise.cloud` endpoints
- static/admin UI assets
- webhook receivers
- cron-style jobs
- generated asset delivery

### Managed-service replacement candidates

- `postgres` -> Supabase Postgres
- `valkey` -> Upstash Redis or Cloudflare KV/Durable Objects depending on access pattern
- `nats` -> Cloudflare Queues or Supabase Queues
- `status.axionenterprise.cloud` -> Better Stack / UptimeRobot / Grafana Cloud Synthetic Monitoring
- `grafana.axionenterprise.cloud`, `loki`, `alloy` -> Grafana Cloud or Better Stack

### Redesign-required workloads

- `picoclaw-official`
- tenant `PicoClaw` containers
- `openclaw` gateway and multi-workspace agent topology
- any workload that depends on:
  - persistent filesystem workspaces
  - long-running container processes
  - local process supervision
  - mutable tenant directories
  - direct Docker socket access

These are not good fits for pure serverless right now. They should either:

- move to managed containers first, or
- be redesigned into split control-plane/data-plane services

## Migration Waves

### Wave 1: Remove easy VPS load

- Move landing and static web delivery to Cloudflare Pages
- Move uploads and generated files to R2
- Introduce Workers as edge gateway for read-heavy and webhook endpoints
- Replace NATS-backed async jobs with Queues where possible
- Move public health/status checks to external managed monitoring

Expected result:

- lower CPU and bandwidth on VPS
- fewer public origin responsibilities
- simpler origin exposure model

### Wave 2: Replace stateful platform primitives

- Move app relational data to Supabase Postgres
- Move auth to Supabase Auth if product model fits
- Replace Valkey usage case by case:
  - edge cache -> KV
  - coordination -> Durable Objects
  - Redis-like ephemeral cache -> Upstash
- Replace scheduled jobs with Supabase `pg_cron` or Cloudflare Cron/Queues

Expected result:

- VPS no longer needed for main app database/cache/queue duties

### Wave 3: Redesign agent and tenant runtime

- Separate AXION control plane from agent runtime
- Build tenant registry/control plane in Workers + Supabase
- Move tenant metadata, auth, job orchestration, and dashboards off VPS
- Rehome remaining long-running agent workloads to managed containers if serverless is still not viable

Expected result:

- only specialized runtimes remain outside serverless

## Reality Check

The current AXION stack cannot be moved "completely serverless" in one safe cut without redesigning the agent runtime model.

The blockers are structural:

- persistent per-tenant filesystems
- containerized agent runtimes
- process lifetimes longer than normal edge/serverless patterns
- Docker-native operations in `qr-scanner` and `tenant-chat`

So the safe interpretation of "complete migration" is:

- move all public/control-plane/app workloads to serverless or managed services
- isolate remaining runtime-heavy agent workloads into the smallest possible non-VPS surface

## Accounts Likely Needed

These are the external services most likely required beyond what is already in the workspace:

- Cloudflare Workers Paid plan
- Cloudflare R2
- Supabase project for AXION primary data plane
- Upstash Redis if Redis semantics remain necessary after redesign
- Grafana Cloud or Better Stack for observability/status

## Immediate Next Step

Implement Wave 1 first:

1. Create Cloudflare app structure for public AXION web and edge API
2. Define R2 bucket layout for assets and artifacts
3. Define Supabase target schema boundaries for AXION app data
4. Split current services into:
   - serverless now
   - managed replacement next
   - redesign required

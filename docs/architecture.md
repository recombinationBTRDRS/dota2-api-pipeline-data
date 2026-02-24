---

## 📄 docs/architecture.md

```md
# Architecture Overview

## 🔷 High-Level Flow

Match Discovery Service
  → знаходить матчі за фільтрами
  → ставить у чергу ingestion

Ingestion Service
  → завантажує raw JSON матчів з API
  → зберігає raw дані

Normalization Service
  → парсить JSON у DTO
  → нормалізує у внутрішні моделі

Storage Service
  → зберігає дані в SQLite/PostgreSQL
  → надає repository layer

Public API
  → віддає дані фронтенду

Analytics Service
  → будує статистику
  → рекомендації білдів, прокачки, талантів
  → аналіз контрів і синергій

## 🔷 Microservices

- match-discovery
- ingestion
- normalization
- storage
- api
- analytics

## 🔷 Data Flow

External APIs → Ingestion → Normalization → Storage → Public API / Analytics

## 🔷 Reliability

- Retry для API викликів
- Rate-limit handling
- Idempotent inserts
- Валідація та deduplication
- Черги для асинхронної обробки

## 🔷 CI/CD

- GitHub Actions
- pytest + coverage
- ruff (lint)
- mypy (types)
- Docker build
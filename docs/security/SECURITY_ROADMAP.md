# SmartOnboard Security Roadmap

## Purpose

This document tracks security controls, hardening efforts, audits, and production readiness requirements.

Security is considered a first-class feature of SmartOnboard.

---

# Milestone 11.5

Production Security & Reliability Foundation

Status: Complete

---

## Implemented Controls

### Authentication

Implemented:

* JWT Authentication
* Session Validation
* Refresh Token Support

Planned:

* Candidate OTP Authentication

---

### Authorization

Implemented:

* RBAC
* Recruiter Roles
* Ownership Checks

Planned:

* Candidate Scopes

---

### File Security

Implemented:

* File Size Validation
* MIME Validation
* Magic Byte Validation
* Malware Scanning Integration

---

### Rate Limiting

Implemented:

* Login Rate Limiting
* AI Endpoint Rate Limiting

Purpose:

* Prevent brute force attacks
* Prevent API abuse

---

### Secret Management

Implemented:

* Environment Validation
* Startup Failure On Missing Secrets

---

### Audit Logging

Implemented:

* Append-only Audit Logs
* Data Access Tracking

---

# Production Security Tasks

## Sentry

Required:

* FastAPI Integration
* Celery Integration
* Production Alerts

---

## Dependency Scanning

Required:

* pip-audit
* Dependabot

---

## Secret Scanning

Required:

* TruffleHog
* detect-secrets

---

## Docker Security

Required:

* Trivy Container Scans

---

## Monitoring

Required:

* Structured Logs
* Prometheus Metrics
* Queue Monitoring

---

# Candidate Security

Requirements:

* Email OTP
* SMS OTP
* JWT

Future:

* Identity Verification
* Employment Verification

---

# Recruiter Security

Requirements:

* Domain Validation
* DNS Validation
* MX Validation

Verification States:

* Pending Verification
* Verified Recruiter
* Verified Company
* Trusted Employer
* Suspended

---

# Security Principles

Trust is earned.

Every participant must be verifiable.

No internal recruiter intelligence should be exposed to candidates.

Security takes priority over convenience when trust is at risk.

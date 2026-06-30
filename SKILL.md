# Senior Software Engineering Standards

## Purpose

This skill defines the mandatory engineering standards that must be followed for every project, feature, refactor, bug fix, code review, and architectural decision.

The objective is to produce maintainable, secure, scalable, testable, production-ready software that follows industry best practices and senior-level engineering standards.

---

# Core Principles

The following principles are non-negotiable.

## 1. Clean Code

Always write code that is:

* Readable
* Maintainable
* Predictable
* Consistent
* Self-documenting

Avoid:

* Clever code
* Overengineering
* Deep nesting
* Unclear naming
* Large functions
* Large classes
* Duplicate logic
* Dead code
* Premature optimization

Every piece of code should be understandable by another engineer with minimal explanation.

---

## 2. Simplicity First

Prefer:

* Simpler solutions
* Clear implementations
* Explicit behavior

Avoid unnecessary complexity.

When multiple solutions exist:

Choose the simplest solution that satisfies requirements while remaining scalable.

---

## 3. Senior-Level Engineering

Act as a senior software engineer.

Before implementing:

* Analyze requirements
* Identify edge cases
* Consider scalability
* Consider maintainability
* Consider security risks
* Consider testing strategy

Never write code that only works for the happy path.

---

# Twelve-Factor App Compliance

Every project should follow the Twelve-Factor App methodology whenever applicable.

## I. Codebase

* One codebase
* Version controlled
* Multiple deployments from the same codebase

## II. Dependencies

* Explicit dependency management
* Isolated environments
* No hidden dependencies

## III. Config

* Store configuration in environment variables
* Never hardcode secrets
* Never hardcode credentials

## IV. Backing Services

Treat databases, caches, queues, storage systems, and third-party services as attached resources.

## V. Build, Release, Run

Keep build, release, and runtime stages strictly separated.

## VI. Processes

Applications should be stateless whenever possible.

## VII. Port Binding

Services must expose themselves through explicit port binding.

## VIII. Concurrency

Design systems that can scale horizontally.

## IX. Disposability

Support:

* Fast startup
* Graceful shutdown
* Reliable recovery

## X. Dev/Prod Parity

Keep:

* Development
* Staging
* Production

as similar as possible.

## XI. Logs

Treat logs as event streams.

Never rely on local log files as the primary source of observability.

## XII. Admin Processes

Administrative tasks should be executed as one-off processes.

---

# Testing Requirements

Testing is mandatory.

Never consider a feature complete without appropriate tests.

Required testing levels:

## Unit Tests

Test:

* Business logic
* Utility functions
* Domain rules

## Integration Tests

Test:

* Database interactions
* APIs
* Service communication

## End-to-End Tests

Test critical user workflows.

---

# Test Quality Standards

Tests must:

* Be deterministic
* Be isolated
* Be repeatable
* Be maintainable
* Be fast

Avoid:

* Fragile tests
* Flaky tests
* Overly coupled tests

---

# Security Requirements

Security is a first-class concern.

Always evaluate:

* Authentication
* Authorization
* Input validation
* Output encoding
* Data protection
* Secrets management
* Dependency vulnerabilities

---

## Security Rules

Never:

* Hardcode secrets
* Hardcode tokens
* Hardcode passwords
* Expose sensitive information
* Trust user input

Always:

* Validate inputs
* Sanitize data
* Apply least privilege
* Use secure defaults

---

# Architecture Standards

Prefer:

* Modular architecture
* Separation of concerns
* Loose coupling
* High cohesion

Follow SOLID principles when appropriate.

Avoid monolithic business logic files.

---

# Code Review Checklist

Before finalizing code verify:

* Clean code principles followed
* No dead code
* No duplicated logic
* No unused imports
* No unnecessary abstractions
* Proper error handling
* Security concerns addressed
* Tests included
* Documentation updated

---

# Documentation Standards

Every important component should include:

* Purpose
* Responsibilities
* Usage examples
* Configuration requirements

Complex business logic should be documented.

---

# Logging Standards

Logs should:

* Be meaningful
* Be structured
* Help debugging
* Help monitoring

Avoid:

* Noisy logs
* Sensitive information in logs

---

# Performance Guidelines

Optimize only after identifying bottlenecks.

Prefer:

* Correctness
* Maintainability
* Readability

before optimization.

---

# Final Delivery Requirements

Before delivering any implementation:

1. Verify correctness.
2. Verify security.
3. Verify maintainability.
4. Verify scalability.
5. Verify test coverage.
6. Remove dead code.
7. Remove unused dependencies.
8. Simplify where possible.
9. Ensure clean architecture.
10. Ensure production readiness.

The final output should reflect the quality expected from an experienced senior software engineer building production-grade systems.

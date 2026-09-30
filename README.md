# ENE-C2-034 — Power Grid Maintenance Work Order Generation & Safety Checklist Agent

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific job-to-be-done)
> **Industry**: ENE (Energy)

## Overview

Generates a compliant power grid outage work order (停電作業指示書) and a
work-type-specific safety checklist from a structured maintenance request
(equipment ID, location, work type, schedule, crew size). Retrieves
applicable 電気事業法 and 労働安全衛生法 requirements via vector search,
drafts the work order and safety checklist, validates mandatory fields and
citation accuracy, and assembles the final document. Primary users are grid
operations planners (authors) and safety officers / qualified electrical
engineers (approvers) at electric utilities and PPS. The agent does not
schedule crews, dispatch resources, or authorize work — a qualified
electrical engineer must review and approve every draft before work
commences.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency (`agenticstar-agentcore[openai,marketplace]==1.0.3`). |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/` for the design and the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner. Generated work orders are drafts only and must be
reviewed and approved by a qualified electrical engineer before any work commences.

---

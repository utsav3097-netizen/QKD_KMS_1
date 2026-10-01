# ETSI QKD 014 Key Management System (KMS)

A production-oriented cryptographic routing infrastructure that connects physical Quantum Key Distribution (QKD) hardware with external Secure Application Entities (SAEs), following the architecture and key-management concepts defined by the **ETSI GS QKD 014** interface standard.

This project was built as a full-stack engineering capstone, covering frontend development, asynchronous backend APIs, relational database design, schema migrations, concurrency control, validation, and structured security telemetry.

## Overview

Traditional public-key cryptography relies on mathematical problems such as integer factorization and discrete logarithms. Large-scale quantum computing is expected to threaten widely deployed public-key schemes, which is one reason quantum-safe key distribution technologies are being researched and developed.

Quantum Key Distribution (QKD) provides a mechanism for generating shared secret key material using quantum communication systems. A **Key Management System (KMS)** acts as the software layer between QKD hardware and applications that need cryptographic keys.

This implementation focuses on the KMS side of that workflow:

1. QKD hardware supplies raw key material to the KMS.
2. The KMS validates and stores the key material.
3. External Secure Application Entities (SAEs) request keys through the API.
4. The KMS reserves an available key for the requesting SAE.
5. Once the key is consumed, it is permanently marked as used and cannot be reused.

## Project Goals

The system was designed to demonstrate how a telecommunications-oriented service can be implemented using modern full-stack engineering practices.

Key goals include:

- Implement a clear QKD key lifecycle.
- Prevent duplicate key allocation under concurrent requests.
- Keep database schema changes version-controlled and reproducible.
- Expose asynchronous REST APIs through FastAPI.
- Validate incoming and outgoing data using Pydantic.
- Produce machine-readable security telemetry using structured JSON logging.
- Provide a web dashboard for monitoring the KMS key buffer and system state.

## Core Architecture

```text
                         QUANTUM KEY DISTRIBUTION
                         Physical QKD Hardware
                                  |
                                  | POST /keys
                                  v
                    +-----------------------------+
                    |          KMS SERVER          |
                    |-----------------------------|
                    | FastAPI                      |
                    | Pydantic validation          |
                    | Key lifecycle management     |
                    | Concurrency-safe allocation   |
                    | Structured audit telemetry    |
                    +-------------+---------------+
                                  |
                    +-------------+-------------+
                    |                           |
             POST /enc_keys                POST /consume
                    |                           |
                    v                           v
              Secure Application Entity (SAE)
                    |
                    v
               Network / Encryption Layer
```

## Key Lifecycle

Each key follows a controlled state transition model.

```text
AVAILABLE  -->  RESERVED  -->  CONSUMED
```

### AVAILABLE

A key is received from the QKD source, validated, assigned a globally unique identifier, and placed in the KMS buffer.

### RESERVED

When an SAE requests key material, the KMS atomically selects an available key and associates it with the requesting SAE.

### CONSUMED

After the key is used by the application workflow, it is permanently marked as consumed. Consumed keys are not returned to the available pool and are not eligible for reuse.

## Engineering Highlights

### 1. Cryptographic Key State Management

The KMS models key usage as an explicit state machine rather than treating keys as simple records.

Each stored key includes identifiers and lifecycle information that allow the service to track ownership and consumption safely.

A typical key record contains:

- A unique `key_id` based on UUIDv4.
- Key material represented as 256-bit hexadecimal entropy.
- Current lifecycle state.
- The associated SAE identifier when reserved.
- Creation and state-transition timestamps where applicable.

The state model makes key allocation behavior explicit and provides a foundation for auditing and operational monitoring.

### 2. Concurrency-Safe Key Allocation

One of the main engineering challenges in a KMS is preventing two concurrent requests from receiving the same key.

The allocation path uses PostgreSQL row-level locking with `SELECT ... FOR UPDATE SKIP LOCKED` inside a transaction.

Conceptually:

```sql
SELECT *
FROM qkd_keys
WHERE state = 'AVAILABLE'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

This allows concurrent workers to safely claim different available rows without waiting on rows that another transaction has already locked. The transaction then updates the selected key to `RESERVED` before committing.

The result is a database-backed allocation mechanism designed to avoid double assignment of the same key under concurrent requests.

### 3. Structured Security Telemetry

Instead of relying on unstructured console messages, the service uses `structlog` to emit JSON-formatted events.

Security-relevant events can include fields such as:

```json
{
  "event": "key_reserved",
  "timestamp": "2026-10-01T12:00:00Z",
  "key_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "sae_id": "sae-001"
}
```

Structured logs make the service easier to integrate with centralized observability and security platforms such as Splunk, Datadog, or other SIEM/log-analysis systems.

### 4. Version-Controlled Database Schema

Database schema evolution is handled through **Alembic** rather than application-startup table creation.

`create_all()` is intentionally disabled in the production-oriented workflow so that Alembic remains the authoritative mechanism for schema changes.

This provides:

- Version-controlled schema revisions.
- Reproducible database setup.
- Controlled changes to tables and PostgreSQL ENUM types.
- Safer deployment and rollback workflows.
- A clear separation between application code and database evolution.

A fresh environment can be rebuilt using:

```bash
alembic upgrade head
```

## API Responsibilities

The KMS exposes REST endpoints for the main stages of the key-management workflow.

| Endpoint | Purpose |
|---|---|
| `POST /keys` | Ingest key material from the QKD source and place it into the KMS buffer. |
| `POST /enc_keys` | Reserve key material for a requesting SAE. |
| `POST /consume` | Mark reserved key material as consumed. |
| `GET ...` | Monitor stored keys, state, or system information depending on the implemented route set. |

> Endpoint names and request/response schemas should be treated as implementation-specific and aligned with the exact API contract used by this repository.

## Full-Stack Implementation

This project covers the complete application stack rather than only the API layer.

### Frontend

The frontend uses **HTML5, CSS3, JavaScript, and React** to provide a dynamic monitoring dashboard.

The dashboard is designed to visualize information such as:

- Current key-buffer status.
- Key lifecycle states.
- Cryptographic key metadata.
- SAE associations.
- Real-time system activity.

### Backend

The backend is implemented with **FastAPI** and **Uvicorn**, providing an asynchronous REST API and the business logic responsible for key ingestion, reservation, consumption, and validation.

### Database

**PostgreSQL** stores key records and supports transactional concurrency control through row-level locking.

**SQLAlchemy** is used for ORM mapping and database interaction.

### Validation and Telemetry

- **Pydantic** handles schema validation and typed request/response models.
- **structlog** generates structured JSON security telemetry.
- **Alembic** manages version-controlled database migrations.

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | HTML5, CSS3, JavaScript | Web UI foundation and presentation |
| Frontend Framework | React.js | State-driven dashboard and API integration |
| Backend API | FastAPI | Asynchronous REST API and service logic |
| ASGI Server | Uvicorn | Application serving |
| Database | PostgreSQL | Relational storage and transactional locking |
| ORM | SQLAlchemy | Database models and persistence |
| Migrations | Alembic | Version-controlled schema evolution |
| Validation | Pydantic | Request and response validation |
| Telemetry | structlog | Structured JSON audit logging |

## Example Workflow

A simplified end-to-end flow looks like this:

```text
1. QKD hardware generates key material
               |
               v
2. KMS receives the key through POST /keys
               |
               v
3. Key is stored as AVAILABLE
               |
               v
4. SAE requests encryption key material
               |
               v
5. KMS atomically reserves one AVAILABLE key
               |
               v
6. Key state becomes RESERVED
               |
               v
7. Encryption workflow completes
               |
               v
8. KMS marks the key as CONSUMED
               |
               v
9. Structured audit event is emitted
```

## Database Migration Workflow

Alembic is used as the source of truth for schema changes.

Create a new migration:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Review the generated revision, then apply migrations:

```bash
alembic upgrade head
```

To inspect the current migration state:

```bash
alembic current
```

To view available revision history:

```bash
alembic history
```

## Local Development

### Prerequisites

Make sure the development environment includes:

- Python 3.10+
- PostgreSQL
- Node.js and npm
- Git

### Backend Setup

```bash
git clone <your-repository-url>
cd <your-project-directory>

python -m venv myenv
```

Activate the virtual environment on Windows:

```bash
myenv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Configure the PostgreSQL connection using the environment variables expected by the application.

Run database migrations:

```bash
alembic upgrade head
```

Start the FastAPI application:

```bash
uvicorn main:app --reload
```

The interactive API documentation is available through FastAPI's generated documentation at:

```text
http://127.0.0.1:8000/docs
```

### Frontend Setup

From the frontend directory:

```bash
npm install
npm start
```

The frontend then communicates with the FastAPI service through the configured API/proxy settings.

## Project Structure

A typical repository layout for the system is:

```text
.
├── alembic/
│   ├── versions/
│   └── env.py
├── frontend/
├── main.py
├── database.py
├── database_models.py
├── models.py
├── alembic.ini
├── requirements.txt
└── README.md
```

> Adjust the tree above to match the exact files and folders in the repository if additional modules have been added.

## Security Considerations

This project is intended as an engineering implementation and learning platform for QKD key-management concepts. A production telecom deployment would require additional controls beyond the core application logic, including authenticated and mutually authenticated interfaces, secure secret handling, transport protection, hardened infrastructure, key provenance, access control, comprehensive testing, and operational monitoring.

The system should also be reviewed against the exact version of the applicable ETSI specification and the requirements of the target deployment before being used in a real security-critical environment.

## What This Project Demonstrates

The project brings together several areas of software engineering in one system:

- REST API design with FastAPI.
- Asynchronous backend development.
- Relational modeling with PostgreSQL and SQLAlchemy.
- Transactional concurrency control.
- Version-controlled schema migrations with Alembic.
- Strict validation with Pydantic.
- Structured security logging with structlog.
- React-based frontend development.
- Backend-to-frontend API integration.
- State-driven visualization of cryptographic resources.

## Future Work

Potential next steps include:

- Stronger authentication and authorization for SAEs and management APIs.
- Automated unit, integration, and concurrency testing.
- Containerized deployment with Docker.
- Production configuration and secrets management.
- Metrics and distributed observability.
- Improved fault recovery and transaction handling.
- API hardening, rate limiting, and audit-trail retention policies.
- Closer validation against ETSI QKD 014 interoperability requirements.
- Deployment automation and CI/CD.

## Disclaimer

This repository is an engineering project and should not be treated as a certified telecommunications or cryptographic product. Conformance to ETSI QKD 014 requires verification against the applicable specification version, interoperability requirements, security controls, and deployment environment.


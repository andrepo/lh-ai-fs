# Production Readiness Plan

## Scenario

Assume BS Detector is moving from a prototype to a paid MVP for law firms and legal teams.

- Users upload litigation documents and request verification reports.
- A single matter may contain dozens to hundreds of documents (robust and scalable storage and indexing is a must).
- The system needs to support different law firms with multiple users, each with different permissions.
- Law firms (tenants) must be isolated from one another - in special the documents can't leak out to other firms. We need to make sure AI agents are restricted to just the given tenant's documents.
- Analyses may take minutes and may involve multiple model calls, retrieval steps, citation checks, and cross-document consistency checks.
- Customers expect status updates, auditability, and reliable handling of long-running jobs.
- Usage can spike: assume many simultaneous users at launch (Queue management is a must).
- Legal data may be confidential, privileged, or otherwise sensitive. We need to handle this properly in the sytem (upload, storage, retrieval).
- Given the the prototype currently doesn't consider OCR I pondered whether I should include it in the production readiness plan or not. I decided to include it because it's a common requirement for legal documents. In real-world litigation, the documents uploaded (police reports, medical records, handwritten witness statements) are almost always scanned PDFs. Without some form of OCR, the product will completely fail on these documents. This is a major risk for a paid MVP.
- Caching to improve performance and reduce token usage and cost.

## Architecture

I opted for AWS as the cloud provider due to its maturity, scalability, flexibility and familiarity to many developers and also for supporting all of the cloud services I need for this MVP.

```text
[User Browser] ------( Direct Upload / Presigned URL )-------> [ S3 Private Buckets ]
      |                                                             ^
      |                                                             |
      v                                                             | (Read/Write Docs)
[ FastAPI Web Server ]                                              |
      |                                                             |
      +-----( SQL + RLS )------------> [ PostgreSQL + pgvector ]    |
      |                                      ^                      |
      |                                      | (Vector Search)      |
      +-----( Enqueue Job )---------> [ AWS SQS Queue ]             |
                                             |                      |
                                             | (Poll Jobs)          |
                                             v                      |
                                     [ ECS Worker Tasks ] ----------+
                                             |                      
                                             +---( Cache )----------> [ Redis Cache ]
                                             |
                                             +---( Model Calls )----> [ OpenAI API / LLM ]
```

### Storage

S3 for object storage (documents, OCR'd text, intermediate results)
- private object store
- isolated per tenant (s3://tenant-{org_id}...)

#### Trade-off: pgvector/Pinecone vs. AWS Bedrock Knowledge Bases

We evaluated AWS Bedrock Knowledge Bases to offload RAG orchestration. However, we rejected it for the MVP due to:
**1.** Cost: The default OpenSearch Serverless backend incurs a high fixed cost (~$700/mo), which contradicts our goal of keeping MVP overhead low.
**2.** Isolation: Relational database security (Postgres RLS) provides much stronger, auditable tenant isolation guarantees required by legal clients than metadata filtering on a shared managed search index. 

I would choose a custom chunking pipeline on ECS/Cloud Run workers, storing embeddings in Postgres pgvector / Pinecone Serverless, keeping fixed costs near zero.

### Multi-Tenant Data Isolation

To prevent any data leakage between different law firms, we isolate tenant data at three boundaries:

**1. Document Storage (S3):** Files are stored using tenant-prefixed paths (e.g., `s3://tenant-{org_id}/matter-{matter_id}/...`).

**2. Database Security (PostgreSQL RLS):** We use PostgreSQL Row-Level Security (RLS). Every table (matters, jobs, reports, chunks) contains an `org_id` column. PostgreSQL automatically filters all select/update/delete operations to match the authenticated user's `org_id`.

**3. Agent/Vector Isolation:** When workers query the vector database for RAG, the query is strictly scoped using metadata filters: `{ "org_id": current_org_id, "matter_id": current_matter_id }`.

### Queue (handling concurrent users)

AWS SQS (Simple Queue Service) for queueing jobs (OCR tasks, analysis tasks).

This will require a worker.py to be added to the current backend directory to pull messages from the SQS queue and process them. The worker.py will need to use the same agents and prompts as the API (import - DRY), but with proper error handling. If it fails, the job should be retried a few times before giving up.

For scalability, I suggest a creating a new Docker image for the worker.py and deploy it on ECS/Cloud Run, but keeping the API on FastAPI.

### Orchestration

Now that I decided to include OCR in the pipeline and that we are dealing with potentially hundreds of large documents, I would implement the following orchestration strategy and include RAG:

**1. OCR:** PDF/Images to text

**2. Embeddings + Chunking:** Chunk the extracted text and index it

**3. Extraction:** Run the extractor_agent gainst the submitted MSJ to extract all citations

**4. RAG + Verification:** to avoind running into issues with the LLM context size, we use RAG to retrieve only the relevant passages (evidence) for each assertion

**5. Synthesis:** Merges the findings into the final report

### Caching Strategy

To optimize latency and keep LLM/infra costs low, I would implement caching at three levels:

**1. OCR / Text Cache:** Compute a SHA-256 hash of every uploaded file. If the file hash exists, skip OCR and load the text from S3.

**2. LLM Prompt Caching:** Structuring our agent prompts to take advantage of LLM provider-level prompt caching, reducing input token costs for large documents.

**3. Report Caching:** Cache final compiled reports in Redis to ensure instant frontend rendering on reload.

### Security & Privacy

I would implement the following security measures:

**1. Transparent Storage Encryption:** Encrypt S3 buckets and RDS PostgreSQL databases at rest using cloud-managed encryption (SSE-S3 and AWS RDS Storage Encryption).

**2. Access control:** Implement strict access control using RBAC.

## User Flow & State Tracking

We need to address the UI and how data flows thru the system now that the prototype is evolving to include RAG, OCR and hundreds of large files.

Here's the proposed UI and data flow:

- User logs in, creates a new matter
- User uploads files
- User clicks on submit -> job is created in the database (Postgres) for tracking and pushed to the execution queue (AWS SQS).
- User gets redirected to a dashboard showing the state of each submitted job (postgres db)
    - For each we show: 
        - Status (QUEUED, PROCESSING, DONE, FAILED, etc.)
        - Progress bar (based on completed steps)
        - Last updated timestamp
    - The user can click on the job to view the report when it's done

## Roadmap

**1. Multi-tenant:** 

Given this is critical and sensitive change, I would implement this first.

**2. Core Async / Queue / UX:** 

Build the SQS queue and the backend worker (worker.py) running our existing agent prototype. Keep using digital PDFs and full-text context first to ensure the async flow works.
This includes the UX changes mentioned above, to allow users to track their jobs.

**3. Hardening:** 

Implement full database/S3 encryption-at-rest keys, Postgres RLS policies, and team permissions.

**4. RAG & OCR:** 

Integrate AWS Textract/Document AI for scanned PDFs and implement pgvector/RAG search so the agents can handle larger matters.

**5. AIKIDO / Audit:** 

I would run and address vulnerabilities in the system before deploying to production. 

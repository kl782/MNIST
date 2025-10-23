# Cloud Architecture Documentation

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT APPLICATION                        │
│                    (Your Frontend/Form)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS POST
                             │ (company data + files)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PAPERSPACE DEPLOYMENT                         │
│                   (webhook_server_cloud.py)                      │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. Receive webhook request                             │     │
│  │ 2. Save to /outputs/{company_slug}/                    │     │
│  │ 3. Download Google Drive files (if provided)           │     │
│  │ 4. Trigger Paperspace Workflow                         │     │
│  │ 5. Return confirmation code                            │     │
│  └────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────┘
                             │ Gradient API
                             │ (trigger workflow)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PAPERSPACE WORKFLOW                            │
│                  (pipeline-workflow.yaml)                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   JOB 1:     │  │   JOB 2:     │  │   JOB 3:     │         │
│  │    Setup     │─▶│Vector Store  │─▶│   Pipeline   │         │
│  │              │  │              │  │              │         │
│  │ • Clone repo │  │ • Preprocess │  │ • Part A     │         │
│  │ • Download   │  │ • Upload to  │  │ • Part B     │         │
│  │   Drive      │  │   OpenAI     │  │ • Consolidate│         │
│  └──────────────┘  └──────────────┘  └──────┬───────┘         │
│                                              │                  │
│                                              ▼                  │
│                                       ┌──────────────┐          │
│                                       │   JOB 4:     │          │
│                                       │   Upload     │          │
│                                       │              │          │
│                                       │ • Send to    │          │
│                                       │   Drive      │          │
│                                       └──────┬───────┘          │
└───────────────────────────────────────────────┼──────────────────┘
                                                │
                                                ▼
                                    ┌─────────────────────┐
                                    │  GOOGLE DRIVE       │
                                    │  Final Report 📄    │
                                    └─────────────────────┘
```

## 📦 Component Details

### 1. Webhook Server (Always-On Deployment)

**File:** `paperspace/webhook_server_cloud.py`

**Instance Type:** C5 (CPU, 2 vCPU, 8GB RAM)

**Responsibilities:**
- Receive POST requests from clients
- Parse company data and files
- Save submissions to persistent storage
- Download Google Drive files
- Trigger pipeline workflows
- Return immediate confirmation

**Endpoints:**
- `GET /health` - Health check
- `GET /test` - Test endpoint
- `POST /` - Main webhook endpoint
- `GET /storage/{company_slug}` - Storage stats

**Storage:**
```
/outputs/
├── logs/
│   └── webhook_server_TIMESTAMP.log
└── {company_slug}/
    ├── debug/
    │   └── submission_TIMESTAMP.json
    └── data/
        ├── uploaded_file1.pdf
        └── downloaded_from_drive.txt
```

### 2. Pipeline Workflow (On-Demand Jobs)

**File:** `paperspace/workflows/pipeline-workflow.yaml`

#### Job 1: Setup (C5 Instance)

**Duration:** ~5 minutes  
**Cost:** ~$0.01

```
Responsibilities:
├── Clone GitHub repository
├── Download Google Drive files
├── Create company_info.json
└── Output: company-data volume
```

#### Job 2: Vector Store (C7 Instance)

**Duration:** ~3 minutes  
**Cost:** ~$0.01

```
Responsibilities:
├── Load company data
├── Convert CSV → JSON
├── Upload to OpenAI vector store
└── Output: vector-id volume
```

#### Job 3: Pipeline (P4000 GPU Instance)

**Duration:** ~45 minutes  
**Cost:** ~$0.38

```
Responsibilities:
├── Install AI dependencies
├── Load vector store ID
├── Run pipeline_cloud.py
│   ├── Part A: Initial analysis
│   ├── Quotes extraction
│   ├── Part B: Use cases generation
│   └── Consolidation: Final report
└── Output: final-reports dataset
```

#### Job 4: Upload (C5 Instance)

**Duration:** ~2 minutes  
**Cost:** ~$0.01

```
Responsibilities:
├── Find latest final report
├── Upload to Google Drive
└── Complete workflow
```

## 🔄 Data Flow

### Input Flow (Client → Pipeline)

```
Client Submission
    │
    ├─► company_name ────────────► Used for directory naming
    ├─► company_description ─────► Passed to pipeline
    ├─► use_cases_count ─────────► Controls generation
    ├─► readiness_score ─────────► Context for analysis
    ├─► google_drive_link ───────► Downloaded files
    └─► uploaded_files ──────────► Saved to data/

           ↓ (stored in)

/outputs/{company_slug}/
    ├── data/
    │   ├── {uploaded files}
    │   └── {downloaded from Drive}
    └── debug/
        └── submission_{timestamp}.json

           ↓ (processed by)

Pipeline Jobs
    ├── Setup: Prepares environment
    ├── Vector Store: Creates embeddings
    ├── Pipeline: Generates insights
    └── Upload: Delivers final report

           ↓ (results in)

/outputs/{company_slug}/final/
    └── FINAL_REPORT_{timestamp}.md

           ↓ (uploaded to)

Google Drive
    └── Final Reports Folder/
        └── FINAL_REPORT_{company_slug}_{timestamp}.md
```

### Log Flow (Pipeline → Monitoring)

```
Python Code
    │
    └─► logger.info("message", key=value)
           │
           ├─► JSON Formatter
           │      │
           │      └─► {"timestamp":"...","level":"INFO","message":"...","key":"value"}
           │
           ├─► stdout (captured by Paperspace)
           │      │
           │      └─► Paperspace Logs UI
           │
           └─► File Handler
                  │
                  └─► /outputs/logs/pipeline_TIMESTAMP.log
                         │
                         └─► Persistent storage
```

## 🗄️ Storage Architecture

### Persistent Volumes

```
Volume: webhook-storage (10GB)
Mount: /outputs
Lifecycle: Persistent across deployments

/outputs/
├── logs/                           # All service logs
│   ├── webhook_server_*.log
│   └── pipeline_*.log
│
├── company_a/                      # Isolated per company
│   ├── debug/
│   ├── data/
│   ├── vector_ids/
│   ├── part_a/
│   ├── part_b/
│   └── final/
│
├── company_b/
│   └── [same structure]
│
└── company_c/
    └── [same structure]
```

### Ephemeral Storage

```
/tmp/                               # Temporary files
├── drive_download/                 # Downloaded Drive files (before move)
└── preprocessing/                  # Temporary processing files

Note: /tmp is cleared after job completion
```

## 🔐 Security Architecture

### Secrets Management

```
GitHub Secrets                      Paperspace Environment
─────────────                      ──────────────────────
PAPERSPACE_API_KEY    ────────►   Used by GitHub Actions
PAPERSPACE_PROJECT_ID ────────►   Used by GitHub Actions
OPENAI_API_KEY        ────────►   Injected as ENV var
GDRIVE_CREDENTIALS    ────────►   Mounted to /app/secrets/

                                   Container
                                   ─────────
                                   ENV: OPENAI_API_KEY
                                   FILE: /app/secrets/google_drive_credentials.json
```

### Network Security

```
Internet
    │
    └─► HTTPS only (Paperspace enforces TLS)
           │
           └─► Webhook Server
                  │
                  ├─► CORS: Configured origins only
                  ├─► Rate limiting: TBD
                  └─► Auth: Optional OPENAI_WEBHOOK_SECRET
```

## 📊 Monitoring & Observability

### Metrics Collected

```python
# Logged automatically by CloudLogger

logger.metric("upload_size", 1024, "KB")
# → {"metric_name":"upload_size","metric_value":1024,"metric_unit":"KB"}

logger.metric("use_cases_count", 7)
# → {"metric_name":"use_cases_count","metric_value":7}

logger.metric("pipeline_duration", 3600, "seconds")
# → {"metric_name":"pipeline_duration","metric_value":3600,"metric_unit":"seconds"}
```

### Log Aggregation

```
Source: Python code
    ↓
Stdout: JSON formatted
    ↓
Paperspace Logs: Real-time aggregation
    ↓
Retention: 30 days (Paperspace default)
    ↓
Export: Available via API or UI
```

## 🔁 Failure Handling

### Webhook Server Failures

```
Request arrives
    ↓
Try: Save submission
    ├─► Success: Continue
    └─► Failure: Log error, save to /outputs/error_*.json
           ↓
Try: Trigger workflow
    ├─► Success: Return confirmation code
    └─► Failure: Log error, return 500 (client can retry)
           ↓
Note: Submission is ALWAYS saved, even if workflow fails
```

### Pipeline Failures

```
Pipeline Job
    ↓
Try: Each step (with retries built-in)
    ├─► Success: Continue to next step
    └─► Failure: Log detailed error
           ↓
           ├─► Transient error (e.g., API timeout)
           │      ├─► Retry 2 more times
           │      └─► If all fail: Mark job failed
           │
           └─► Permanent error (e.g., missing file)
                  └─► Mark job failed immediately

Result: Workflow run marked as failed in Paperspace
    ↓
Notification: Email/Slack (if configured)
    ↓
Manual intervention: Review logs, fix issue, re-trigger
```

## 🚀 Scaling Strategy

### Horizontal Scaling (Multiple Companies)

```
Webhook Server (1 instance)
    │
    ├─► Workflow Run 1 (Company A) ──► P4000 instance
    ├─► Workflow Run 2 (Company B) ──► P4000 instance
    ├─► Workflow Run 3 (Company C) ──► P4000 instance
    └─► Workflow Run N (Company N) ──► P4000 instance

Note: Unlimited parallel workflows, each isolated
```

### Vertical Scaling (Larger Companies)

```yaml
# In pipeline-workflow.yaml

jobs:
  pipeline:
    resources:
      # Small company (< 100 docs)
      instance-type: P4000
      
      # Medium company (100-500 docs)
      instance-type: P5000
      
      # Large company (500+ docs)
      instance-type: V100
```

## 💰 Cost Optimization

### Instance Selection Matrix

```
Task Type          CPU Need   GPU Need   Instance    Cost/hr
─────────────────  ─────────  ─────────  ──────────  ───────
File I/O           Low        None       C5          $0.09
Data processing    Medium     None       C7          $0.14
AI inference       High       Yes        P4000       $0.51
Large models       High       Yes (big)  V100        $2.30
```

### Cost Per Pipeline Run

```
Setup (C5, 5 min)          = $0.01
Vector Store (C7, 3 min)   = $0.01
Pipeline (P4000, 45 min)   = $0.38
Upload (C5, 2 min)         = $0.01
                           ─────
TOTAL                      = $0.41 per company

Monthly (100 companies)    = $41.00
Webhook (always-on C5)     = $6.48
                           ─────
TOTAL MONTHLY              = $47.48
```

## 🔮 Future Architecture Enhancements

### Phase 2: Caching

```
Vector Store Upload
    ↓
Check: Cache for similar companies
    ├─► Cache hit: Reuse vector store
    │      └─► Save: ~3 min, ~$0.01
    └─► Cache miss: Create new
           └─► Cost: Original
```

### Phase 3: Queue System

```
Webhook Server
    ↓
Save to Queue (Redis/SQS)
    ↓
Queue Worker (monitors queue)
    ├─► Available slot: Trigger workflow
    └─► Queue full: Wait and retry
           └─► Prevents overwhelming Paperspace
```

### Phase 4: Multi-Region

```
Client Location
    ├─► US East ──► Paperspace US East
    ├─► EU ───────► Paperspace EU
    └─► APAC ─────► Paperspace APAC

Benefits:
├─► Lower latency
├─► Compliance (data residency)
└─► High availability
```

## 📚 Reference

### Directory Structure Map

```
paperspace_pipeline/
├── paperspace/                     # Cloud-specific code
│   ├── webhook_server_cloud.py    # Webhook server
│   ├── pipeline_cloud.py          # Pipeline runner
│   ├── utils/
│   │   ├── cloud_logging.py       # Logging
│   │   └── cloud_storage.py       # Storage
│   ├── scripts/
│   │   ├── preprocess_data.py     # Preprocessing
│   │   └── download_gdrive.py     # Drive downloads
│   └── workflows/
│       ├── webhook-deployment.yaml # Deployment spec
│       └── pipeline-workflow.yaml  # Workflow spec
│
├── .github/workflows/
│   └── deploy-paperspace.yml      # CI/CD
│
├── webhook_server.py              # Original (local)
├── pipeline_minimal.py            # Original (local)
├── part_a/                        # Part A code
├── part_b/                        # Part B code
└── final_consolidation/           # Consolidation code
```

### API Reference

**Webhook Server Endpoints:**

```
GET /health
Response: {"status":"healthy","service":"webhook_server_cloud",...}

POST /
Body: {"company_name":"Acme","use_cases_count":7,...}
Response: {"status":"success","confirmation_code":"CONF_...",.. }

GET /storage/{company_slug}
Response: {"company":"acme","total_size_bytes":1024,...}
```

**Gradient API (used internally):**

```python
from gradient import WorkflowsClient

client = WorkflowsClient(api_key=API_KEY)
run = client.run_workflow(
    workflow_id=WORKFLOW_ID,
    inputs={"company_name": "Acme", ...}
)
```

---

**Last Updated:** October 23, 2025  
**Version:** 1.0  
**Maintained By:** AI Pipeline Team


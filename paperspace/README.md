# Paperspace Cloud Deployment Guide

This directory contains the cloud-compatible version of the AI pipeline, designed to run on Paperspace Workflows.

## ⚡ Quick Start

**Most users should use the Direct API approach** (no webhook server needed):

👉 **See [`DIRECT_API_GUIDE.md`](DIRECT_API_GUIDE.md)** for the simplest deployment (saves $6.48/month)

**Or continue reading for the full webhook server option.**

---

## 🏗️ Architecture Overview

### Two Deployment Options

#### Option 1: Direct API (Recommended) ⭐

```
Your App → Paperspace API → Workflow (4 jobs) → Final Report
```

- **Cost:** $0.41 per run (no always-on server)
- **Setup:** 5 minutes
- **See:** `DIRECT_API_GUIDE.md` and `client_examples/`

#### Option 2: Webhook Server (Optional)

```
Your App → Webhook Server → Paperspace Workflow → Final Report
```

- **Cost:** $0.41 per run + $6.48/month (server)
- **Use when:** You need custom preprocessing or file handling
- **See:** This README (below)

### Components

1. **Webhook Server** (`webhook_server_cloud.py`) - **OPTIONAL**
   - Receives webhook requests from external clients
   - Saves submission data to persistent storage
   - Triggers Paperspace Workflows for processing
   - No local dependencies (no terminal spawning, no ngrok)

2. **Cloud Pipeline** (`pipeline_cloud.py`)
   - Runs the full AI pipeline in cloud environment
   - Uses structured JSON logging for monitoring
   - Persistent storage in `/outputs` directory
   - Supports parallel processing of multiple companies

3. **Client Examples** (`client_examples/`) - **RECOMMENDED**
   - Direct API call examples (JavaScript, Python)
   - No webhook server needed
   - Saves $6.48/month

4. **Utilities**
   - `utils/cloud_logging.py`: Structured JSON logging
   - `utils/cloud_storage.py`: Persistent storage management
   - `scripts/preprocess_data.py`: Data preprocessing
   - `scripts/download_gdrive.py`: Google Drive downloads

### Key Differences from Local Version

| Feature | Local Version | Cloud Version |
|---------|---------------|---------------|
| **Process Management** | Terminal windows (osascript) | Background processes |
| **Networking** | ngrok tunnels | Paperspace routing |
| **Storage** | Local directories | `/outputs` persistent volumes |
| **Logging** | Console + file | Structured JSON to stdout |
| **Parallelization** | Port-based (3 max) | Workflow-based (unlimited) |

## 🚀 Deployment

### Prerequisites

1. **Paperspace Account**
   - Sign up at https://www.paperspace.com
   - Create a project
   - Get your API key

2. **Required Secrets** (Set in GitHub or Paperspace)
   ```bash
   PAPERSPACE_API_KEY=your_api_key
   PAPERSPACE_PROJECT_ID=your_project_id
   OPENAI_API_KEY=your_openai_key
   GDRIVE_CREDENTIALS_PATH=/app/secrets/google_drive_credentials.json
   GDRIVE_FINAL_REPORT_FOLDER=https://drive.google.com/drive/folders/...
   ```

3. **Google Drive Service Account**
   - Create a service account in Google Cloud Console
   - Download credentials JSON
   - Share your Drive folder with the service account email
   - Upload credentials to Paperspace Secrets

### Deployment Steps

#### Option 1: GitHub Actions (Recommended)

1. **Configure GitHub Secrets**
   ```
   Repository Settings > Secrets and variables > Actions
   Add:
   - PAPERSPACE_API_KEY
   - PAPERSPACE_PROJECT_ID
   - OPENAI_API_KEY
   - GDRIVE_FINAL_REPORT_FOLDER
   ```

2. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Deploy to Paperspace"
   git push origin main
   ```

3. **Automatic Deployment**
   - GitHub Actions will automatically deploy on push
   - Check Actions tab for deployment status
   - Webhook URL will be displayed in deployment logs

#### Option 2: Manual Deployment

1. **Install Gradient CLI**
   ```bash
   pip install gradient
   gradient apiKey YOUR_API_KEY
   ```

2. **Deploy Webhook Server**
   ```bash
   gradient deployments create \
     --name "ai-pipeline-webhook" \
     --projectId "YOUR_PROJECT_ID" \
     --spec paperspace/workflows/webhook-deployment.yaml
   ```

3. **Create Pipeline Workflow**
   ```bash
   gradient workflows create \
     --name "ai-pipeline-workflow" \
     --projectId "YOUR_PROJECT_ID" \
     --workflowSpec paperspace/workflows/pipeline-workflow.yaml
   ```

4. **Get Workflow ID**
   ```bash
   gradient workflows list --projectId "YOUR_PROJECT_ID"
   # Copy the workflow ID and set it as PAPERSPACE_WORKFLOW_ID
   ```

## 📊 Monitoring & Logging

### Viewing Logs

#### Via Paperspace Console
1. Go to https://console.paperspace.com
2. Navigate to your project
3. Select Deployments or Workflows
4. Click on running instance
5. View logs in real-time

#### Via Gradient CLI
```bash
# Webhook server logs
gradient deployments logs --deploymentId DEPLOYMENT_ID

# Workflow run logs
gradient workflows logs --workflowRunId RUN_ID
```

### Log Structure

Logs are output in JSON format for easy parsing:

```json
{
  "timestamp": "2025-10-23T12:34:56Z",
  "level": "INFO",
  "service": "pipeline",
  "company": "Acme Corp",
  "message": "[STEP 1/10] Uploading to vector store",
  "step": 1,
  "total_steps": 10
}
```

### Monitoring Metrics

Key metrics logged during pipeline execution:
- `upload_size`: Data upload size in KB
- `use_cases_count`: Number of use cases generated
- `part_a_length`: Part A draft length in characters
- `final_report_size`: Final report size in characters
- `pipeline_duration`: Total pipeline duration in seconds

## 💾 Persistent Storage

### Directory Structure

```
/outputs/
├── logs/                          # Service logs
│   ├── webhook_server_*.log
│   └── pipeline_*.log
└── {company_slug}/               # Per-company data
    ├── debug/                    # Webhook submissions
    │   └── submission_*.json
    ├── data/                     # Input files
    │   ├── document1.pdf
    │   └── document2.txt
    ├── vector_ids/               # Vector store IDs
    │   └── vector_*.json
    ├── part_a/                   # Part A drafts
    │   └── report_draft_*.md
    ├── part_b/                   # Part B reports
    │   └── report_enhanced_*.md
    └── final/                    # Final reports
        ├── FINAL_REPORT_*.md
        └── FINAL_REPORT_*.ready
```

### Accessing Storage

**During Development:**
```python
from paperspace.utils.cloud_storage import CloudStorage

storage = CloudStorage("Acme Corp")
print(storage.get_storage_stats())
```

**From Paperspace Console:**
1. Navigate to Datasets
2. Find your company's dataset
3. Download or browse files

## 🔄 Workflow Execution

### Triggering from Webhook

When a webhook is received:

1. **Webhook Server** (`webhook_server_cloud.py`)
   - Receives POST request
   - Extracts company data
   - Saves to persistent storage
   - Triggers Paperspace Workflow

2. **Workflow Jobs** (defined in `pipeline-workflow.yaml`)
   - **Job 1 - Setup**: Clone repo, download Drive files
   - **Job 2 - Vector Store**: Upload data to OpenAI
   - **Job 3 - Pipeline**: Run full AI pipeline
   - **Job 4 - Upload**: Upload final report to Drive

3. **Status Updates**
   - Each job logs progress to stdout
   - Metrics tracked for monitoring
   - Final report uploaded to Google Drive

### Manual Workflow Trigger

```bash
gradient workflows run \
  --workflowId "WORKFLOW_ID" \
  --inputs '{"company_name": "Acme Corp", "use_cases_count": "7"}'
```

## 🧪 Testing

### Test Webhook Locally

```bash
cd paperspace
python webhook_server_cloud.py
```

In another terminal:
```bash
curl -X POST http://localhost:8080/health
curl -X POST http://localhost:8080/test
```

### Test Pipeline Locally

```bash
python paperspace/pipeline_cloud.py "Test Company" \
  --company-info "Test company description" \
  --model-set gpt5 \
  --use-cases-count 3
```

### Test on Paperspace

```bash
# Deploy to staging
gradient deployments create \
  --name "webhook-test" \
  --projectId "YOUR_PROJECT_ID" \
  --spec paperspace/workflows/webhook-deployment.yaml

# Get deployment URL
gradient deployments list --projectId "YOUR_PROJECT_ID"

# Test webhook
curl -X POST https://YOUR_DEPLOYMENT_URL/health
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Webhook Not Receiving Requests
- Check deployment status: `gradient deployments list`
- Verify webhook URL is correct
- Check CORS configuration
- Review webhook logs

#### 2. Pipeline Fails to Start
- Verify PAPERSPACE_WORKFLOW_ID is set correctly
- Check workflow exists: `gradient workflows list`
- Ensure Gradient SDK is installed in webhook container
- Review webhook server logs

#### 3. Vector Store Upload Fails
- Verify OPENAI_API_KEY is set
- Check company data directory has files
- Ensure helper_vectorstoreupload.py is in repository
- Review upload logs

#### 4. Google Drive Download Fails
- Verify service account credentials are mounted
- Check credentials file path
- Ensure folder is shared with service account
- Review download logs

#### 5. Out of Memory Errors
- Increase instance type in workflow spec
- Change from C5 to C7 or P4000
- Monitor memory usage in Paperspace console

#### 6. Logs Not Appearing
- Ensure logging to stdout (not just files)
- Check JSON formatter is working
- Verify log level is set to INFO or DEBUG
- Wait for log aggregation (can take 30-60 seconds)

### Debug Mode

Enable verbose logging:

```python
# In webhook_server_cloud.py or pipeline_cloud.py
import os
os.environ["LOG_LEVEL"] = "DEBUG"
```

## 📈 Scaling

### Parallel Processing

The cloud architecture supports unlimited parallel processing:

1. **Webhook Server**: Single instance handles all requests
2. **Workflows**: Each company gets its own workflow run
3. **Resources**: Paperspace auto-scales instances

### Resource Allocation

Adjust instance types in `pipeline-workflow.yaml`:

```yaml
jobs:
  pipeline:
    resources:
      instance-type: P5000  # Faster GPU
```

Available instance types:
- `C5`, `C7`: CPU instances (cheap, for I/O tasks)
- `P4000`, `P5000`, `P6000`: GPU instances (for AI processing)
- `V100`, `A100`: High-end GPU (for large models)

### Cost Optimization

1. **Use CPU instances for non-AI tasks**
   - Setup job: C5 ($0.09/hr)
   - Vector store: C7 ($0.14/hr)

2. **Use GPU only for AI pipeline**
   - Pipeline job: P4000 ($0.51/hr)

3. **Set timeouts to prevent runaway costs**
   ```yaml
   timeout: 7200  # 2 hours max
   ```

## 🔐 Security

### Best Practices

1. **Never commit secrets**
   - Use Paperspace Secrets
   - Use GitHub Secrets
   - Use environment variables

2. **Service Account Permissions**
   - Grant minimum required permissions
   - Use separate service accounts for dev/prod
   - Regularly rotate credentials

3. **Webhook Authentication**
   - Set OPENAI_WEBHOOK_SECRET
   - Verify webhook signatures
   - Use HTTPS only

4. **Network Security**
   - Enable CORS only for trusted origins
   - Use rate limiting
   - Monitor for unusual traffic

## 📚 Additional Resources

- [Paperspace Documentation](https://docs.paperspace.com)
- [Gradient Workflows Guide](https://docs.paperspace.com/gradient/workflows/)
- [Gradient CLI Reference](https://docs.paperspace.com/gradient/cli/)
- [Google Drive API](https://developers.google.com/drive/api/guides/about-sdk)

## 🆘 Support

For issues or questions:

1. Check Paperspace community: https://community.paperspace.com
2. Review Paperspace status: https://status.paperspace.com
3. Contact Paperspace support: support@paperspace.com

## 📝 License

Same as parent project.


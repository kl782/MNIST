# Migration Guide: Local to Paperspace Cloud

This guide helps you migrate from the local webhook/pipeline setup to Paperspace cloud deployment.

## 📋 Pre-Migration Checklist

- [ ] Paperspace account created
- [ ] Project created in Paperspace
- [ ] API key obtained
- [ ] Google Drive service account configured
- [ ] All required secrets collected
- [ ] Code committed to GitHub repository
- [ ] GitHub Actions secrets configured

## 🔄 Migration Steps

### Step 1: Update Dependencies

Create `paperspace/requirements.txt`:

```bash
cd paperspace
cat > requirements.txt <<EOF
# Web server
flask==3.0.0
flask-cors==4.0.0
gunicorn==21.2.0
waitress==2.1.2

# OpenAI & AI
openai==1.12.0
anthropic==0.18.0

# Paperspace
gradient==2.0.6

# Google Drive
google-api-python-client==2.116.0
google-auth==2.27.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0

# Data processing
pandas==2.2.0
numpy==1.26.3

# Utilities
python-dotenv==1.0.1
requests==2.31.0
EOF
```

### Step 2: Environment Variable Mapping

Map your current environment variables to Paperspace:

| Local `.env` | Paperspace Secret | Notes |
|--------------|-------------------|-------|
| `OPENAI_API_KEY` | `OPENAI_API_KEY` | Same |
| `DEEP_RESEARCH_API_KEY` | `DEEP_RESEARCH_API_KEY` | Same |
| `GDRIVE_CREDENTIALS_PATH` | Mount as `/app/secrets/...` | Upload to Secrets |
| `GDRIVE_FINAL_REPORT_FOLDER` | `GDRIVE_FINAL_REPORT_FOLDER` | Same |
| N/A | `PAPERSPACE_API_KEY` | New - for webhook server |
| N/A | `PAPERSPACE_PROJECT_ID` | New - your project ID |
| N/A | `PAPERSPACE_WORKFLOW_ID` | New - created after first deploy |

### Step 3: Update Your Client/Frontend

Change webhook URL from local to cloud:

**Before (Local):**
```javascript
const WEBHOOK_URL = 'http://localhost:3000';
```

**After (Paperspace):**
```javascript
const WEBHOOK_URL = 'https://YOUR_DEPLOYMENT_URL.paperspace.com';
```

### Step 4: Test Migration

#### 4.1 Local Testing

First, test the cloud-compatible code locally:

```bash
# Terminal 1: Start webhook server
cd /path/to/paperspace_pipeline
python3 paperspace/webhook_server_cloud.py

# Terminal 2: Test endpoints
curl http://localhost:8080/health
curl -X POST http://localhost:8080/test

# Terminal 3: Test with sample data
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "company_description": "A test company",
    "use_cases_count": 3
  }'
```

#### 4.2 Deploy to Paperspace

```bash
# Install Gradient CLI
pip install gradient

# Configure
gradient apiKey YOUR_API_KEY

# Deploy webhook
gradient deployments create \
  --name "ai-pipeline-webhook" \
  --projectId "YOUR_PROJECT_ID" \
  --spec paperspace/workflows/webhook-deployment.yaml

# Create workflow
gradient workflows create \
  --name "ai-pipeline-workflow" \
  --projectId "YOUR_PROJECT_ID" \
  --workflowSpec paperspace/workflows/pipeline-workflow.yaml
```

#### 4.3 Test Cloud Deployment

```bash
# Get deployment URL
WEBHOOK_URL=$(gradient deployments list --projectId "YOUR_PROJECT_ID" --json | jq -r '.[0].endpoint')

# Test health
curl $WEBHOOK_URL/health

# Test with sample data
curl -X POST $WEBHOOK_URL/ \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Cloud Test Corp",
    "company_description": "Testing cloud deployment",
    "use_cases_count": 3
  }'
```

### Step 5: Monitor First Production Run

1. **Watch Webhook Logs**
   ```bash
   gradient deployments logs --deploymentId DEPLOYMENT_ID --follow
   ```

2. **Watch Workflow Logs**
   ```bash
   gradient workflows logs --workflowRunId RUN_ID --follow
   ```

3. **Check Storage**
   - Go to Paperspace Console
   - Navigate to Datasets
   - Verify company data is being saved

4. **Verify Final Report**
   - Check Google Drive for final report
   - Verify email notification (if configured)

## 🔀 Key Code Changes

### Webhook Server Changes

#### Before (Local - `webhook_server.py`):
```python
# Opens new terminal window
subprocess.Popen(
    terminal_cmd,
    env=env,
    cwd=os.getcwd()
)
```

#### After (Cloud - `webhook_server_cloud.py`):
```python
# Triggers Paperspace Workflow
client = WorkflowsClient(api_key=PAPERSPACE_API_KEY)
run = client.run_workflow(
    workflow_id=PAPERSPACE_WORKFLOW_ID,
    inputs=params
)
```

### Pipeline Changes

#### Before (Local - `pipeline_minimal.py`):
```python
# Starts ngrok tunnel
ngrok_process = subprocess.Popen(
    f"ngrok http {port}",
    shell=True,
    ...
)
```

#### After (Cloud - `pipeline_cloud.py`):
```python
# Uses Paperspace's built-in routing
# No ngrok needed - MCP URL is localhost within pod
mcp_url = f"http://localhost:{port}/sse"
```

### Logging Changes

#### Before (Local):
```python
# Console output with colors
print(f"{Colors.GREEN}✓ Success{Colors.ENDC}")
```

#### After (Cloud):
```python
# Structured JSON logging
logger.success("Success", status="completed", duration_sec=123)
# Output: {"timestamp":"2025-10-23T12:34:56Z","level":"INFO","message":"✓ Success",...}
```

### Storage Changes

#### Before (Local):
```python
# Direct file system access
company_folder = Path(f"start_here/{company_name}")
company_folder.mkdir(parents=True, exist_ok=True)
```

#### After (Cloud):
```python
# Cloud storage manager
storage = CloudStorage(company_name)
storage.save_uploaded_file(content, filename)
# Automatically uses /outputs/company_slug/data/
```

## 🐛 Common Migration Issues

### Issue 1: "Module not found" errors

**Cause:** Dependencies not installed in cloud environment

**Solution:** Add to `requirements.txt` and redeploy

```bash
# Check what's missing
grep "import" paperspace/*.py | grep -v "^#" | sort | uniq

# Add to requirements.txt
echo "missing-package==1.0.0" >> paperspace/requirements.txt
```

### Issue 2: File paths don't work

**Cause:** Hardcoded local paths

**Solution:** Use cloud storage manager or environment variables

```python
# Bad
data_dir = "/Users/kristi/data"

# Good
from paperspace.utils.cloud_storage import CloudStorage
storage = CloudStorage(company_name)
data_dir = storage.get_company_data_dir()
```

### Issue 3: Environment variables not set

**Cause:** Missing secrets in Paperspace

**Solution:** Add secrets via CLI or Console

```bash
# Via CLI
gradient secrets create \
  --name "OPENAI_API_KEY" \
  --value "sk-..." \
  --projectId "YOUR_PROJECT_ID"

# Then reference in deployment spec
env:
  - name: OPENAI_API_KEY
    value: ${OPENAI_API_KEY}
```

### Issue 4: Logs not visible

**Cause:** Logging to files instead of stdout

**Solution:** Use cloud logger

```python
# Bad
with open("debug.log", "a") as f:
    f.write("Debug info")

# Good
from paperspace.utils.cloud_logging import create_logger
logger = create_logger("my_service")
logger.debug("Debug info")
```

### Issue 5: Google Drive download fails

**Cause:** Service account not shared with folder

**Solution:** 
1. Get service account email from credentials JSON
2. Share Google Drive folder with that email
3. Grant "Editor" permissions

```bash
# Get service account email
cat google_drive_credentials.json | jq -r '.client_email'
# Output: your-service-account@project.iam.gserviceaccount.com

# Share folder with this email in Google Drive UI
```

## 📊 Performance Comparison

| Metric | Local | Paperspace Cloud | Improvement |
|--------|-------|------------------|-------------|
| **Setup Time** | Manual (5-10 min) | Automated (30 sec) | 10-20x faster |
| **Parallelization** | 3 companies max | Unlimited | ∞ |
| **Reliability** | Requires computer on | 24/7 availability | 100% uptime |
| **Logs** | Console only | Persistent + searchable | Better debugging |
| **Scaling** | Manual port allocation | Auto-scaling | Effortless |
| **Cost** | Local compute | Pay-per-use | More economical |

## ✅ Post-Migration Checklist

- [ ] Webhook URL updated in client application
- [ ] Test submission processed successfully
- [ ] Logs are visible in Paperspace console
- [ ] Final report appears in Google Drive
- [ ] Email notifications working (if configured)
- [ ] Monitoring dashboard set up
- [ ] Alert rules configured
- [ ] Documentation updated
- [ ] Team trained on new system
- [ ] Old local server decommissioned

## 🎯 Next Steps

1. **Set up monitoring**
   - Configure alerts for failures
   - Set up log aggregation
   - Create dashboards

2. **Optimize costs**
   - Review instance types
   - Set appropriate timeouts
   - Enable auto-shutdown

3. **Improve reliability**
   - Add retry logic
   - Implement health checks
   - Set up backup workflows

4. **Scale**
   - Add more workers if needed
   - Optimize pipeline steps
   - Cache vector stores

## 🆘 Rollback Plan

If migration fails, you can quickly rollback:

1. **Revert client webhook URL** to local
2. **Restart local webhook server**
   ```bash
   cd /path/to/paperspace_pipeline
   python3 webhook_server.py
   ```
3. **Restart local ngrok**
   ```bash
   ./start_mcp.sh
   ```
4. **Debug cloud issues** without pressure
5. **Try migration again** when ready

---

**Remember:** Take it slow, test thoroughly, and don't hesitate to rollback if needed. The local system will continue working while you iron out cloud deployment issues.


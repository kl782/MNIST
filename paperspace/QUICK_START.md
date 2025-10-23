# Quick Start Guide

Get your AI pipeline running on Paperspace in under 30 minutes!

## ⚡ TL;DR

```bash
# 1. Install Gradient CLI
pip install gradient

# 2. Configure
gradient apiKey YOUR_API_KEY

# 3. Deploy
gradient deployments create \
  --name "ai-pipeline-webhook" \
  --projectId "YOUR_PROJECT_ID" \
  --spec paperspace/workflows/webhook-deployment.yaml

gradient workflows create \
  --name "ai-pipeline-workflow" \
  --projectId "YOUR_PROJECT_ID" \
  --workflowSpec paperspace/workflows/pipeline-workflow.yaml

# 4. Test
curl https://YOUR_DEPLOYMENT_URL/health
```

## 📝 Detailed Steps

### 1. Get Paperspace Account (5 minutes)

1. Go to https://console.paperspace.com
2. Sign up or log in
3. Create a new project
4. Note your **Project ID**
5. Go to Settings > API Keys
6. Create new API key
7. Copy the **API Key**

### 2. Prepare Secrets (10 minutes)

You need these secrets:

```bash
# Required
PAPERSPACE_API_KEY=ps_...           # From step 1
PAPERSPACE_PROJECT_ID=pr...         # From step 1
OPENAI_API_KEY=sk-...               # Your OpenAI key

# Optional (for Google Drive)
GDRIVE_CREDENTIALS_PATH=/app/secrets/google_drive_credentials.json
GDRIVE_FINAL_REPORT_FOLDER=https://drive.google.com/drive/folders/...
```

**Set them in GitHub Secrets:**
1. Go to GitHub repo > Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Add each secret

### 3. Push to GitHub (2 minutes)

```bash
git add .
git commit -m "Add Paperspace deployment"
git push origin main
```

GitHub Actions will automatically deploy! 🎉

### 4. Get Deployment URL (3 minutes)

#### Option A: From GitHub Actions

1. Go to Actions tab
2. Click latest workflow run
3. Look for "Deploy Webhook Server" job
4. Find the deployment URL in logs

#### Option B: From CLI

```bash
gradient deployments list --projectId "YOUR_PROJECT_ID" --json | jq -r '.[0].endpoint'
```

### 5. Test It! (5 minutes)

```bash
# Health check
curl https://YOUR_DEPLOYMENT_URL/health

# Test endpoint
curl -X POST https://YOUR_DEPLOYMENT_URL/test

# Real submission
curl -X POST https://YOUR_DEPLOYMENT_URL/ \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "company_description": "A test company for validation",
    "overall_readiness_score": 75,
    "readiness_category": "Adopter",
    "use_cases_count": 5,
    "report_expectations": "Generate comprehensive AI readiness report"
  }'
```

### 6. Monitor Execution (5 minutes)

```bash
# Watch webhook logs
DEPLOYMENT_ID=$(gradient deployments list --projectId "YOUR_PROJECT_ID" --json | jq -r '.[0].id')
gradient deployments logs --deploymentId $DEPLOYMENT_ID --follow

# Watch workflow
gradient workflows runs list --workflowId "YOUR_WORKFLOW_ID"
gradient workflows logs --workflowRunId "RUN_ID" --follow
```

## 🎯 What Happens Next?

1. **Webhook receives request** → Saves data to `/outputs`
2. **Workflow triggered** → 4 jobs run in sequence:
   - **Setup**: Downloads your data
   - **Vector Store**: Uploads to OpenAI
   - **Pipeline**: Runs AI analysis (20-60 min)
   - **Upload**: Sends report to Google Drive
3. **Final report** → Appears in your Google Drive folder

## 🔍 Troubleshooting

### "Deployment failed"
- Check your secrets are set correctly
- Verify Paperspace project ID is correct
- Review deployment logs for specific error

### "Workflow not triggering"
- Ensure `PAPERSPACE_WORKFLOW_ID` secret is set
- Check webhook logs for errors
- Verify Gradient SDK is installed (it's in requirements.txt)

### "Pipeline takes too long"
- Expected: 20-60 minutes for full pipeline
- Check instance type (P4000 recommended)
- Review logs for hanging steps

### "No final report"
- Check Google Drive folder permissions
- Verify service account has access
- Review upload job logs

## 📚 Next Steps

Once it's working:

1. **Update your client app** with new webhook URL
2. **Set up monitoring** (see README.md)
3. **Configure alerts** for failures
4. **Optimize costs** by adjusting instance types
5. **Read full documentation** for advanced features

## 🆘 Need Help?

- **Logs not appearing?** → Wait 60 seconds, Paperspace aggregates logs
- **API errors?** → Check your OpenAI API key has credits
- **Storage errors?** → Verify `/outputs` volume is mounted
- **Still stuck?** → Check [README.md](README.md) or [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

---

**Estimated total time: 30 minutes** ⏱️  
**Difficulty: Beginner** 🟢  
**Cost: ~$1-3 per pipeline run** 💰


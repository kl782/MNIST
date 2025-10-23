# Direct API Integration Guide

**Skip the webhook server entirely!** Trigger your AI pipeline directly from your application using the Paperspace API.

## 🎯 Architecture Comparison

### Before (With Webhook Server)
```
Client → Webhook Server ($6.48/mo) → Paperspace Workflow → Final Report
         └── Always running
         └── Extra hop
```

### After (Direct API)
```
Client → Paperspace Workflow → Final Report
         └── No extra cost
         └── Direct connection
```

**Savings: $6.48/month + simpler architecture!**

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Get Your Credentials

**You need TWO things** (both different!):

1. **API Key** (starts with `ps_...`)
   - Go to https://console.paperspace.com
   - Click profile → Team Settings → API Keys
   - Create new key or copy existing
   - Example: `ps_abc123def456...`

2. **Workflow ID** (starts with `wf_...`)
   - Deploy the workflow first (see below)
   - Or get from: `gradient workflows list --projectId YOUR_PROJECT_ID`
   - Example: `wf_xyz789abc123...`

**Note:** Your Project ID (`prjyqfzasih`) is different from both of these!

### Step 2: Deploy the Workflow (One-Time Setup)

```bash
# Install Gradient CLI
pip install gradient

# Set your API key
gradient apiKey YOUR_API_KEY

# Deploy the workflow
gradient workflows create \
  --name "ai-pipeline-workflow" \
  --projectId "YOUR_PROJECT_ID" \
  --workflowSpec paperspace/workflows/pipeline-workflow.yaml

# Copy the workflow ID from the output (starts with wf_...)
```

### Step 3: Call from Your App

**JavaScript:**
```javascript
const response = await fetch('https://api.paperspace.io/v1/workflows/runs', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${process.env.PAPERSPACE_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    workflowId: process.env.PAPERSPACE_WORKFLOW_ID,
    inputs: {
      company_name: 'Acme Corporation',
      use_cases_count: '7',
      company_description: 'A leading tech company',
      readiness_score: '75',
      google_drive_link: 'https://drive.google.com/drive/folders/...',
    },
  }),
});

const result = await response.json();
console.log('Pipeline started:', result.id);
```

**Python:**
```python
import requests

response = requests.post(
    'https://api.paperspace.io/v1/workflows/runs',
    headers={
        'Authorization': f'Bearer {os.environ["PAPERSPACE_API_KEY"]}',
        'Content-Type': 'application/json',
    },
    json={
        'workflowId': os.environ['PAPERSPACE_WORKFLOW_ID'],
        'inputs': {
            'company_name': 'Acme Corporation',
            'use_cases_count': '7',
            'company_description': 'A leading tech company',
            'readiness_score': '75',
            'google_drive_link': 'https://drive.google.com/drive/folders/...',
        },
    }
)

result = response.json()
print('Pipeline started:', result['id'])
```

**cURL:**
```bash
curl -X POST https://api.paperspace.io/v1/workflows/runs \
  -H "Authorization: Bearer $PAPERSPACE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflowId": "'$PAPERSPACE_WORKFLOW_ID'",
    "inputs": {
      "company_name": "Acme Corporation",
      "use_cases_count": "7",
      "company_description": "A leading tech company",
      "readiness_score": "75"
    }
  }'
```

---

## 📋 Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `company_name` | ✅ Yes | - | Company name |
| `company_slug` | No | Auto-generated | Filesystem-safe slug |
| `use_cases_count` | No | `"7"` | Number of use cases (as string) |
| `company_description` | No | `""` | Company description |
| `readiness_score` | No | `"50"` | AI readiness score 0-100 (as string) |
| `readiness_category` | No | `"Explorer"` | Explorer/Adopter/Leader |
| `report_expectations` | No | `""` | Special requirements |
| `google_drive_link` | No | `""` | Google Drive folder URL |

**Important:** All numeric values should be passed as **strings** (e.g., `"7"` not `7`)!

---

## 🔐 Security Best Practices

### ❌ DON'T: Expose API Key in Browser

```javascript
// BAD - Don't do this!
// Your API key will be visible in browser DevTools
const apiKey = 'ps_abc123...'; // ❌ NEVER hardcode
```

### ✅ DO: Call from Backend

**Option A: Your Own Backend**
```javascript
// Client (browser)
const response = await fetch('/api/trigger-pipeline', {
  method: 'POST',
  body: JSON.stringify({ company_name: 'Acme' }),
});

// Server (Node.js/Express)
app.post('/api/trigger-pipeline', async (req, res) => {
  // API key is safe on server
  const result = await triggerPaperspace(req.body);
  res.json(result);
});
```

**Option B: Serverless Function** (even cheaper!)
```javascript
// Cloudflare Worker / AWS Lambda / Vercel Function
export default async (req) => {
  const data = await req.json();
  
  // API key from environment variable
  const response = await fetch('https://api.paperspace.io/v1/workflows/runs', {
    headers: { 'Authorization': `Bearer ${process.env.PAPERSPACE_API_KEY}` },
    body: JSON.stringify({ workflowId: process.env.WORKFLOW_ID, inputs: data }),
  });
  
  return response;
};
```

### Environment Variables

```bash
# .env file (add to .gitignore!)
PAPERSPACE_API_KEY=ps_abc123...
PAPERSPACE_WORKFLOW_ID=wf_xyz789...
PAPERSPACE_PROJECT_ID=prjyqfzasih
```

---

## 📊 Monitoring

### Via Paperspace Console
1. Go to https://console.paperspace.com
2. Navigate to your project
3. Click "Workflows"
4. Find your run by ID
5. View logs in real-time

### Via API (Programmatic)

**Check Status:**
```bash
curl https://api.paperspace.io/v1/workflows/runs/RUN_ID \
  -H "Authorization: Bearer $PAPERSPACE_API_KEY"
```

**Monitor in Code:**
```javascript
async function waitForCompletion(runId) {
  while (true) {
    const response = await fetch(
      `https://api.paperspace.io/v1/workflows/runs/${runId}`,
      { headers: { 'Authorization': `Bearer ${API_KEY}` } }
    );
    
    const run = await response.json();
    
    if (run.status === 'succeeded') {
      console.log('✅ Pipeline completed!');
      return run;
    } else if (run.status === 'failed') {
      throw new Error('Pipeline failed');
    }
    
    await sleep(30000); // Check every 30 seconds
  }
}
```

---

## 🎓 Complete Examples

See `paperspace/client_examples/` for full working examples:

- **`direct_api_call.js`** - JavaScript/Node.js with multiple examples
- **`direct_api_call.py`** - Python with CLI interface
- **`README.md`** - Detailed usage guide

**Run examples:**
```bash
# JavaScript
cd paperspace/client_examples
npm install
export PAPERSPACE_API_KEY=ps_...
export PAPERSPACE_WORKFLOW_ID=wf_...
node direct_api_call.js

# Python
cd paperspace/client_examples
pip install requests
export PAPERSPACE_API_KEY=ps_...
export PAPERSPACE_WORKFLOW_ID=wf_...
python direct_api_call.py "Acme Corp" --use-cases 7
```

---

## 🐛 Troubleshooting

### Error: "Unauthorized" or "Invalid API key"

**Check:**
- API key starts with `ps_`
- No extra spaces or newlines
- Key is active in Paperspace console
- Using correct environment variable name

**Fix:**
```bash
# Verify your API key
echo $PAPERSPACE_API_KEY | cut -c1-5
# Should output: ps_ab

# Re-set if needed
export PAPERSPACE_API_KEY=ps_your_actual_key
```

### Error: "Workflow not found"

**Check:**
- Workflow ID starts with `wf_`
- Workflow exists: `gradient workflows list`
- Using correct project

**Fix:**
```bash
# List your workflows
gradient workflows list --projectId YOUR_PROJECT_ID

# Copy the correct workflow ID
export PAPERSPACE_WORKFLOW_ID=wf_...
```

### Error: "Missing required input: company_name"

**Check:**
- All required fields are provided
- Field names match exactly (case-sensitive)
- Values are strings (e.g., `"7"` not `7`)

**Fix:**
```javascript
// Ensure company_name is provided
inputs: {
  company_name: 'Acme Corp', // ✅ Required
  use_cases_count: '7',      // ✅ String
}
```

### Pipeline Runs But Fails

**Check:**
- Paperspace console logs for error details
- Google Drive link is shared with service account
- All required secrets are set (OPENAI_API_KEY, etc.)
- Workflow YAML has correct GitHub repo URL

---

## 💰 Cost Comparison

| Component | With Webhook | Direct API | Savings |
|-----------|-------------|------------|---------|
| Webhook Server | $6.48/mo | $0 | **$6.48/mo** |
| Per Pipeline Run | $0.41 | $0.41 | - |
| **100 runs/month** | **$47.48** | **$41.00** | **$6.48/mo** |

**Annual savings: $77.76** 💰

---

## ✅ Migration Checklist

If you already deployed the webhook server and want to switch:

- [ ] Get Paperspace API key (`ps_...`)
- [ ] Get Workflow ID (`wf_...`)
- [ ] Test direct API call locally
- [ ] Update your client application code
- [ ] Deploy updated client
- [ ] Test end-to-end with real submission
- [ ] Delete webhook server deployment (optional, saves $6.48/mo)
  ```bash
  gradient deployments delete --deploymentId DEPLOYMENT_ID
  ```
- [ ] Update documentation/team

---

## 🎯 Next Steps

1. **Get credentials** (API key + Workflow ID)
2. **Test locally** with examples
3. **Integrate** into your application
4. **Deploy** (no webhook server needed!)
5. **Monitor** via Paperspace console

---

**Questions?** Check the full examples in `paperspace/client_examples/` or review the Paperspace API docs: https://docs.paperspace.com/gradient/api/


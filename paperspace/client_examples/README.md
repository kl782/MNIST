# Direct API Call Examples

These examples show how to trigger the Paperspace pipeline **directly** from your client application, **without** needing a webhook server.

## 🎯 Why Direct API Calls?

**Savings:** $6.48/month (no always-on webhook server)  
**Simplicity:** One less component to maintain  
**Speed:** Direct connection, no middleman  

## 📋 Prerequisites

1. **Paperspace API Key** (starts with `ps_...`)
   - Get from: https://console.paperspace.com → Team Settings → API Keys
   
2. **Workflow ID** (starts with `wf_...`)
   - Get from: `gradient workflows list --projectId YOUR_PROJECT_ID`
   
3. **Set environment variables:**
   ```bash
   export PAPERSPACE_API_KEY=ps_xxxxxxxxxxxxx
   export PAPERSPACE_WORKFLOW_ID=wf_xxxxxxxxxxxxx
   ```

## 🚀 Quick Start

### JavaScript/Node.js

```bash
# Install dependencies
npm install node-fetch

# Set environment variables
export PAPERSPACE_API_KEY=ps_xxxxxxxxxxxxx
export PAPERSPACE_WORKFLOW_ID=wf_xxxxxxxxxxxxx

# Run example
node direct_api_call.js
```

**Basic usage:**
```javascript
const { triggerAIPipeline } = require('./direct_api_call');

const result = await triggerAIPipeline({
  company_name: 'Acme Corp',
  company_description: 'A tech company',
  use_cases_count: 7,
  readiness_score: 75,
});

console.log('Pipeline started:', result.id);
```

### Python

```bash
# Install dependencies
pip install requests

# Set environment variables
export PAPERSPACE_API_KEY=ps_xxxxxxxxxxxxx
export PAPERSPACE_WORKFLOW_ID=wf_xxxxxxxxxxxxx

# Run example
python direct_api_call.py "Acme Corp" --use-cases 7 --score 75
```

**Basic usage:**
```python
from direct_api_call import trigger_ai_pipeline

result = trigger_ai_pipeline({
    'company_name': 'Acme Corp',
    'company_description': 'A tech company',
    'use_cases_count': 7,
    'readiness_score': 75,
})

print('Pipeline started:', result['id'])
```

## 📖 Usage Examples

### 1. Basic Company Submission

```javascript
// JavaScript
await triggerAIPipeline({
  company_name: 'TechCorp',
  company_description: 'Leading AI company',
  use_cases_count: 5,
  readiness_score: 80,
  readiness_category: 'Adopter',
});
```

```python
# Python
trigger_ai_pipeline({
    'company_name': 'TechCorp',
    'company_description': 'Leading AI company',
    'use_cases_count': 5,
    'readiness_score': 80,
    'readiness_category': 'Adopter',
})
```

### 2. With Google Drive Files

```javascript
// JavaScript
await triggerAIPipeline({
  company_name: 'StartupXYZ',
  use_cases_count: 7,
  google_drive_link: 'https://drive.google.com/drive/folders/1ABC123...',
});
```

```python
# Python
trigger_ai_pipeline({
    'company_name': 'StartupXYZ',
    'use_cases_count': 7,
    'google_drive_link': 'https://drive.google.com/drive/folders/1ABC123...',
})
```

### 3. Monitor Until Completion

```javascript
// JavaScript
const result = await triggerAIPipeline({ company_name: 'Acme' });
const finalResult = await monitorWorkflow(result.id);
console.log('Pipeline completed!');
```

```python
# Python
result = trigger_ai_pipeline({'company_name': 'Acme'})
final_result = monitor_workflow(result['id'])
print('Pipeline completed!')
```

### 4. Integration with Your Backend

**Express.js:**
```javascript
const express = require('express');
const { triggerAIPipeline } = require('./direct_api_call');

const app = express();
app.use(express.json());

app.post('/api/submit-company', async (req, res) => {
  try {
    const result = await triggerAIPipeline(req.body);
    res.json({ success: true, runId: result.id });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000);
```

**Flask:**
```python
from flask import Flask, request, jsonify
from direct_api_call import trigger_ai_pipeline

app = Flask(__name__)

@app.route('/api/submit-company', methods=['POST'])
def submit_company():
    try:
        result = trigger_ai_pipeline(request.json)
        return jsonify({'success': True, 'runId': result['id']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

app.run(port=3000)
```

### 5. Batch Processing

```python
# Python - Process multiple companies
companies = [
    {'company_name': 'Company A', 'use_cases_count': 5},
    {'company_name': 'Company B', 'use_cases_count': 7},
    {'company_name': 'Company C', 'use_cases_count': 10},
]

for company in companies:
    result = trigger_ai_pipeline(company)
    print(f"Started pipeline for {company['company_name']}: {result['id']}")
```

## 🔐 Security Best Practices

### 1. Never Hardcode API Keys

```javascript
// ❌ BAD
const API_KEY = 'ps_abc123...';

// ✅ GOOD
const API_KEY = process.env.PAPERSPACE_API_KEY;
```

### 2. Use Environment Variables

```bash
# .env file (add to .gitignore!)
PAPERSPACE_API_KEY=ps_xxxxxxxxxxxxx
PAPERSPACE_WORKFLOW_ID=wf_xxxxxxxxxxxxx
```

### 3. Server-Side Only (for web apps)

```javascript
// ❌ BAD - Don't call from browser/client-side JavaScript
// Browser can see your API key!

// ✅ GOOD - Call from your backend
// Your backend calls Paperspace API
// Browser calls your backend (no API key exposed)
```

### 4. Rate Limiting

```javascript
// Add delays between requests
for (const company of companies) {
  await triggerAIPipeline(company);
  await sleep(5000); // Wait 5 seconds between requests
}
```

## 📊 Monitoring Workflow Runs

### Via Paperspace Console

1. Go to https://console.paperspace.com
2. Navigate to your project
3. Click "Workflows"
4. Find your workflow run by ID
5. View logs and status in real-time

### Via API (Programmatic)

```javascript
// JavaScript
const response = await fetch(
  `https://api.paperspace.io/v1/workflows/runs/${runId}`,
  {
    headers: {
      'Authorization': `Bearer ${PAPERSPACE_API_KEY}`,
    },
  }
);

const run = await response.json();
console.log('Status:', run.status);
console.log('Started:', run.createdAt);
```

```python
# Python
response = requests.get(
    f'https://api.paperspace.io/v1/workflows/runs/{run_id}',
    headers={'Authorization': f'Bearer {PAPERSPACE_API_KEY}'}
)

run = response.json()
print('Status:', run['status'])
print('Started:', run['createdAt'])
```

## 🐛 Troubleshooting

### Error: "Invalid API key"
- Check that `PAPERSPACE_API_KEY` starts with `ps_`
- Verify the key is active in Paperspace console
- Make sure no extra spaces in environment variable

### Error: "Workflow not found"
- Verify `PAPERSPACE_WORKFLOW_ID` starts with `wf_`
- Check workflow exists: `gradient workflows list`
- Ensure you're using the correct project

### Error: "Missing required input"
- Check `company_name` is provided
- Verify all field names match exactly
- Review workflow YAML for required inputs

### Rate Limiting
- Paperspace may rate limit API calls
- Add delays between requests (5-10 seconds)
- Consider implementing exponential backoff

## 📚 API Reference

### Paperspace Workflows API

**Trigger Workflow:**
```
POST https://api.paperspace.io/v1/workflows/runs
Headers:
  Authorization: Bearer ps_xxxxxxxxxxxxx
  Content-Type: application/json
Body:
  {
    "workflowId": "wf_xxxxxxxxxxxxx",
    "inputs": { ... }
  }
```

**Get Run Status:**
```
GET https://api.paperspace.io/v1/workflows/runs/{runId}
Headers:
  Authorization: Bearer ps_xxxxxxxxxxxxx
```

**List Runs:**
```
GET https://api.paperspace.io/v1/workflows/{workflowId}/runs
Headers:
  Authorization: Bearer ps_xxxxxxxxxxxxx
```

Full API docs: https://docs.paperspace.com/gradient/api/

## 💰 Cost Comparison

| Approach | Setup Cost | Per-Run Cost | Monthly (100 runs) |
|----------|------------|--------------|-------------------|
| **Webhook Server** | $6.48/mo | $0.41 | $47.48 |
| **Direct API** | $0 | $0.41 | $41.00 |

**Savings: $6.48/month** by skipping the webhook server!

## 🎯 Next Steps

1. **Test locally:** Run the examples with your API key
2. **Integrate:** Add to your application's backend
3. **Deploy:** No webhook server needed!
4. **Monitor:** Use Paperspace console to track runs

---

**Note:** The webhook server (`webhook_server_cloud.py`) is now **optional**. Use it only if you need custom preprocessing or can't make direct API calls from your application.


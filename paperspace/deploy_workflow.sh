#!/bin/bash
# Deploy AI Pipeline Workflow using Paperspace REST API
# No CLI tool needed - just curl!

set -e

# Your credentials (set these environment variables or replace below)
API_KEY="${PAPERSPACE_API_KEY:-YOUR_API_KEY_HERE}"
PROJECT_ID="${PAPERSPACE_PROJECT_ID:-prjyqfzasih}"

echo "🚀 Deploying AI Pipeline Workflow..."
echo "📦 Project: $PROJECT_ID"
echo ""

# Read workflow spec
WORKFLOW_SPEC=$(cat paperspace/workflows/pipeline-workflow.yaml)

# Create workflow via REST API
echo "📡 Calling Paperspace API..."
RESPONSE=$(curl -s -X POST https://api.paperspace.com/v1/workflows \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"projectId\": \"$PROJECT_ID\",
    \"name\": \"ai-pipeline-workflow\",
    \"spec\": $(echo "$WORKFLOW_SPEC" | jq -Rs .)
  }")

# Check if successful
if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.id')
  echo ""
  echo "✅ Workflow created successfully!"
  echo "🆔 Workflow ID: $WORKFLOW_ID"
  echo ""
  echo "📝 Add this to your .env file:"
  echo "PAPERSPACE_WORKFLOW_ID=$WORKFLOW_ID"
  echo ""
  echo "🎯 Next step: Test triggering the workflow"
  echo "cd paperspace/client_examples"
  echo "export PAPERSPACE_API_KEY=$API_KEY"
  echo "export PAPERSPACE_WORKFLOW_ID=$WORKFLOW_ID"
  echo "python direct_api_call.py \"Test Company\" --use-cases 3"
else
  echo "❌ Failed to create workflow"
  echo "Response: $RESPONSE"
  exit 1
fi


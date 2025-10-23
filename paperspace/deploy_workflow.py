#!/usr/bin/env python3
"""
Deploy Paperspace Workflow directly using Python SDK (no CLI needed!)
"""

import os
import sys
from gradient import GradientApi

# Your credentials (set these environment variables)
API_KEY = os.environ.get("PAPERSPACE_API_KEY", "YOUR_API_KEY_HERE")
PROJECT_ID = os.environ.get("PAPERSPACE_PROJECT_ID", "YOUR_PROJECT_ID_HERE")

def deploy_workflow():
    """Deploy the AI pipeline workflow."""
    print("🚀 Deploying AI Pipeline Workflow...")
    
    try:
        # Initialize Gradient client
        client = GradientApi(api_key=API_KEY)
        
        # Read workflow spec
        with open('paperspace/workflows/pipeline-workflow.yaml', 'r') as f:
            workflow_spec = f.read()
        
        # Create workflow
        print(f"📦 Creating workflow in project {PROJECT_ID}...")
        
        # Note: The exact method depends on the SDK version
        # This is a placeholder - check gradient SDK docs
        try:
            result = client.workflows.create(
                project_id=PROJECT_ID,
                name="ai-pipeline-workflow",
                spec=workflow_spec
            )
            
            print(f"✅ Workflow created successfully!")
            print(f"🆔 Workflow ID: {result.id}")
            print(f"📝 Save this ID as PAPERSPACE_WORKFLOW_ID={result.id}")
            
            return result.id
            
        except AttributeError:
            print("⚠️  The gradient Python SDK may not support workflow creation.")
            print("📖 Use the REST API approach instead (see Option 2 below)")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Try Option 2: Direct REST API (see below)")
        return None

if __name__ == '__main__':
    workflow_id = deploy_workflow()
    
    if not workflow_id:
        print("\n" + "="*60)
        print("OPTION 2: Use Direct REST API (Recommended)")
        print("="*60)
        print("\nRun this curl command instead:\n")
        print(f"""curl -X POST https://api.paperspace.com/v1/workflows \\
  -H "Authorization: Bearer {API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "projectId": "{PROJECT_ID}",
    "name": "ai-pipeline-workflow",
    "spec": @paperspace/workflows/pipeline-workflow.yaml
  }}'
""")


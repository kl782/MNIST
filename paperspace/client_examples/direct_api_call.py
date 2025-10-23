#!/usr/bin/env python3
"""
Direct Paperspace API Call Example (Python)

This replaces the webhook server approach.
Call this directly from your Python application or backend.
"""

import os
import re
import time
import requests
from typing import Dict, Any, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

PAPERSPACE_API_KEY = os.environ.get('PAPERSPACE_API_KEY')
PAPERSPACE_WORKFLOW_ID = os.environ.get('PAPERSPACE_WORKFLOW_ID')
PAPERSPACE_API_URL = 'https://api.paperspace.io/v1/workflows/runs'


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def trigger_ai_pipeline(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger AI pipeline for a company.
    
    Args:
        company_data: Company information dict with keys:
            - company_name (required)
            - company_description
            - use_cases_count
            - readiness_score
            - readiness_category
            - report_expectations
            - google_drive_link
    
    Returns:
        Workflow run details
    """
    # Validate required fields
    if not company_data.get('company_name'):
        raise ValueError('company_name is required')
    
    print(f"🚀 Triggering AI pipeline for: {company_data['company_name']}")
    
    # Prepare workflow inputs
    workflow_inputs = {
        'company_name': company_data['company_name'],
        'company_slug': slugify(company_data['company_name']),
        'use_cases_count': str(company_data.get('use_cases_count', 7)),
        'company_description': company_data.get('company_description', ''),
        'readiness_score': str(company_data.get('readiness_score', 50)),
        'readiness_category': company_data.get('readiness_category', 'Explorer'),
        'report_expectations': company_data.get('report_expectations', ''),
        'google_drive_link': company_data.get('google_drive_link', ''),
    }
    
    print(f"📋 Workflow inputs: {workflow_inputs}")
    
    # Call Paperspace API
    response = requests.post(
        PAPERSPACE_API_URL,
        headers={
            'Authorization': f'Bearer {PAPERSPACE_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'workflowId': PAPERSPACE_WORKFLOW_ID,
            'inputs': workflow_inputs,
        }
    )
    
    if not response.ok:
        raise Exception(f'Paperspace API error: {response.status_code} - {response.text}')
    
    result = response.json()
    
    print('✅ Pipeline triggered successfully!')
    print(f"📊 Run ID: {result['id']}")
    print(f"🔗 Monitor at: https://console.paperspace.com/workflows/{PAPERSPACE_WORKFLOW_ID}/runs/{result['id']}")
    
    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def slugify(text: str) -> str:
    """Convert company name to filesystem-safe slug."""
    return re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_').lower()


def monitor_workflow(run_id: str) -> Dict[str, Any]:
    """
    Monitor workflow run until completion.
    
    Args:
        run_id: Workflow run ID
    
    Returns:
        Final workflow run status
    """
    status_url = f'https://api.paperspace.io/v1/workflows/runs/{run_id}'
    
    while True:
        response = requests.get(
            status_url,
            headers={
                'Authorization': f'Bearer {PAPERSPACE_API_KEY}',
            }
        )
        
        run = response.json()
        
        print(f"📊 Status: {run['status']}")
        
        if run['status'] == 'succeeded':
            print('✅ Pipeline completed successfully!')
            return run
        elif run['status'] == 'failed':
            print('❌ Pipeline failed')
            raise Exception('Workflow failed')
        
        # Wait 30 seconds before checking again
        time.sleep(30)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

def example1_basic():
    """Example 1: Basic usage"""
    result = trigger_ai_pipeline({
        'company_name': 'Acme Corporation',
        'company_description': 'A leading technology company',
        'use_cases_count': 7,
        'readiness_score': 75,
        'readiness_category': 'Adopter',
        'report_expectations': 'Comprehensive AI readiness analysis',
    })
    
    print(f"Pipeline started: {result['id']}")


def example2_with_drive():
    """Example 2: With Google Drive files"""
    result = trigger_ai_pipeline({
        'company_name': 'TechStartup Inc',
        'company_description': 'Innovative startup in AI space',
        'use_cases_count': 5,
        'google_drive_link': 'https://drive.google.com/drive/folders/1ABC...',
    })
    
    # Monitor until completion
    final_result = monitor_workflow(result['id'])
    print('Final report ready!')


def example3_flask():
    """Example 3: Integration with Flask backend"""
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    
    @app.route('/api/trigger-pipeline', methods=['POST'])
    def api_trigger_pipeline():
        try:
            result = trigger_ai_pipeline(request.json)
            return jsonify({
                'success': True,
                'runId': result['id'],
                'message': 'Pipeline triggered successfully',
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500
    
    app.run(port=3000)


def example4_batch():
    """Example 4: Process multiple companies"""
    companies = [
        {'company_name': 'Company A', 'use_cases_count': 5},
        {'company_name': 'Company B', 'use_cases_count': 7},
        {'company_name': 'Company C', 'use_cases_count': 10},
    ]
    
    run_ids = []
    for company in companies:
        result = trigger_ai_pipeline(company)
        run_ids.append(result['id'])
        time.sleep(5)  # Rate limiting
    
    print(f"Started {len(run_ids)} pipelines")
    
    # Monitor all
    for run_id in run_ids:
        try:
            monitor_workflow(run_id)
        except Exception as e:
            print(f"Run {run_id} failed: {e}")


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Trigger AI pipeline via Paperspace API')
    parser.add_argument('company_name', help='Company name')
    parser.add_argument('--description', help='Company description', default='')
    parser.add_argument('--use-cases', type=int, help='Number of use cases', default=7)
    parser.add_argument('--score', type=int, help='Readiness score', default=50)
    parser.add_argument('--category', help='Readiness category', default='Explorer')
    parser.add_argument('--drive-link', help='Google Drive link', default='')
    parser.add_argument('--monitor', action='store_true', help='Monitor until completion')
    
    args = parser.parse_args()
    
    # Trigger pipeline
    result = trigger_ai_pipeline({
        'company_name': args.company_name,
        'company_description': args.description,
        'use_cases_count': args.use_cases,
        'readiness_score': args.score,
        'readiness_category': args.category,
        'google_drive_link': args.drive_link,
    })
    
    # Monitor if requested
    if args.monitor:
        monitor_workflow(result['id'])


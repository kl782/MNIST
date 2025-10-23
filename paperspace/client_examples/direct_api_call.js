/**
 * Direct Paperspace API Call Example (JavaScript/Node.js)
 * 
 * This replaces the webhook server approach.
 * Call this directly from your client application or backend.
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const PAPERSPACE_API_KEY = process.env.PAPERSPACE_API_KEY; // Get from console.paperspace.com
const PAPERSPACE_WORKFLOW_ID = process.env.PAPERSPACE_WORKFLOW_ID; // Created workflow ID
const PAPERSPACE_API_URL = 'https://api.paperspace.io/v1/workflows/runs';

// =============================================================================
// MAIN FUNCTION
// =============================================================================

/**
 * Trigger AI pipeline for a company
 * @param {Object} companyData - Company information
 * @returns {Promise<Object>} - Workflow run details
 */
async function triggerAIPipeline(companyData) {
  // Validate required fields
  if (!companyData.company_name) {
    throw new Error('company_name is required');
  }
  
  console.log(`🚀 Triggering AI pipeline for: ${companyData.company_name}`);
  
  // Prepare workflow inputs
  const workflowInputs = {
    company_name: companyData.company_name,
    company_slug: slugify(companyData.company_name),
    use_cases_count: String(companyData.use_cases_count || 7),
    company_description: companyData.company_description || '',
    readiness_score: String(companyData.readiness_score || 50),
    readiness_category: companyData.readiness_category || 'Explorer',
    report_expectations: companyData.report_expectations || '',
    google_drive_link: companyData.google_drive_link || '',
  };
  
  console.log('📋 Workflow inputs:', workflowInputs);
  
  // Call Paperspace API
  const response = await fetch(PAPERSPACE_API_URL, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${PAPERSPACE_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      workflowId: PAPERSPACE_WORKFLOW_ID,
      inputs: workflowInputs,
    }),
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Paperspace API error: ${response.status} - ${error}`);
  }
  
  const result = await response.json();
  
  console.log('✅ Pipeline triggered successfully!');
  console.log(`📊 Run ID: ${result.id}`);
  console.log(`🔗 Monitor at: https://console.paperspace.com/workflows/${PAPERSPACE_WORKFLOW_ID}/runs/${result.id}`);
  
  return result;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Convert company name to filesystem-safe slug
 */
function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '_')
    .replace(/^-+|-+$/g, '');
}

/**
 * Monitor workflow run status
 */
async function monitorWorkflow(runId) {
  const statusUrl = `https://api.paperspace.io/v1/workflows/runs/${runId}`;
  
  while (true) {
    const response = await fetch(statusUrl, {
      headers: {
        'Authorization': `Bearer ${PAPERSPACE_API_KEY}`,
      },
    });
    
    const run = await response.json();
    
    console.log(`📊 Status: ${run.status}`);
    
    if (run.status === 'succeeded') {
      console.log('✅ Pipeline completed successfully!');
      return run;
    } else if (run.status === 'failed') {
      console.log('❌ Pipeline failed');
      throw new Error('Workflow failed');
    }
    
    // Wait 30 seconds before checking again
    await new Promise(resolve => setTimeout(resolve, 30000));
  }
}

// =============================================================================
// USAGE EXAMPLES
// =============================================================================

// Example 1: Basic usage
async function example1_basic() {
  const result = await triggerAIPipeline({
    company_name: 'Acme Corporation',
    company_description: 'A leading technology company',
    use_cases_count: 7,
    readiness_score: 75,
    readiness_category: 'Adopter',
    report_expectations: 'Comprehensive AI readiness analysis',
  });
  
  console.log('Pipeline started:', result.id);
}

// Example 2: With Google Drive files
async function example2_with_drive() {
  const result = await triggerAIPipeline({
    company_name: 'TechStartup Inc',
    company_description: 'Innovative startup in AI space',
    use_cases_count: 5,
    google_drive_link: 'https://drive.google.com/drive/folders/1ABC...',
  });
  
  // Monitor until completion
  const finalResult = await monitorWorkflow(result.id);
  console.log('Final report ready!');
}

// Example 3: Integration with Express.js backend
function example3_express() {
  const express = require('express');
  const app = express();
  app.use(express.json());
  
  app.post('/api/trigger-pipeline', async (req, res) => {
    try {
      const result = await triggerAIPipeline(req.body);
      res.json({
        success: true,
        runId: result.id,
        message: 'Pipeline triggered successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  });
  
  app.listen(3000, () => {
    console.log('Server running on port 3000');
  });
}

// =============================================================================
// EXPORT
// =============================================================================

module.exports = {
  triggerAIPipeline,
  monitorWorkflow,
  slugify,
};

// Run example if called directly
if (require.main === module) {
  example1_basic().catch(console.error);
}


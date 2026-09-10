import pytest# Fake data to feed the test
from unittest.mock import MagicMock, patch
import ai_engine


FAKE_RESUME = "experienced Python Developer"
FAKE_JOBS = [{"title": "Backend Engineer", "company": "TechCorp", "description": "Needs Python."}]

# Use @patch to intercept the exact path to the Gemini client method
@patch("ai_engine.client.models.generate_content")
def test_triage_job_batch_success(mock_generate):
    """Tests if the AI engine correctly parses a valid API response."""
    
    # 1. Arrange: Build a fake API response object
    fake_response = MagicMock()
    # This is the exact JSON string structure the prompt demands
    fake_response.text = '[{"score": 95, "match_verdict": "HIGH", "aligned_skills": ["Python"], "gap_analysis": "None", "reasoning": "Great fit"}]'
    
    # Tell the interceptor to return this fake response
    mock_generate.return_value = fake_response
    
    # 2. Act: Run the function. It will hit the interceptor instead of the real API.
    results = ai_engine.triage_job_batch_with_retry(FAKE_RESUME, FAKE_JOBS)
    
    # 3. Assert: Verify the Python logic handled the data correctly
    assert len(results) == 1
    assert results[0]["score"] == 95
    assert results[0]["match_verdict"] == "HIGH"
    
    # Prove that the interceptor was actually called
    mock_generate.assert_called_once()
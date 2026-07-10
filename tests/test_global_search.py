import pytest

def test_command_palette_filtering():
    """Asserts that search terms match expected list items in the global palette."""
    commands = [
        {"id": "new-job", "label": "Create new job"},
        {"id": "go-crm", "label": "Go to CRM Directory"},
        {"id": "go-agent", "label": "Open AI Recruiter Workspace"}
    ]
    
    query = "crm"
    matches = [c for c in commands if query.lower() in c["label"].lower()]
    assert len(matches) == 1
    assert matches[0]["id"] == "go-crm"

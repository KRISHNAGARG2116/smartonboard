from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field


class BaseAgentTool:
    """Base class for all tools in the AI Recruiting Agent Platform."""
    name: str = ""
    tool_version: str = "1.0.0"
    description: str = ""
    required_permissions: List[str] = []
    approval_level: str = "read_only"  # read_only, draft, mutating
    health_status: str = "healthy"  # healthy, degraded, offline
    requires: List[str] = []  # Dependency tags required as inputs
    produces: List[str] = []  # Dependency tags produced as outputs
    cost_estimate_tokens: int = 1000
    cache_policy_seconds: int = 300

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Verify that the tool has all required inputs before execution."""
        for req in self.requires:
            if req not in inputs:
                return False
        return True

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool's core logic. Must be overridden by subclasses."""
        raise NotImplementedError("Tool must implement execute method.")


# --- Capabilities / Skill Groupings Tool Definitions ---

class SearchCandidatesTool(BaseAgentTool):
    name = "search_candidates"
    tool_version = "search_candidates v4"
    description = "Search and filter candidate profiles by keyword, skills, or location."
    required_permissions = ["VIEW_CANDIDATES"]
    approval_level = "read_only"
    requires = []
    produces = ["candidate_ids"]
    cost_estimate_tokens = 500
    cache_policy_seconds = 60

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation will query candidate database/PGVector
        query = inputs.get("query", "")
        location = inputs.get("location", "")
        return {
            "candidate_ids": [
                "ff8ad11b-f3c2-414c-bf3c-51fb5743d0a3",  # Demo Candidate John
                "cand-2",
                "cand-3"
            ],
            "metadata": {"query": query, "location": location, "count": 3}
        }


class SearchJobsTool(BaseAgentTool):
    name = "search_jobs"
    tool_version = "search_jobs v1"
    description = "Search and filter job requisitions by department, title, or status."
    required_permissions = ["VIEW_JOBS"]
    approval_level = "read_only"
    requires = []
    produces = ["job_ids"]

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "job_ids": ["74b162a7-a3dc-4337-a275-789be4674756"],
            "metadata": {"count": 1}
        }


class SearchTalentPoolsTool(BaseAgentTool):
    name = "search_talent_pools"
    tool_version = "search_talent_pools v1"
    description = "Search active talent CRM pools and dynamic lists."
    required_permissions = ["VIEW_TALENT_CRM"]
    approval_level = "read_only"
    requires = []
    produces = ["pool_ids"]

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "pool_ids": ["pool-1", "pool-2"],
            "metadata": {"count": 2}
        }


class CompareCandidatesTool(BaseAgentTool):
    name = "compare_candidates"
    tool_version = "compare_candidates v2"
    description = "Generate side-by-side strengths, experience and match comparisons."
    required_permissions = ["VIEW_CANDIDATES"]
    approval_level = "read_only"
    requires = ["candidate_ids"]
    produces = ["comparison_matrix"]
    cost_estimate_tokens = 2500

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        candidate_ids = inputs.get("candidate_ids", [])
        return {
            "comparison_matrix": {
                "candidates": [
                    {"id": cid, "name": "John Doe" if "ff8ad11b" in str(cid) else "Lookalike Candidate", "experience": "6 years", "skills_overlap": ["Python", "React"], "ai_match": 92}
                    for cid in candidate_ids
                ]
            }
        }


class ResumeQATool(BaseAgentTool):
    name = "resume_qa"
    tool_version = "resume_qa v1"
    description = "Ask questions regarding a candidate's background, tenure, or gaps."
    required_permissions = ["VIEW_CANDIDATES"]
    approval_level = "read_only"
    requires = ["candidate_ids"]
    produces = ["qa_responses"]

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "qa_responses": [
                {"question": inputs.get("question", "Summarize gaps"), "answer": "The candidate has a 3-month gap in 2024 which was explained as travel."}
            ]
        }


class AddToPoolTool(BaseAgentTool):
    name = "add_to_pool"
    tool_version = "add_to_pool v1"
    description = "Add candidates to a static talent CRM pool."
    required_permissions = ["MANAGE_TALENT_POOLS"]
    approval_level = "mutating"
    requires = ["candidate_ids", "pool_id"]
    produces = ["action_status"]

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"action_status": "success", "message": "Candidates added to pool successfully."}


class MoveStageTool(BaseAgentTool):
    name = "move_stage"
    tool_version = "move_stage v1"
    description = "Transition candidate application to a different pipeline stage."
    required_permissions = ["MANAGE_CANDIDATE_RELATIONSHIPS"]
    approval_level = "mutating"
    requires = ["application_id", "target_stage_id"]
    produces = ["action_status"]

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"action_status": "success", "message": "Application moved to target stage successfully."}


class DraftOutreachTool(BaseAgentTool):
    name = "draft_outreach"
    tool_version = "draft_outreach v3"
    description = "Draft custom email template (outreach, invite, rejection) for a candidate."
    required_permissions = ["MANAGE_CANDIDATE_RELATIONSHIPS"]
    approval_level = "draft"
    requires = ["candidate_ids"]
    produces = ["email_draft"]
    cost_estimate_tokens = 1500

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "email_draft": {
                "subject": "Exciting Opportunity at SmartOnboard",
                "body": "Hi John,\n\nI was reviewing your backend React background and wanted to connect..."
            }
        }


class ViewExecutiveReportTool(BaseAgentTool):
    name = "view_executive_report"
    tool_version = "view_executive_report v1"
    description = "Fetch high-level company recruitment metric summaries."
    required_permissions = ["VIEW_EXECUTIVE_REPORTS"]
    approval_level = "read_only"
    requires = []
    produces = ["report_data"]

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report_data": {
                "time_to_hire": "28 days",
                "active_jobs_count": 8,
                "offers_accepted_rate": "84%"
            }
        }


# --- Tool Registry Directory class ---

class ToolRegistry:
    _registry: Dict[str, Type[BaseAgentTool]] = {
        "search_candidates": SearchCandidatesTool,
        "search_jobs": SearchJobsTool,
        "search_talent_pools": SearchTalentPoolsTool,
        "compare_candidates": CompareCandidatesTool,
        "resume_qa": ResumeQATool,
        "add_to_pool": AddToPoolTool,
        "move_stage": MoveStageTool,
        "draft_outreach": DraftOutreachTool,
        "view_executive_report": ViewExecutiveReportTool
    }

    @classmethod
    def get_tool(cls, name: str) -> BaseAgentTool | None:
        tool_class = cls._registry.get(name)
        if tool_class:
            return tool_class()
        return None

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "version": t.tool_version,
                "description": t.description,
                "permissions": t.required_permissions,
                "approval_level": t.approval_level,
                "health": t.health_status,
                "requires": t.requires,
                "produces": t.produces
            }
            for t in [c() for c in cls._registry.values()]
        ]

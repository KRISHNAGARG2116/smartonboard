from fastapi import APIRouter

from api.applications import router as applications_router
from api.auth import router as auth_router
from api.companies import router as companies_router
from api.jobs import router as jobs_router
from api.audit import router as audit_router
from api.notes import router as notes_router
from api.interviews import router as interviews_router
from api.offers import router as offers_router
from api.candidates import router as candidates_router
from api.analytics import router as analytics_router
from api.intelligence import router as intelligence_router
from api.sso import router as sso_router
from api.calendars import router as calendars_router
from api.scheduling import router as scheduling_router
from api.pipelines import router as pipelines_router
from api.approvals import router as approvals_router
from api.committees import router as committees_router
from api.webhooks import router as webhooks_router
from api.enterprise import router as enterprise_router
from api.employees import router as employees_router
from api.notifications import router as notifications_router
from api.search import router as search_router
from api.ai_copilot import router as ai_copilot_router
from api.dashboard import router as dashboard_router
from api.executive_analytics import router as executive_analytics_router
from api.workflows import router as workflows_router
from api.api_keys import router as api_keys_router
from api.emails import router as emails_router
from api.slack_teams import router as slack_teams_router
from api.background_checks import router as background_checks_router
from api.hris_imports import router as hris_imports_router



# Dedicated Candidate Routers
from api.candidate_auth import router as candidate_auth_router
from api.candidate_resumes import router as candidate_resumes_router
from api.candidate_jobs import router as candidate_jobs_router
from api.candidate_applications import router as candidate_applications_router
from api.candidate_interviews import router as candidate_interviews_router
from api.candidate_dashboard import router as candidate_dashboard_router
from api.candidate_messages import router as candidate_messages_router
from api.candidate_tasks import router as candidate_tasks_router
from api.candidate_documents import router as candidate_documents_router
from api.candidate_offers import router as candidate_offers_router
from api.candidate_timeline import router as candidate_timeline_router
from api.candidate_profile import router as candidate_profile_router
from api.candidate_ai import router as candidate_ai_router

# Dedicated Employee Routers
from api.hr_onboarding import router as hr_onboarding_router


v1_router = APIRouter(prefix="/api/v1")

# Mount candidate & employee routers first to prevent path parameter shadowing (e.g. /jobs/feed matching /jobs/{job_id})
v1_router.include_router(candidate_auth_router)
v1_router.include_router(candidate_resumes_router)
v1_router.include_router(candidate_jobs_router)
v1_router.include_router(candidate_applications_router)
v1_router.include_router(candidate_interviews_router)
v1_router.include_router(candidate_dashboard_router)
v1_router.include_router(candidate_messages_router)
v1_router.include_router(candidate_tasks_router)
v1_router.include_router(candidate_documents_router)
v1_router.include_router(candidate_offers_router)
v1_router.include_router(candidate_timeline_router)
v1_router.include_router(candidate_profile_router)
v1_router.include_router(candidate_ai_router)
v1_router.include_router(hr_onboarding_router)



v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(jobs_router)
v1_router.include_router(applications_router)
v1_router.include_router(audit_router)
v1_router.include_router(notes_router)
v1_router.include_router(interviews_router)
v1_router.include_router(offers_router)
v1_router.include_router(candidates_router)
v1_router.include_router(analytics_router)
v1_router.include_router(intelligence_router)
v1_router.include_router(sso_router)
v1_router.include_router(calendars_router)
v1_router.include_router(scheduling_router)
v1_router.include_router(pipelines_router)
v1_router.include_router(approvals_router)
v1_router.include_router(committees_router)
v1_router.include_router(webhooks_router)
v1_router.include_router(enterprise_router)
v1_router.include_router(employees_router)
v1_router.include_router(notifications_router)
v1_router.include_router(search_router)
v1_router.include_router(ai_copilot_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(executive_analytics_router)
v1_router.include_router(workflows_router)
v1_router.include_router(api_keys_router)
v1_router.include_router(emails_router)
v1_router.include_router(slack_teams_router)
v1_router.include_router(background_checks_router)
v1_router.include_router(hris_imports_router)








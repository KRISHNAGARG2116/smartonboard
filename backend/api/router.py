from fastapi import APIRouter

from api import applications, auth, companies, jobs, audit

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(companies.router)
v1_router.include_router(jobs.router)
v1_router.include_router(applications.router)
v1_router.include_router(audit.router)

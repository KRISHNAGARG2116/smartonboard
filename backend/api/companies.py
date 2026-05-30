from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.deps import CurrentUser, TenantDb, RequireOwner
from models import Company
from schemas.company import CompanyResponse, CompanyUpdateRequest

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyResponse)
def get_my_company(current_user: CurrentUser, db: TenantDb):
    company = db.scalar(select(Company).where(Company.id == current_user.company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/me", response_model=CompanyResponse)
def update_my_company(body: CompanyUpdateRequest, current_user: RequireOwner, db: TenantDb):
    company = db.scalar(select(Company).where(Company.id == current_user.company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    if body.name is not None:
        company.name = body.name
    db.commit()
    db.refresh(company)
    return company

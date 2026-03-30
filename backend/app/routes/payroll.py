"""Payroll management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, date
from app.database import get_db
from app.models.user import Business
from app.models.employee import Employee, PayrollRun
from app.auth.dependencies import get_current_user
from app.services.payroll_service import payroll_service

router = APIRouter(prefix="/api/v1/payroll", tags=["Payroll"])

@router.get("/employees")
async def list_employees(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employees = db.query(Employee).filter(
        Employee.business_id == current_user.id,
        Employee.is_active == True,
    ).all()
    return [payroll_service.compute_employee(e) for e in employees]

@router.post("/employees", status_code=201)
async def add_employee(
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start_date = None
    if data.get("start_date"):
        try:
            start_date = date.fromisoformat(data["start_date"])
        except Exception:
            pass

    emp = Employee(
        business_id=current_user.id,
        name_ar=data["name_ar"],
        name_en=data.get("name_en"),
        job_title=data.get("job_title", ""),
        national_id=data.get("national_id"),
        base_salary=float(data["base_salary"]),
        is_saudi=bool(data.get("is_saudi", True)),
        gosi_enrolled=bool(data.get("gosi_enrolled", True)),
        start_date=start_date,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return payroll_service.compute_employee(emp)

@router.put("/employees/{emp_id}")
async def update_employee(
    emp_id: int,
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == emp_id, Employee.business_id == current_user.id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    for field in ["name_ar", "name_en", "job_title", "national_id", "base_salary", "is_saudi", "gosi_enrolled"]:
        if field in data:
            setattr(emp, field, data[field])
    db.commit()
    return payroll_service.compute_employee(emp)

@router.delete("/employees/{emp_id}", status_code=204)
async def delete_employee(
    emp_id: int,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == emp_id, Employee.business_id == current_user.id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.is_active = False
    db.commit()

@router.post("/run")
async def run_payroll(
    data: dict,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    month = int(data.get("month", now.month))
    year = int(data.get("year", now.year))
    return payroll_service.run_payroll(current_user.id, month, year, db)

@router.get("/runs")
async def list_payroll_runs(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    runs = db.query(PayrollRun).filter(
        PayrollRun.business_id == current_user.id,
    ).order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).all()
    return [{
        "id": r.id, "month": r.month, "year": r.year,
        "total_gross": r.total_gross, "total_gosi_employer": r.total_gosi_employer,
        "total_gosi_employee": r.total_gosi_employee, "total_net": r.total_net,
        "headcount": r.headcount, "status": r.status,
        "created_at": r.created_at.isoformat(),
    } for r in runs]

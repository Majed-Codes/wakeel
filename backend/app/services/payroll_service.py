"""Payroll calculation service — Saudi labor law GOSI rates."""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.employee import Employee, PayrollRun

# GOSI rates (Saudi General Organization for Social Insurance)
GOSI_EMPLOYER_SAUDI = 0.09    # 9% for Saudi employees
GOSI_EMPLOYEE_SAUDI = 0.09    # 9% for Saudi employees
GOSI_EMPLOYER_EXPAT = 0.02    # 2% for non-Saudi (work injury only)
GOSI_EMPLOYEE_EXPAT = 0.0     # Non-Saudi employees pay 0%

class PayrollService:
    def compute_employee(self, emp: Employee) -> dict:
        """Compute GOSI and net salary for a single employee."""
        if emp.is_saudi and emp.gosi_enrolled:
            gosi_emp = round(emp.base_salary * GOSI_EMPLOYER_SAUDI, 2)
            gosi_ee = round(emp.base_salary * GOSI_EMPLOYEE_SAUDI, 2)
        elif emp.gosi_enrolled:
            gosi_emp = round(emp.base_salary * GOSI_EMPLOYER_EXPAT, 2)
            gosi_ee = 0.0
        else:
            gosi_emp = 0.0
            gosi_ee = 0.0

        net = round(emp.base_salary - gosi_ee, 2)
        total_cost = round(emp.base_salary + gosi_emp, 2)

        return {
            "id": emp.id,
            "name_ar": emp.name_ar,
            "name_en": emp.name_en,
            "job_title": emp.job_title,
            "base_salary": emp.base_salary,
            "is_saudi": emp.is_saudi,
            "gosi_enrolled": emp.gosi_enrolled,
            "gosi_employer": gosi_emp,
            "gosi_employee": gosi_ee,
            "net_salary": net,
            "total_cost": total_cost,
            "national_id": emp.national_id,
            "start_date": emp.start_date.isoformat() if emp.start_date else None,
            "is_active": emp.is_active,
            "created_at": emp.created_at.isoformat() if emp.created_at else None,
        }

    def run_payroll(self, business_id: int, month: int, year: int, db: Session) -> dict:
        """Calculate and save a payroll run for all active employees."""
        employees = db.query(Employee).filter(
            Employee.business_id == business_id,
            Employee.is_active == True,
        ).all()

        computed = [self.compute_employee(e) for e in employees]

        total_gross = sum(c["base_salary"] for c in computed)
        total_gosi_employer = sum(c["gosi_employer"] for c in computed)
        total_gosi_employee = sum(c["gosi_employee"] for c in computed)
        total_net = sum(c["net_salary"] for c in computed)

        run = PayrollRun(
            business_id=business_id,
            month=month,
            year=year,
            total_gross=round(total_gross, 2),
            total_gosi_employer=round(total_gosi_employer, 2),
            total_gosi_employee=round(total_gosi_employee, 2),
            total_net=round(total_net, 2),
            headcount=len(computed),
            status="completed",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        return {
            "id": run.id,
            "month": run.month,
            "year": run.year,
            "total_gross": run.total_gross,
            "total_gosi_employer": run.total_gosi_employer,
            "total_gosi_employee": run.total_gosi_employee,
            "total_net": run.total_net,
            "headcount": run.headcount,
            "status": run.status,
            "created_at": run.created_at.isoformat(),
            "employees": computed,
        }

payroll_service = PayrollService()

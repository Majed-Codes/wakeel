"""AI Financial Advisor — generates personalized Arabic insights via Claude."""
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from anthropic import Anthropic
from app.models.transaction import Transaction

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

class FinancialAdvisor:
    def generate(self, business_id: int, db: Session) -> dict:
        # Gather financial context
        end = datetime.now(timezone.utc)
        start_30d = end - timedelta(days=30)
        start_90d = end - timedelta(days=90)

        revenue_30d = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "REVENUE",
            Transaction.date >= start_30d,
        ).scalar() or 0.0

        expenses_30d = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "EXPENSE",
            Transaction.date >= start_30d,
        ).scalar() or 0.0

        revenue_90d = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "REVENUE",
            Transaction.date >= start_90d,
        ).scalar() or 0.0

        expenses_90d = db.query(func.sum(Transaction.amount)).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "EXPENSE",
            Transaction.date >= start_90d,
        ).scalar() or 0.0

        net_30d = revenue_30d - expenses_30d
        profit_margin = round((net_30d / revenue_30d * 100) if revenue_30d > 0 else 0, 1)

        # Health score (0-100)
        health_score = self._compute_health(revenue_30d, expenses_30d, revenue_90d, expenses_90d)

        # Generate Arabic advice via Claude
        advice, focus_areas, action_items = self._generate_advice(
            revenue_30d, expenses_30d, profit_margin, health_score, db, business_id
        )

        return {
            "weekly_advice": advice,
            "focus_areas": focus_areas,
            "action_items": action_items,
            "health_score": health_score,
            "generated_at": end.isoformat(),
        }

    def _compute_health(self, rev30, exp30, rev90, exp90) -> int:
        score = 50
        if rev30 > 0:
            if exp30 / rev30 < 0.7: score += 20
            elif exp30 / rev30 < 0.9: score += 10
            else: score -= 10
        if rev90 > 0:
            avg_monthly_rev = rev90 / 3
            if rev30 > avg_monthly_rev * 1.1: score += 15
            elif rev30 > avg_monthly_rev * 0.9: score += 5
            else: score -= 10
        if rev30 > 0: score += 15
        return max(0, min(100, score))

    def _generate_advice(self, revenue, expenses, margin, health, db, business_id) -> tuple:
        if not client.api_key:
            return self._mock_advice(health)

        # Get top categories
        from sqlalchemy import desc
        end = datetime.now(timezone.utc)
        top_cats = db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        ).filter(
            Transaction.business_id == business_id,
            Transaction.transaction_type == "EXPENSE",
            Transaction.date >= end - timedelta(days=30),
        ).group_by(Transaction.category).order_by(desc("total")).limit(3).all()

        cat_str = "، ".join([f"{c[0] or 'أخرى'}: {c[1]:,.0f} ر.س" for c in top_cats]) if top_cats else "لا يوجد"

        prompt = f"""أنت مستشار مالي خبير للمنشآت الصغيرة والمتوسطة في السعودية.

البيانات المالية للشهر الماضي:
- الإيرادات: {revenue:,.0f} ر.س
- المصاريف: {expenses:,.0f} ر.س
- هامش الربح: {margin}%
- مؤشر الصحة المالية: {health}/100
- أعلى فئات الإنفاق: {cat_str}

اكتب:
1. نصيحة أسبوعية مختصرة (3-4 جمل) باللغة العربية الفصحى
2. 3 مجالات تركيز مهمة (كل واحدة جملة قصيرة)
3. 3 إجراءات عملية فورية (كل واحدة جملة واحدة)

أجب بـ JSON فقط:
{{"advice": "...", "focus": ["...", "...", "..."], "actions": ["...", "...", "..."]}}"""

        try:
            msg = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            data = __import__("json").loads(raw)
            return data.get("advice", ""), data.get("focus", []), data.get("actions", [])
        except Exception:
            return self._mock_advice(health)

    def _mock_advice(self, health: int) -> tuple:
        advice = "بناءً على البيانات المالية لمنشأتك، نلاحظ أداءً جيداً في تحقيق الإيرادات. ننصح بمتابعة المصاريف التشغيلية بشكل دوري للحفاظ على هامش الربح. التخطيط المالي المسبق يساعدك على تجنب المفاجآت ويعزز استقرار منشأتك."
        focus = ["تحسين هامش الربح", "مراقبة المصاريف التشغيلية", "تنويع مصادر الإيراد"]
        actions = ["راجع فئات الإنفاق الأعلى وابحث عن فرص التوفير", "ضع ميزانية شهرية لكل فئة", "تابع الفواتير المعلقة وحصّل المستحقات"]
        return advice, focus, actions

financial_advisor = FinancialAdvisor()

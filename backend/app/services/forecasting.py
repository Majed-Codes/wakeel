"""
Cash Flow Forecasting Service — the core of Wakeel AI.

Uses Facebook Prophet for time-series forecasting when sufficient data exists,
falls back to simple moving average for sparse data, and returns mock data
when no transactions are available.

Bachmann: "Predict the future, but always show your confidence bounds.
A forecast without uncertainty is just a guess."
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

from app.config import settings
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Category sets — support both English and Arabic labels
REVENUE_CATEGORIES = {"Revenue", "إيرادات"}
EXPENSE_CATEGORIES = {"OpEx", "CapEx", "تشغيلية", "رأسمالية"}

# Prophet minimum threshold — below this, use moving average
PROPHET_MIN_TRANSACTIONS = 15


class ForecastingService:
    """خدمة التنبؤ بالتدفقات النقدية"""

    def __init__(self):
        self._anthropic_client = None
        if settings.has_anthropic_key:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("Forecasting insights: using Anthropic Claude")
            except ImportError:
                logger.warning("anthropic package not installed — insights will use fallback")

    # ── Main Forecast ────────────────────────────────────────────

    def generate_forecast(self, business_id: int, db, period_days: int = 90) -> dict:
        """
        Generate cash flow forecast for a business.

        Returns a ForecastResponse-compatible dict with:
        - revenue_forecast, expense_forecast, net_forecast (lists of ForecastPoint)
        - summary (ForecastSummary)
        """
        transactions = (
            db.query(Transaction)
            .filter(Transaction.business_id == business_id)
            .order_by(Transaction.date.asc())
            .all()
        )

        if not transactions:
            logger.info(f"Business {business_id}: no transactions — returning mock forecast")
            return self._mock_forecast(period_days)

        if len(transactions) < PROPHET_MIN_TRANSACTIONS:
            logger.info(
                f"Business {business_id}: {len(transactions)} transactions "
                f"(< {PROPHET_MIN_TRANSACTIONS}) — using moving average"
            )
            return self._moving_average_forecast(transactions, period_days)

        # Enough data — try Prophet
        return self._prophet_forecast(transactions, period_days)

    # ── Prophet Forecast ─────────────────────────────────────────

    def _prophet_forecast(self, transactions: list, period_days: int) -> dict:
        """Full Prophet-based forecast with Saudi seasonality and full preprocessing."""
        try:
            import pandas as pd
            from prophet import Prophet
        except ImportError:
            logger.warning("Prophet not installed — falling back to moving average")
            return self._moving_average_forecast(transactions, period_days)

        # Group transactions by date into revenue and expense time series
        daily_revenue, daily_expenses = self._aggregate_daily(transactions)

        # ── Full preprocessing pipeline ─────────────────────────────────────────
        # 1. Clip outliers (IQR × 3)
        # 2. Fill date gaps with 0
        # 3. Apply 7-day centered rolling smooth
        daily_revenue = self._preprocess_series(daily_revenue, "revenue")
        daily_expenses = self._preprocess_series(daily_expenses, "expenses")

        # Build DataFrames for Prophet (with log1p transform for right-skewed data)
        rev_df = self._to_prophet_df(daily_revenue, log_transform=True)
        exp_df = self._to_prophet_df(daily_expenses, log_transform=True)

        # Build Saudi holidays regressor
        holidays = self._make_saudi_holidays_df()

        # Train models
        rev_forecast = self._train_and_predict(rev_df, period_days, "revenue", holidays=holidays)
        exp_forecast = self._train_and_predict(exp_df, period_days, "expenses", holidays=holidays)

        # Compute net forecast
        net_forecast = []
        for r, e in zip(rev_forecast, exp_forecast):
            net_forecast.append({
                "date": r["date"],
                "value": round(r["value"] - e["value"], 2),
                "lower": round(r["lower"] - e["upper"], 2),
                "upper": round(r["upper"] - e["lower"], 2),
            })

        summary = self._compute_summary(rev_forecast, exp_forecast, net_forecast, transactions)

        return {
            "period_days": period_days,
            "revenue_forecast": rev_forecast,
            "expense_forecast": exp_forecast,
            "net_forecast": net_forecast,
            "summary": summary,
        }

    def _train_and_predict(
        self, df, period_days: int, series_name: str, holidays=None
    ) -> list:
        """
        Train a Prophet model and return forecast points.

        If the DataFrame was log-transformed (df.attrs['log_transformed'] == True),
        applies math.expm1 to reverse the transform on predicted values.
        Saudi holidays are passed as a Prophet-compatible holidays DataFrame.
        """
        import pandas as pd
        from prophet import Prophet

        log_transformed = df.attrs.get("log_transformed", False)

        model_kwargs = dict(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.80,
        )
        if holidays is not None:
            model_kwargs["holidays"] = holidays

        model = Prophet(**model_kwargs)

        # Add Saudi-specific seasonality
        # Ramadan effect (~30 days, shifts yearly in Gregorian calendar)
        model.add_seasonality(name="ramadan", period=354.37, fourier_order=5)
        # Summer seasonality (tourism / spending patterns)
        model.add_seasonality(name="summer", period=365.25, fourier_order=3)

        model.fit(df)

        future = model.make_future_dataframe(periods=period_days)
        prediction = model.predict(future)

        # Extract only the forecast period (last period_days rows)
        forecast_rows = prediction.tail(period_days)

        points = []
        for _, row in forecast_rows.iterrows():
            yhat = row["yhat"]
            yhat_lower = row["yhat_lower"]
            yhat_upper = row["yhat_upper"]

            # Inverse log1p transform — recover original scale
            if log_transformed:
                yhat = math.expm1(max(0.0, yhat))
                yhat_lower = math.expm1(max(0.0, yhat_lower))
                yhat_upper = math.expm1(max(0.0, yhat_upper))

            points.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "value": round(max(0.0, yhat), 2),
                "lower": round(max(0.0, yhat_lower), 2),
                "upper": round(max(0.0, yhat_upper), 2),
            })

        logger.info(
            f"Prophet [{series_name}]: trained on {len(df)} points, "
            f"log_transform={log_transformed}, holidays={'yes' if holidays is not None else 'no'}"
        )
        return points

    def _to_prophet_df(self, daily_data: dict, log_transform: bool = False):
        """
        Convert {date_str: value} dict to Prophet DataFrame.

        If log_transform=True, applies math.log1p to y values so Prophet
        learns on a log scale (better for right-skewed financial data).
        The transform flag is stored in df.attrs for inverse transform later.
        """
        import pandas as pd

        records = [{"ds": date_str, "y": value} for date_str, value in daily_data.items()]
        if not records:
            # Return minimal DataFrame with zero values
            today = datetime.now(timezone.utc).date()
            records = [{"ds": (today - timedelta(days=i)).isoformat(), "y": 0} for i in range(30)]

        df = pd.DataFrame(records)
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.sort_values("ds").reset_index(drop=True)

        if log_transform:
            # log1p is safe for 0 values; clip negatives just in case
            df["y"] = df["y"].apply(lambda x: math.log1p(max(0.0, x)))
            df.attrs["log_transformed"] = True
            logger.debug(f"Prophet DataFrame: applied log1p transform to {len(df)} rows")
        else:
            df.attrs["log_transformed"] = False

        return df

    # ── Moving Average Fallback ──────────────────────────────────

    def _moving_average_forecast(self, transactions: list, period_days: int) -> dict:
        """Simple moving average forecast for sparse data."""
        daily_revenue, daily_expenses = self._aggregate_daily(transactions)

        # Calculate averages
        avg_revenue = (
            sum(daily_revenue.values()) / max(len(daily_revenue), 1)
        )
        avg_expense = (
            sum(daily_expenses.values()) / max(len(daily_expenses), 1)
        )

        # If we have few distinct days, scale down to daily estimate
        # (transactions might all be on the same day)
        if transactions:
            date_range = self._date_range_days(transactions)
            if date_range > 0:
                total_rev = sum(daily_revenue.values())
                total_exp = sum(daily_expenses.values())
                avg_revenue = total_rev / date_range
                avg_expense = total_exp / date_range

        today = datetime.now(timezone.utc).date()

        # Add slight variation (+/- 10%) for bounds
        rev_forecast = []
        exp_forecast = []
        net_forecast = []

        for i in range(period_days):
            forecast_date = (today + timedelta(days=i + 1)).isoformat()

            rev_point = {
                "date": forecast_date,
                "value": round(avg_revenue, 2),
                "lower": round(avg_revenue * 0.9, 2),
                "upper": round(avg_revenue * 1.1, 2),
            }
            exp_point = {
                "date": forecast_date,
                "value": round(avg_expense, 2),
                "lower": round(avg_expense * 0.9, 2),
                "upper": round(avg_expense * 1.1, 2),
            }
            net_val = avg_revenue - avg_expense
            net_point = {
                "date": forecast_date,
                "value": round(net_val, 2),
                "lower": round(net_val * 0.9 if net_val >= 0 else net_val * 1.1, 2),
                "upper": round(net_val * 1.1 if net_val >= 0 else net_val * 0.9, 2),
            }

            rev_forecast.append(rev_point)
            exp_forecast.append(exp_point)
            net_forecast.append(net_point)

        summary = self._compute_summary(rev_forecast, exp_forecast, net_forecast, transactions)

        return {
            "period_days": period_days,
            "revenue_forecast": rev_forecast,
            "expense_forecast": exp_forecast,
            "net_forecast": net_forecast,
            "summary": summary,
        }

    # ── Mock Forecast ────────────────────────────────────────────

    def _mock_forecast(self, period_days: int) -> dict:
        """Return realistic mock forecast when no transactions exist."""
        today = datetime.now(timezone.utc).date()

        rev_forecast = []
        exp_forecast = []
        net_forecast = []

        # Mock: ~3000 SAR daily revenue, ~2000 SAR daily expenses
        base_revenue = 3000.0
        base_expense = 2000.0

        for i in range(period_days):
            forecast_date = (today + timedelta(days=i + 1)).isoformat()

            # Add slight wave pattern for realism
            import math
            wave = math.sin(i * 2 * math.pi / 30) * 200

            rev_val = base_revenue + wave
            exp_val = base_expense - wave * 0.5
            net_val = rev_val - exp_val

            rev_forecast.append({
                "date": forecast_date,
                "value": round(rev_val, 2),
                "lower": round(rev_val * 0.85, 2),
                "upper": round(rev_val * 1.15, 2),
            })
            exp_forecast.append({
                "date": forecast_date,
                "value": round(exp_val, 2),
                "lower": round(exp_val * 0.85, 2),
                "upper": round(exp_val * 1.15, 2),
            })
            net_forecast.append({
                "date": forecast_date,
                "value": round(net_val, 2),
                "lower": round(net_val * 0.8, 2),
                "upper": round(net_val * 1.2, 2),
            })

        summary = {
            "avg_daily_revenue": base_revenue,
            "avg_daily_expense": base_expense,
            "predicted_net_30d": round((base_revenue - base_expense) * 30, 2),
            "trend": "stable",
            "risk_level": "low",
        }

        return {
            "period_days": period_days,
            "revenue_forecast": rev_forecast,
            "expense_forecast": exp_forecast,
            "net_forecast": net_forecast,
            "summary": summary,
        }

    # ── Insights (Claude-powered) ────────────────────────────────

    def get_insights(self, business_id: int, db) -> dict:
        """
        Analyze forecast trends and generate actionable insights.
        Uses Claude for Arabic recommendations if API key is configured.

        Returns ForecastInsights-compatible dict.
        """
        transactions = (
            db.query(Transaction)
            .filter(Transaction.business_id == business_id)
            .order_by(Transaction.date.asc())
            .all()
        )

        # Compute basic trend analysis
        trend = self._analyze_trend(transactions)
        seasonal_patterns = self._detect_seasonal_patterns(transactions)
        risk_factors = self._assess_risks(transactions)

        # Generate recommendations — use Claude if available
        recommendations = self._generate_recommendations(
            transactions, trend, seasonal_patterns, risk_factors
        )

        return {
            "trend": trend,
            "seasonal_patterns": seasonal_patterns,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
        }

    def _analyze_trend(self, transactions: list) -> str:
        """Determine overall financial trend from transaction history."""
        if not transactions:
            return "stable"

        # Split into two halves and compare net income
        mid = len(transactions) // 2
        if mid == 0:
            return "stable"

        first_half = transactions[:mid]
        second_half = transactions[mid:]

        first_net = self._compute_net(first_half)
        second_net = self._compute_net(second_half)

        if second_net > first_net * 1.1:
            return "growing"
        elif second_net < first_net * 0.9:
            return "declining"
        return "stable"

    def _detect_seasonal_patterns(self, transactions: list) -> list:
        """Identify seasonal spending/revenue patterns."""
        patterns = []

        if not transactions:
            return ["لا توجد بيانات كافية لتحديد أنماط موسمية"]

        # Group by month
        monthly = defaultdict(float)
        for t in transactions:
            if t.date:
                month_key = t.date.strftime("%m")
                if t.category in REVENUE_CATEGORIES:
                    monthly[month_key] += t.amount
                elif t.category in EXPENSE_CATEGORIES:
                    monthly[month_key] -= t.amount

        if not monthly:
            return ["لا توجد بيانات كافية لتحديد أنماط موسمية"]

        avg_monthly = sum(monthly.values()) / len(monthly)

        # Identify high/low months
        for month, value in sorted(monthly.items()):
            month_names = {
                "01": "يناير", "02": "فبراير", "03": "مارس",
                "04": "أبريل", "05": "مايو", "06": "يونيو",
                "07": "يوليو", "08": "أغسطس", "09": "سبتمبر",
                "10": "أكتوبر", "11": "نوفمبر", "12": "ديسمبر",
            }
            month_name = month_names.get(month, month)
            if value > avg_monthly * 1.3:
                patterns.append(f"أداء مرتفع في {month_name}")
            elif value < avg_monthly * 0.7:
                patterns.append(f"أداء منخفض في {month_name}")

        if not patterns:
            patterns.append("أداء مالي مستقر عبر الأشهر")

        return patterns

    def _assess_risks(self, transactions: list) -> list:
        """Identify financial risk factors."""
        risks = []

        if not transactions:
            return ["لا توجد بيانات كافية لتقييم المخاطر"]

        total_revenue = sum(t.amount for t in transactions if t.category in REVENUE_CATEGORIES)
        total_expense = sum(t.amount for t in transactions if t.category in EXPENSE_CATEGORIES)

        # Risk: expenses exceed revenue
        if total_expense > total_revenue:
            risks.append("المصروفات تتجاوز الإيرادات — خطر على التدفق النقدي")

        # Risk: high vendor concentration
        vendor_totals = defaultdict(float)
        for t in transactions:
            if t.category in EXPENSE_CATEGORIES and t.vendor:
                vendor_totals[t.vendor] += t.amount
        if vendor_totals and total_expense > 0:
            max_vendor_pct = max(vendor_totals.values()) / total_expense
            if max_vendor_pct > 0.5:
                top_vendor = max(vendor_totals, key=vendor_totals.get)
                risks.append(f"تركّز عالي في المصروفات مع {top_vendor}")

        # Risk: low transaction volume
        if len(transactions) < 10:
            risks.append("عدد المعاملات منخفض — دقة التنبؤ محدودة")

        if not risks:
            risks.append("لا توجد مخاطر ملحوظة حالياً")

        return risks

    def _generate_recommendations(
        self, transactions: list, trend: str,
        seasonal_patterns: list, risk_factors: list,
    ) -> list:
        """Generate actionable recommendations. Uses Claude if available."""

        if self._anthropic_client and transactions:
            try:
                return self._claude_recommendations(
                    transactions, trend, seasonal_patterns, risk_factors
                )
            except Exception as e:
                logger.warning(f"Claude recommendations failed: {e} — using fallback")

        # Fallback: rule-based recommendations
        return self._fallback_recommendations(trend, risk_factors)

    def _claude_recommendations(
        self, transactions: list, trend: str,
        seasonal_patterns: list, risk_factors: list,
    ) -> list:
        """Use Claude to generate Arabic financial recommendations."""
        total_revenue = sum(t.amount for t in transactions if t.category in REVENUE_CATEGORIES)
        total_expense = sum(t.amount for t in transactions if t.category in EXPENSE_CATEGORIES)
        net = total_revenue - total_expense

        prompt = (
            f"أنت مستشار مالي سعودي. قدّم 3-4 توصيات عملية وقصيرة بالعربي.\n\n"
            f"البيانات:\n"
            f"- إجمالي الإيرادات: {total_revenue:,.0f} ر.س\n"
            f"- إجمالي المصروفات: {total_expense:,.0f} ر.س\n"
            f"- صافي: {net:,.0f} ر.س\n"
            f"- الاتجاه: {trend}\n"
            f"- الأنماط الموسمية: {', '.join(seasonal_patterns)}\n"
            f"- عوامل الخطر: {', '.join(risk_factors)}\n\n"
            f"اكتب كل توصية في سطر واحد. لا تستخدم ترقيم.\n"
            f"ركّز على نصائح عملية للمنشآت الصغيرة في السعودية."
        )

        response = self._anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )

        text = response.content[0].text
        recommendations = [
            line.strip() for line in text.strip().split("\n")
            if line.strip() and len(line.strip()) > 5
        ]

        return recommendations[:4]

    def _fallback_recommendations(self, trend: str, risk_factors: list) -> list:
        """Rule-based recommendations when Claude is not available."""
        recommendations = []

        if trend == "declining":
            recommendations.append("الإيرادات في تراجع — راجع استراتيجية التسعير وابحث عن مصادر دخل جديدة")
        elif trend == "growing":
            recommendations.append("النمو إيجابي — فكّر في استثمار جزء من الأرباح لتوسيع النشاط")

        for risk in risk_factors:
            if "المصروفات تتجاوز" in risk:
                recommendations.append("خفّض المصاريف غير الضرورية وراقب التدفق النقدي أسبوعياً")
            if "تركّز عالي" in risk:
                recommendations.append("نوّع الموردين لتقليل مخاطر الاعتماد على مورد واحد")
            if "عدد المعاملات منخفض" in risk:
                recommendations.append("سجّل جميع المعاملات بانتظام لتحسين دقة التنبؤات")

        if not recommendations:
            recommendations.append("حافظ على مستوى الأداء الحالي وراقب التدفق النقدي شهرياً")

        return recommendations

    # ── Preprocessing Pipeline ────────────────────────────────────

    def _preprocess_series(self, daily_data: dict, series_name: str = "") -> dict:
        """
        Full preprocessing pipeline for a daily financial time series.

        Steps (applied in order):
        1. Clip outliers using IQR × 3 (conservative — clips, doesn't remove)
        2. Fill missing dates with 0.0 (Prophet needs a continuous date index)
        3. Apply 7-day centered rolling mean (reduces day-to-day noise)

        Returns the preprocessed {date_str: float} dict.
        """
        logger.info(
            f"Preprocessing [{series_name}]: starting with {len(daily_data)} data points"
        )
        daily_data = self._clip_outliers_iqr(daily_data, series_name)
        daily_data = self._fill_date_gaps(daily_data, series_name)
        daily_data = self._rolling_smooth(daily_data, window=7, series_name=series_name)
        logger.info(
            f"Preprocessing [{series_name}]: done → {len(daily_data)} data points"
        )
        return daily_data

    def _clip_outliers_iqr(self, daily_data: dict, series_name: str = "") -> dict:
        """
        Clip extreme values using the IQR method.

        Uses 3 × IQR for the upper fence (less aggressive than the standard 1.5 ×
        because financial data has legitimate large transactions).
        Values are *clipped*, not removed — preserving time-series continuity.
        """
        if len(daily_data) < 4:
            return daily_data  # Not enough data to compute a meaningful IQR

        values = sorted(daily_data.values())
        n = len(values)

        # Quartile indices (simple positional)
        q1 = values[n // 4]
        q3 = values[(3 * n) // 4]
        iqr = q3 - q1

        upper_fence = q3 + 3.0 * iqr
        lower_fence = max(0.0, q1 - 1.5 * iqr)  # Financial amounts can't be negative

        clipped = {}
        clipped_count = 0
        for date_str, value in daily_data.items():
            new_val = max(lower_fence, min(value, upper_fence))
            if new_val != value:
                clipped_count += 1
            clipped[date_str] = new_val

        if clipped_count:
            logger.info(
                f"Preprocessing [{series_name}]: clipped {clipped_count} outlier(s) "
                f"(IQR × 3, fence=[{lower_fence:.0f}, {upper_fence:.0f}])"
            )
        return clipped

    def _fill_date_gaps(self, daily_data: dict, series_name: str = "") -> dict:
        """
        Fill missing dates with 0.0 to produce a continuous daily time series.

        Prophet performs better without gaps — missing revenue/expense days
        genuinely mean zero activity, so 0 is the correct fill value.
        """
        if not daily_data:
            return daily_data

        # Parse all dates, find full range
        dates = sorted(
            datetime.strptime(d, "%Y-%m-%d").date() for d in daily_data
        )
        start, end = dates[0], dates[-1]

        filled: dict = {}
        filled_count = 0
        current = start
        while current <= end:
            date_str = current.isoformat()
            filled[date_str] = daily_data.get(date_str, 0.0)
            if date_str not in daily_data:
                filled_count += 1
            current += timedelta(days=1)

        if filled_count:
            logger.info(
                f"Preprocessing [{series_name}]: filled {filled_count} missing date(s) with 0"
            )
        return filled

    def _rolling_smooth(
        self, daily_data: dict, window: int = 7, series_name: str = ""
    ) -> dict:
        """
        Apply a centered rolling mean to reduce daily noise.

        Requires at least 3 × window data points — smaller datasets are returned
        unchanged (smoothing would distort sparse data).
        """
        if len(daily_data) < window * 3:
            logger.info(
                f"Preprocessing [{series_name}]: skipping rolling smooth "
                f"(need {window * 3} points, have {len(daily_data)})"
            )
            return daily_data

        sorted_items = sorted(daily_data.items())  # chronological order
        dates = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]

        half = window // 2
        smoothed: list = []
        for i in range(len(values)):
            start_idx = max(0, i - half)
            end_idx = min(len(values), i + half + 1)
            window_vals = values[start_idx:end_idx]
            smoothed.append(sum(window_vals) / len(window_vals))

        logger.info(
            f"Preprocessing [{series_name}]: applied {window}-day centered rolling smooth"
        )
        return dict(zip(dates, smoothed))

    def _make_saudi_holidays_df(self):
        """
        Build a Prophet-compatible holidays DataFrame for Saudi Arabia (2020–2030).

        Includes:
        - اليوم الوطني السعودي  (National Day)  — Sep 23 every year
        - يوم التأسيس           (Founding Day)  — Feb 22 from 2022
        - عيد الفطر             (Eid Al-Fitr)   — approximate Hijri → Gregorian
        - عيد الأضحى            (Eid Al-Adha)   — approximate Hijri → Gregorian

        Prophet uses lower_window / upper_window (days before/after) to capture
        the spending pattern around each holiday.
        """
        import pandas as pd

        rows = []

        # ── Fixed Gregorian holidays ────────────────────────────────────────────
        fixed_holidays = {
            "اليوم الوطني السعودي": ("09-23", range(2020, 2031), -1, 2),
            "يوم التأسيس":          ("02-22", range(2022, 2031), -1, 1),
        }
        for name, (month_day, years, lo, hi) in fixed_holidays.items():
            for year in years:
                rows.append({
                    "holiday": name,
                    "ds": pd.Timestamp(f"{year}-{month_day}"),
                    "lower_window": lo,
                    "upper_window": hi,
                })

        # ── Hijri holidays (approximate Gregorian dates, shifts ~11 d/year) ─────
        # Eid Al-Fitr: first day of Shawwal
        eid_fitr_dates = [
            "2020-05-24", "2021-05-13", "2022-05-02", "2023-04-21",
            "2024-04-10", "2025-03-30", "2026-03-20", "2027-03-09",
            "2028-02-26", "2029-02-14", "2030-02-04",
        ]
        # Eid Al-Adha: 10th of Dhul Hijja
        eid_adha_dates = [
            "2020-07-31", "2021-07-20", "2022-07-09", "2023-06-28",
            "2024-06-16", "2025-06-06", "2026-05-26", "2027-05-16",
            "2028-05-04", "2029-04-24", "2030-04-13",
        ]

        for date_str in eid_fitr_dates:
            rows.append({
                "holiday": "عيد الفطر",
                "ds": pd.Timestamp(date_str),
                "lower_window": -3,   # 3 days pre-holiday spending spike
                "upper_window": 6,    # 6 days holiday period
            })
        for date_str in eid_adha_dates:
            rows.append({
                "holiday": "عيد الأضحى",
                "ds": pd.Timestamp(date_str),
                "lower_window": -3,
                "upper_window": 6,
            })

        holidays_df = pd.DataFrame(rows)
        logger.debug(f"Saudi holidays: {len(holidays_df)} holiday entries loaded")
        return holidays_df

    # ── Helpers ───────────────────────────────────────────────────

    def _aggregate_daily(self, transactions: list) -> tuple:
        """
        Group transactions by date into daily revenue and expense totals.
        Returns (daily_revenue, daily_expenses) as {date_str: float} dicts.
        """
        daily_revenue = defaultdict(float)
        daily_expenses = defaultdict(float)

        for t in transactions:
            if not t.date:
                continue
            date_key = t.date.strftime("%Y-%m-%d") if isinstance(t.date, datetime) else str(t.date)[:10]

            if t.category in REVENUE_CATEGORIES:
                daily_revenue[date_key] += t.amount
            elif t.category in EXPENSE_CATEGORIES:
                daily_expenses[date_key] += t.amount

        return dict(daily_revenue), dict(daily_expenses)

    def _compute_net(self, transactions: list) -> float:
        """Compute net income (revenue - expenses) for a list of transactions."""
        revenue = sum(t.amount for t in transactions if t.category in REVENUE_CATEGORIES)
        expenses = sum(t.amount for t in transactions if t.category in EXPENSE_CATEGORIES)
        return revenue - expenses

    def _date_range_days(self, transactions: list) -> int:
        """Compute the date range in days across transactions."""
        dates = [t.date for t in transactions if t.date]
        if len(dates) < 2:
            return 1
        min_date = min(dates)
        max_date = max(dates)
        delta = (max_date - min_date).days
        return max(delta, 1)

    def _compute_summary(
        self, rev_forecast: list, exp_forecast: list,
        net_forecast: list, transactions: list,
    ) -> dict:
        """
        Compute ForecastSummary from forecast data.

        - avg_daily_revenue, avg_daily_expense from forecast
        - predicted_net_30d = sum of net forecast for first 30 days
        - trend: compare last 30 days actual vs next 30 days predicted
        - risk_level: "high" if predicted net < 0, "medium" if declining, "low" if growing
        """
        # Averages from full forecast
        avg_rev = (
            sum(p["value"] for p in rev_forecast) / max(len(rev_forecast), 1)
        )
        avg_exp = (
            sum(p["value"] for p in exp_forecast) / max(len(exp_forecast), 1)
        )

        # Sum net for first 30 days
        net_30 = sum(p["value"] for p in net_forecast[:30])

        # Trend: compare actual historical net vs predicted net
        actual_net = self._compute_net(transactions) if transactions else 0
        predicted_avg = avg_rev - avg_exp

        if transactions and actual_net != 0:
            change_ratio = predicted_avg / max(abs(actual_net / max(len(transactions), 1)), 0.01)
            if change_ratio > 1.1:
                trend = "growing"
            elif change_ratio < 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Risk level
        if net_30 < 0:
            risk_level = "high"
        elif trend == "declining":
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "avg_daily_revenue": round(avg_rev, 2),
            "avg_daily_expense": round(avg_exp, 2),
            "predicted_net_30d": round(net_30, 2),
            "trend": trend,
            "risk_level": risk_level,
        }


# Singleton instance
forecasting_service = ForecastingService()

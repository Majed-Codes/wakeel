"""Tests for cash flow forecasting — the core feature of Wakeel AI."""

import pytest
from unittest.mock import patch, MagicMock


class TestForecastEndpoints:

    def test_forecast_requires_auth(self, client):
        response = client.get("/api/v1/forecast/")
        assert response.status_code in (401, 403)

    def test_forecast_empty_no_transactions(self, client, auth_headers):
        """With no transactions, returns mock forecast data."""
        response = client.get("/api/v1/forecast/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "revenue_forecast" in data
        assert "expense_forecast" in data
        assert "net_forecast" in data
        assert "summary" in data
        assert data["period_days"] == 30

    def test_forecast_with_transactions(self, client, auth_headers, sample_transactions):
        """With transactions, forecast returns valid data."""
        response = client.get("/api/v1/forecast/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["revenue_forecast"]) == 30
        assert len(data["expense_forecast"]) == 30
        assert len(data["net_forecast"]) == 30

    def test_forecast_summary_fields(self, client, auth_headers):
        """Summary has all required fields."""
        response = client.get("/api/v1/forecast/", headers=auth_headers)
        assert response.status_code == 200
        summary = response.json()["summary"]
        assert "avg_daily_revenue" in summary
        assert "avg_daily_expense" in summary
        assert "predicted_net_30d" in summary
        assert "trend" in summary
        assert "risk_level" in summary
        assert summary["trend"] in ("growing", "stable", "declining")
        assert summary["risk_level"] in ("low", "medium", "high")

    def test_forecast_period_30(self, client, auth_headers):
        response = client.get("/api/v1/forecast/?period_days=30", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["period_days"] == 30
        assert len(response.json()["revenue_forecast"]) == 30

    def test_forecast_period_60(self, client, auth_headers):
        response = client.get("/api/v1/forecast/?period_days=60", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["period_days"] == 60
        assert len(response.json()["revenue_forecast"]) == 60

    def test_forecast_period_90(self, client, auth_headers):
        response = client.get("/api/v1/forecast/?period_days=90", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["period_days"] == 90

    def test_forecast_points_have_bounds(self, client, auth_headers):
        """Each forecast point has date, value, lower, upper."""
        response = client.get("/api/v1/forecast/", headers=auth_headers)
        assert response.status_code == 200
        points = response.json()["revenue_forecast"]
        assert len(points) > 0
        point = points[0]
        assert "date" in point
        assert "value" in point
        assert "lower" in point
        assert "upper" in point
        assert point["upper"] >= point["value"] >= point["lower"]

    def test_forecast_insights_requires_auth(self, client):
        response = client.get("/api/v1/forecast/insights")
        assert response.status_code in (401, 403)

    def test_forecast_insights_fields(self, client, auth_headers):
        """Insights returns all required fields."""
        response = client.get("/api/v1/forecast/insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "trend" in data
        assert "seasonal_patterns" in data
        assert "risk_factors" in data
        assert "recommendations" in data
        assert isinstance(data["seasonal_patterns"], list)
        assert isinstance(data["risk_factors"], list)
        assert isinstance(data["recommendations"], list)

    def test_forecast_insights_with_transactions(self, client, auth_headers, sample_transactions):
        """Insights includes non-empty patterns."""
        response = client.get("/api/v1/forecast/insights", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["risk_factors"]) > 0
        assert len(data["recommendations"]) > 0


class TestForecastingService:

    def test_mock_forecast_structure(self):
        """Mock forecast returns correct structure."""
        from app.services.forecasting import ForecastingService
        service = ForecastingService()
        result = service._mock_forecast(30)
        assert result["period_days"] == 30
        assert len(result["revenue_forecast"]) == 30
        assert len(result["expense_forecast"]) == 30
        assert len(result["net_forecast"]) == 30

    def test_mock_forecast_positive_values(self):
        """Mock revenue and expenses are positive."""
        from app.services.forecasting import ForecastingService
        service = ForecastingService()
        result = service._mock_forecast(30)
        for point in result["revenue_forecast"]:
            assert point["value"] > 0
        for point in result["expense_forecast"]:
            assert point["value"] > 0

    def test_moving_average_with_transactions(self, db, test_business, sample_transactions):
        """Moving average fallback works with sparse transactions."""
        from app.services.forecasting import ForecastingService
        service = ForecastingService()
        result = service.generate_forecast(test_business.id, db, period_days=30)
        assert result["period_days"] == 30
        assert len(result["revenue_forecast"]) == 30

    def test_analyze_trend_empty(self):
        from app.services.forecasting import ForecastingService
        service = ForecastingService()
        assert service._analyze_trend([]) == "stable"

    def test_assess_risks_empty(self):
        from app.services.forecasting import ForecastingService
        service = ForecastingService()
        risks = service._assess_risks([])
        assert len(risks) > 0  # Returns "not enough data" message

    def test_compute_summary_structure(self):
        from app.services.forecasting import ForecastingService
        service = ForecastingService()
        rev = [{"date": "2024-01-01", "value": 1000, "lower": 900, "upper": 1100}] * 30
        exp = [{"date": "2024-01-01", "value": 800, "lower": 720, "upper": 880}] * 30
        net = [{"date": "2024-01-01", "value": 200, "lower": 180, "upper": 220}] * 30
        summary = service._compute_summary(rev, exp, net, [])
        assert "avg_daily_revenue" in summary
        assert "avg_daily_expense" in summary
        assert "predicted_net_30d" in summary
        assert summary["avg_daily_revenue"] == 1000.0
        assert summary["avg_daily_expense"] == 800.0


class TestForecastPreprocessing:
    """Tests for the full preprocessing pipeline added to ForecastingService."""

    def _make_service(self):
        from app.services.forecasting import ForecastingService
        return ForecastingService()

    # ── _clip_outliers_iqr ─────────────────────────────────────────────────────

    def test_clip_outliers_iqr_clips_extreme_values(self):
        """Extreme outliers are clipped to the IQR upper fence."""
        service = self._make_service()
        # 8 normal values around 1000 + one extreme outlier (100 000)
        data = {
            "2024-01-01": 900.0, "2024-01-02": 950.0, "2024-01-03": 1000.0,
            "2024-01-04": 1050.0, "2024-01-05": 980.0, "2024-01-06": 1020.0,
            "2024-01-07": 970.0, "2024-01-08": 100_000.0,  # outlier
        }
        result = service._clip_outliers_iqr(data, "test")
        assert result["2024-01-08"] < 10_000, "Outlier should be clipped down"
        # Normal values should be unchanged
        assert result["2024-01-01"] == 900.0

    def test_clip_outliers_iqr_non_negative(self):
        """Clipped values should never be negative."""
        service = self._make_service()
        data = {str(i): float(i * 10) for i in range(1, 20)}
        result = service._clip_outliers_iqr(data, "test")
        for v in result.values():
            assert v >= 0.0, "Clipped values must be non-negative"

    def test_clip_outliers_iqr_too_few_points_unchanged(self):
        """Less than 4 data points → returned unchanged."""
        service = self._make_service()
        data = {"2024-01-01": 500.0, "2024-01-02": 99999.0, "2024-01-03": 300.0}
        result = service._clip_outliers_iqr(data, "test")
        assert result == data

    # ── _fill_date_gaps ────────────────────────────────────────────────────────

    def test_fill_date_gaps_fills_missing_dates(self):
        """Missing dates between start and end are filled with 0."""
        service = self._make_service()
        data = {
            "2024-01-01": 1000.0,
            "2024-01-05": 2000.0,  # gap: Jan 2, 3, 4 are missing
        }
        result = service._fill_date_gaps(data, "test")
        assert len(result) == 5  # Jan 1 through Jan 5
        assert result["2024-01-02"] == 0.0
        assert result["2024-01-03"] == 0.0
        assert result["2024-01-04"] == 0.0
        # Original values preserved
        assert result["2024-01-01"] == 1000.0
        assert result["2024-01-05"] == 2000.0

    def test_fill_date_gaps_no_gaps_unchanged(self):
        """Consecutive dates → same data returned."""
        service = self._make_service()
        data = {
            "2024-01-01": 100.0,
            "2024-01-02": 200.0,
            "2024-01-03": 300.0,
        }
        result = service._fill_date_gaps(data, "test")
        assert result == data

    def test_fill_date_gaps_empty_returns_empty(self):
        """Empty dict → empty dict returned."""
        service = self._make_service()
        assert service._fill_date_gaps({}, "test") == {}

    def test_fill_date_gaps_preserves_order(self):
        """Result dict keys are in chronological order."""
        service = self._make_service()
        data = {"2024-01-10": 500.0, "2024-01-01": 100.0}
        result = service._fill_date_gaps(data, "test")
        keys = list(result.keys())
        assert keys == sorted(keys)

    # ── _rolling_smooth ────────────────────────────────────────────────────────

    def test_rolling_smooth_reduces_spike(self):
        """A single-day spike is smoothed towards neighbours."""
        service = self._make_service()
        # 30 days of 100, with one spike at day 15 → 10 000
        data = {}
        from datetime import date, timedelta
        base = date(2024, 1, 1)
        for i in range(30):
            d = (base + timedelta(days=i)).isoformat()
            data[d] = 10_000.0 if i == 14 else 100.0

        result = service._rolling_smooth(data, window=7, series_name="test")
        spike_key = (base + timedelta(days=14)).isoformat()
        # Smoothed spike should be much less than 10 000
        assert result[spike_key] < 5_000.0

    def test_rolling_smooth_too_few_points_unchanged(self):
        """Less than 3× window points → data returned unchanged."""
        service = self._make_service()
        from datetime import date, timedelta
        base = date(2024, 1, 1)
        data = {(base + timedelta(days=i)).isoformat(): float(i * 10) for i in range(10)}
        # window=7 → need 21+ points; we only have 10
        result = service._rolling_smooth(data, window=7, series_name="test")
        assert result == data

    def test_rolling_smooth_preserves_length(self):
        """Output has the same number of dates as input."""
        service = self._make_service()
        from datetime import date, timedelta
        base = date(2024, 1, 1)
        data = {(base + timedelta(days=i)).isoformat(): float(i) for i in range(30)}
        result = service._rolling_smooth(data, window=7, series_name="test")
        assert len(result) == len(data)

    # ── _preprocess_series ─────────────────────────────────────────────────────

    def test_preprocess_series_returns_dict(self):
        """Pipeline returns a dict."""
        service = self._make_service()
        from datetime import date, timedelta
        base = date(2024, 1, 1)
        data = {(base + timedelta(days=i)).isoformat(): float(i * 50) for i in range(30)}
        result = service._preprocess_series(data, "test")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_preprocess_series_fills_gaps(self):
        """Pipeline fills date gaps introduced by sparse input."""
        service = self._make_service()
        data = {"2024-01-01": 500.0, "2024-01-15": 800.0}
        result = service._preprocess_series(data, "test")
        # Should have 15 days (Jan 1–15) after gap filling
        assert len(result) == 15

    def test_preprocess_series_no_negative_values(self):
        """Pipeline never produces negative values."""
        service = self._make_service()
        from datetime import date, timedelta
        base = date(2024, 1, 1)
        data = {(base + timedelta(days=i)).isoformat(): float(i * 30 + 1) for i in range(40)}
        result = service._preprocess_series(data, "test")
        for v in result.values():
            assert v >= 0.0

    # ── _make_saudi_holidays_df ────────────────────────────────────────────────

    def test_make_saudi_holidays_df_structure(self):
        """Returns a DataFrame with required Prophet columns."""
        pytest.importorskip("pandas")
        service = self._make_service()
        df = service._make_saudi_holidays_df()
        assert "holiday" in df.columns
        assert "ds" in df.columns
        assert "lower_window" in df.columns
        assert "upper_window" in df.columns

    def test_make_saudi_holidays_df_contains_eid(self):
        """DataFrame includes Eid holidays."""
        pytest.importorskip("pandas")
        service = self._make_service()
        df = service._make_saudi_holidays_df()
        holiday_names = df["holiday"].unique().tolist()
        assert "عيد الفطر" in holiday_names
        assert "عيد الأضحى" in holiday_names

    def test_make_saudi_holidays_df_contains_national_day(self):
        """DataFrame includes National Day and Founding Day."""
        pytest.importorskip("pandas")
        service = self._make_service()
        df = service._make_saudi_holidays_df()
        holiday_names = df["holiday"].unique().tolist()
        assert "اليوم الوطني السعودي" in holiday_names
        assert "يوم التأسيس" in holiday_names

    def test_make_saudi_holidays_df_minimum_rows(self):
        """At least 30 holiday entries across 2020–2030."""
        pytest.importorskip("pandas")
        service = self._make_service()
        df = service._make_saudi_holidays_df()
        assert len(df) >= 30

    # ── _to_prophet_df log transform ──────────────────────────────────────────

    def test_to_prophet_df_log_transform_applied(self):
        """log_transform=True applies log1p to y column."""
        import math
        pytest.importorskip("pandas")
        service = self._make_service()
        data = {
            "2024-01-01": 1000.0,
            "2024-01-02": 2000.0,
            "2024-01-03": 500.0,
        }
        df = service._to_prophet_df(data, log_transform=True)
        assert df.attrs.get("log_transformed") is True
        # First value: log1p(1000) ≈ 6.908
        assert abs(df["y"].iloc[0] - math.log1p(1000.0)) < 0.001

    def test_to_prophet_df_no_transform(self):
        """log_transform=False leaves y values unchanged."""
        pytest.importorskip("pandas")
        service = self._make_service()
        data = {"2024-01-01": 1000.0, "2024-01-02": 2000.0}
        df = service._to_prophet_df(data, log_transform=False)
        assert df.attrs.get("log_transformed") is False
        assert df["y"].iloc[0] == pytest.approx(1000.0) or df["y"].iloc[1] == pytest.approx(1000.0)

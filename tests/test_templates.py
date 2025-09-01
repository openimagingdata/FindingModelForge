"""Unit tests for template configuration and custom filters."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.templates import humanize_time, templates


class TestHumanizeTime:
    """Test humanize_time filter function."""

    def test_none_returns_empty_string(self):
        """Test that None input returns empty string."""
        result = humanize_time(None)
        assert result == ""

    @patch("app.templates.datetime")
    def test_five_minutes_ago(self, mock_datetime):
        """Test datetime from 5 minutes ago."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        five_minutes_ago = mock_now - timedelta(minutes=5)
        result = humanize_time(five_minutes_ago)

        # Should contain "5 minutes ago" or similar
        assert "ago" in result
        assert "minute" in result

    @patch("app.templates.datetime")
    def test_two_hours_ago(self, mock_datetime):
        """Test datetime from 2 hours ago."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        two_hours_ago = mock_now - timedelta(hours=2)
        result = humanize_time(two_hours_ago)

        # Should contain "2 hours ago" or similar
        assert "ago" in result
        assert "hour" in result

    @patch("app.templates.datetime")
    def test_yesterday(self, mock_datetime):
        """Test datetime from yesterday."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        yesterday = mock_now - timedelta(days=1)
        result = humanize_time(yesterday)

        # Should contain "day ago" or similar
        assert "ago" in result
        assert "day" in result

    @patch("app.templates.datetime")
    def test_timezone_naive_datetime_gets_utc(self, mock_datetime):
        """Test that timezone-naive datetime gets UTC timezone added."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Create timezone-naive datetime
        naive_dt = datetime(2024, 1, 1, 11, 55, 0)  # 5 minutes ago, but naive
        result = humanize_time(naive_dt)

        # Should not raise any timezone-related errors
        assert isinstance(result, str)
        assert "ago" in result

    @patch("app.templates.datetime")
    def test_timezone_aware_datetime_preserved(self, mock_datetime):
        """Test that timezone-aware datetime is handled correctly."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Create timezone-aware datetime
        aware_dt = datetime(2024, 1, 1, 11, 55, 0, tzinfo=UTC)
        result = humanize_time(aware_dt)

        assert isinstance(result, str)
        assert "ago" in result

    @patch("app.templates.datetime")
    def test_future_datetime(self, mock_datetime):
        """Test datetime in the future."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        future_dt = mock_now + timedelta(hours=2)
        result = humanize_time(future_dt)

        # Should handle future times gracefully
        assert isinstance(result, str)
        # Humanize library should say "in 2 hours" or similar
        assert "in" in result or "from now" in result

    @patch("app.templates.datetime")
    def test_empty_string_datetime_handled(self, mock_datetime):
        """Test that function handles edge cases gracefully."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Test with current time (should be "now" or similar)
        result = humanize_time(mock_now)
        assert isinstance(result, str)
        # Could be "now", "a moment ago", etc.
        assert len(result) > 0


class TestTemplatesInitialization:
    """Test template initialization and filter registration."""

    def test_templates_object_created(self):
        """Test that templates object is properly created."""
        assert templates is not None
        assert hasattr(templates, "env")
        assert hasattr(templates.env, "filters")

    def test_humanize_filter_registered(self):
        """Test that humanize filter is registered with templates."""
        assert "humanize" in templates.env.filters
        assert templates.env.filters["humanize"] is humanize_time

    def test_filter_name_is_humanize(self):
        """Test that the filter is accessible by name 'humanize'."""
        filter_func = templates.env.filters.get("humanize")
        assert filter_func is not None
        assert callable(filter_func)

    def test_templates_directory_configured(self):
        """Test that templates directory is properly configured."""
        # The templates object should have the loader configured
        # Jinja2Templates stores directory info in env.loader
        assert hasattr(templates.env, "loader")
        assert templates.env.loader is not None

    def test_humanize_filter_can_be_called_through_templates(self):
        """Test that the filter can be accessed through the templates environment."""
        # This tests the integration - that the filter is properly bound
        filter_func = templates.env.filters["humanize"]

        # Test it with a simple case
        test_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        with patch("app.templates.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 5, 0, tzinfo=UTC)  # 5 minutes later
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = filter_func(test_dt)
            assert isinstance(result, str)
            assert "ago" in result

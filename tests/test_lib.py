from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from werkzeug.exceptions import HTTPException

from chrono_des_vignes.lib import (
    assert400,
    calc_points_dist,
    create_gcalendar_link,
    deg_to_dms,
    format_timedelta,
    is_valide_name,
    midpoint,
)


def test_assert400_raises_http_exception_for_none():
    with pytest.raises(HTTPException) as exc:
        assert400(None)
    assert exc.value.code == 400


def test_is_valide_name_rejects_invalid_characters():
    assert not is_valide_name("name with spaces")
    assert not is_valide_name("name/with/slash")
    assert is_valide_name("valid-name_123")


def test_is_valide_name_respects_length_limits():
    assert not is_valide_name("", min_length=1)
    assert not is_valide_name("abc", max_length=2)
    assert is_valide_name("abc", min_length=1, max_length=5)


def test_midpoint_returns_center_point():
    assert midpoint((0.0, 0.0), (2.0, 4.0)) == (1.0, 2.0)


def test_calc_points_dist_returns_approximate_km():
    distance = calc_points_dist(0.0, 0.0, 0.0, 1.0)
    assert pytest.approx(111.0, rel=0.01) == distance


def test_deg_to_dms_positive_and_negative():
    assert deg_to_dms(12.5) == (12, 30, 0.0)
    assert deg_to_dms(-0.5) == (0, 30, 0.0)


def test_format_timedelta_formats_days_and_time():
    delta = timedelta(days=1, hours=2, minutes=3, seconds=4)
    assert format_timedelta(delta) == "1 jours, 02:03:04"
    assert format_timedelta(timedelta(hours=2, minutes=4, seconds=5)) == "02:04:05"


def test_create_gcalendar_link_encodes_parameters():
    start = datetime(2026, 8, 1, 9, 15, 0)
    end = datetime(2026, 8, 1, 10, 15, 0)
    link = create_gcalendar_link(
        title="Test Event",
        start=start,
        end=end,
        detail="A test description",
        location="My Place",
    )

    assert "calendar.google.com" in link
    assert "text=Test+Event" in link
    assert "details=A%20test%20description" in link
    assert "location=My%20Place" in link

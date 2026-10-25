from __future__ import annotations

import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from motor_editorial.radar_policy import (
    next_daily_window_utc,
    normalize_domain_quotas,
    parse_local_time,
)


class RadarPolicyTests(unittest.TestCase):
    def test_sao_paulo_local_window_is_stored_as_utc(self) -> None:
        due = next_daily_window_utc(
            "08:00", "America/Sao_Paulo", "2026-01-01T00:00:00+00:00"
        )
        self.assertEqual(due, datetime(2026, 1, 1, 11, tzinfo=timezone.utc))
        tomorrow = next_daily_window_utc(
            "08:00", "America/Sao_Paulo", due, include_equal=False
        )
        self.assertEqual(tomorrow, datetime(2026, 1, 2, 11, tzinfo=timezone.utc))

    def test_dst_gap_shifts_nonexistent_local_time_forward_by_gap(self) -> None:
        due = next_daily_window_utc(
            "02:30", "America/New_York", "2024-03-10T00:00:00+00:00"
        )
        self.assertEqual(due, datetime(2024, 3, 10, 7, 30, tzinfo=timezone.utc))
        self.assertEqual(due.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M"), "03:30")

    def test_dst_fold_uses_first_occurrence_and_never_duplicates_local_day(self) -> None:
        first = next_daily_window_utc(
            "01:30", "America/New_York", "2024-11-03T04:00:00+00:00"
        )
        self.assertEqual(first, datetime(2024, 11, 3, 5, 30, tzinfo=timezone.utc))
        after_fold = next_daily_window_utc(
            "01:30", "America/New_York", "2024-11-03T06:00:00+00:00",
            include_equal=False,
        )
        self.assertEqual(after_fold, datetime(2024, 11, 4, 6, 30, tzinfo=timezone.utc))

    def test_local_time_and_daily_domain_quota_validation(self) -> None:
        self.assertEqual(parse_local_time("23:59").strftime("%H:%M"), "23:59")
        with self.assertRaises(ValueError):
            parse_local_time("24:00")
        self.assertEqual(
            normalize_domain_quotas({"NEWS.EXAMPLE.INVALID.": 3}),
            {"news.example.invalid": 3},
        )
        with self.assertRaisesRegex(ValueError, "positivo"):
            normalize_domain_quotas({"example.invalid": True})
        with self.assertRaisesRegex(ValueError, "duplicados"):
            normalize_domain_quotas({"NEWS.EXAMPLE.INVALID": 3, "news.example.invalid.": 4})


if __name__ == "__main__":
    unittest.main()

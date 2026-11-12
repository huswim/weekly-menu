"""Regression tests for weekly-menu PDF allergen validation."""
import datetime as dt
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update-menu.py"
spec = importlib.util.spec_from_file_location("update_menu", SCRIPT)
update_menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_menu)


class FakePage:
    def __init__(self, day, weekday, menu_row):
        self.day = day
        self.weekday = weekday
        self.menu_row = menu_row

    def extract_text(self):
        return (
            f"11/{self.day}({self.weekday}) 알레르기\n"
            f"구분 메뉴\n조식 {self.menu_row}\n"
            "알레르기 유발물질이 포함"
        )


class PdfAllergenTests(unittest.TestCase):
    def parse_week(self, menu_row):
        pages = [object()] + [
            FakePage(16 + i, weekday, menu_row)
            for i, weekday in enumerate("월화수목금")
        ]
        with patch.object(update_menu, "PdfReader") as reader:
            reader.return_value.pages = pages
            return update_menu.parse_pdf(
                b"%PDF-test", dt.date(2026, 11, 16), dt.date(2026, 11, 20)
            )

    def test_beef_allergen_spellings(self):
        for label in ("소고기", "쇠고기"):
            with self.subTest(label=label):
                allergy = f"{label}, 난류, 대두, 밀, 닭고기"
                days = self.parse_week(f"소보로메추리알조림 {allergy}")
                item = days[0]["meals"][0]["corners"][0]["items"][0]
                self.assertEqual(item, {
                    "name": "소보로메추리알조림", "allergy": allergy
                })

    def test_unrecognized_allergen_still_fails(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized PDF row"):
            self.parse_week("소보로메추리알조림 소고기, 알수없는성분")


if __name__ == "__main__":
    unittest.main()

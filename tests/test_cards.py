import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from profile_cards import activity, hero, links, stack, stats, waka


def days(count, start=date(2026, 1, 1)):
    return [((start + timedelta(days=i)).isoformat(), i % 7) for i in range(count)]


WAKA = {
    "human_readable_total": "1,891 hrs 29 mins",
    "languages": [
        {"name": "TypeScript", "percent": 45.9, "hours": 886, "minutes": 18},
        {"name": "Python", "percent": 24.9, "hours": 481, "minutes": 26},
        {"name": "C#", "percent": 3.3, "hours": 0, "minutes": 40},
    ],
}


class CardTests(unittest.TestCase):
    def test_every_card_is_valid_svg(self):
        cards = [
            hero.render(date(2026, 11, 22)),
            stats.render(
                commits=1, stars=2, repos=3, contributed=4, followers=5, added=10, deleted=4
            ),
            stack.render(),
            activity.render(days(30), days(400)),
            waka.render(WAKA),
            links.render("Portfolio", "example.dev", 0, 4),
        ]
        for card in cards:
            ET.fromstring(card)

    def test_hero_age(self):
        self.assertEqual(hero.age(date(2026, 10, 25)), 21)
        self.assertEqual(hero.age(date(2026, 10, 26)), 22)

    def test_all_time_stats(self):
        history = [("a", 0), ("b", 2), ("c", 3), ("d", 0), ("e", 1)]
        self.assertEqual(activity.all_time_stats(history), (3, 6 / 4, 1, 2))

    def test_streak_survives_an_empty_today(self):
        self.assertEqual(activity.all_time_stats([("a", 1), ("b", 1), ("c", 0)])[2], 2)

    def test_waka_strip_fills_to_combined_share(self):
        self.assertEqual(sum(waka._allocate_cells([45.9, 24.9, 3.3])), 44)
        self.assertEqual(waka.render(WAKA).count('class="c"'), waka.CELLS)


if __name__ == "__main__":
    unittest.main()

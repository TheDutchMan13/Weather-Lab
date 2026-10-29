"""The order of the reading cards on Home (0.37.35)."""
import unittest

from weatherlab import card_order


class CardOrderTests(unittest.TestCase):
    def test_move_down_and_up(self):
        cards = ["tempf", "humidity", "uv"]
        self.assertEqual(card_order.move(cards, "tempf", 1), ["humidity", "tempf", "uv"])
        self.assertEqual(card_order.move(cards, "uv", -1), ["tempf", "uv", "humidity"])
        self.assertEqual(cards, ["tempf", "humidity", "uv"])  # the original list is not changed

    def test_ends_and_unknown_do_nothing(self):
        cards = ["tempf", "humidity"]
        self.assertEqual(card_order.move(cards, "tempf", -1), cards)
        self.assertEqual(card_order.move(cards, "humidity", 1), cards)
        self.assertEqual(card_order.move(cards, "nope", 1), cards)

    def test_merge_keeps_order_and_adds_new_at_the_end(self):
        self.assertEqual(card_order.merge(["uv", "tempf", "humidity"], ["humidity", "tempf", "dewpointf"]),
                         ["tempf", "humidity", "dewpointf"])
        self.assertEqual(card_order.merge(["uv"], []), [])


if __name__ == "__main__":
    unittest.main()

import threading
import unittest

from ui.search_view import SearchView


class SearchHarness:
    def __init__(self):
        self._destroyed = False
        self._search_generation = 1
        self._active_stop_event = None
        self.search_thread = object()
        self.published = []

    def _show_results(self, results):
        self.published.append(results)


class TestSearchGeneration(unittest.TestCase):
    def test_only_current_generation_can_publish(self):
        harness = SearchHarness()
        current_event = threading.Event()
        harness._active_stop_event = current_event

        SearchView._publish_results(harness, 0, current_event, ["stale"])
        self.assertEqual(harness.published, [])

        SearchView._publish_results(harness, 1, current_event, ["current"])
        self.assertEqual(harness.published, [["current"]])
        self.assertIsNone(harness._active_stop_event)
        self.assertIsNone(harness.search_thread)

    def test_cancelled_or_destroyed_generation_cannot_publish(self):
        harness = SearchHarness()
        event = threading.Event()
        harness._active_stop_event = event
        event.set()
        SearchView._publish_results(harness, 1, event, ["cancelled"])
        self.assertEqual(harness.published, [])

        harness._destroyed = True
        event.clear()
        SearchView._publish_results(harness, 1, event, ["destroyed"])
        self.assertEqual(harness.published, [])


if __name__ == "__main__":
    unittest.main()

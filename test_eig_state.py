import unittest
from eig_state import StateExtractor, State, History

class TestHistory(unittest.TestCase):

    def setUp(self):
        self.history = History()

    def tearDown(self):
        del self.history

    def test_update(self):
        test_text = "This is a test."
        test_state = State(History(), test_text)
        self.history.update(test_state)
        self.assertEqual(self.history.state, test_state)
        self.assertEqual(self.history.past_states, [])
        self.assertEqual(self.history.past_turns, [])
        self.assertIsInstance(self.history.current_turn, tuple)
        self.assertEqual(self.history.current_turn[0], test_text)

        test_text_2 = "This is a second test."
        new_state = State(self.history, test_text_2)
        self.assertEqual(self.history.state, new_state)
        self.assertEqual(self.history.past_states[-1], test_state)
        self.assertEqual(self.history.past_turns[-1], (test_text, None))
        self.assertEqual(self.history.current_turn[0], test_text_2)

    def test_add_response(self):
        test_text = "This is a test."
        test_state = State(History(), test_text)
        self.history.update(test_state)
        response = "Hi There!"
        self.history.response = response

        self.assertEqual(self.history.current_turn[1], response)


class TestState(unittest.TestCase):

    def setUp(self):
        self.history = History()

    def test_runs_all_state_extractors(self):
        extractor_cls = StateExtractor.__subclasses__()
        extractors = [cls() for cls in extractor_cls]
        test_text = "This is a test!"
        test_state = State(self.history, test_text)
        for extractor in extractors:
            for name in extractor.state_var_names:
                self.assertTrue(hasattr(test_state, name), 
                                msg="Extractor {} missing variable {}".format(extractor.__class__.__name__, name))

    def test_updates_history(self):
        test_text = "This is a test!"
        test_state = State(self.history, test_text)
        self.assertEqual(self.history.question, test_text)
        self.assertEqual(self.history.state, test_state)

    def test_bad_history_input(self):
        test_text = "This is a test!"
        try:
            test_state = State(123, test_text)
            self.assertTrue(False)
        except Exception as e:
            self.assertIsInstance(e, ValueError)


class TestStateExtractors(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.extractors = [cls() for cls in StateExtractor.__subclasses__()]

    def test_extractors_no_state_no_history(self):

        for extractor in self.extractors:
            for state, history, output in extractor.test_cases:
                extractor(state, history)
                for key, value in output.items():
                    error_msg = 'for extractor {} with input "{}" and state var "{}"'
                    error_msg = error_msg.format(extractor.__class__.__name__,
                                                 state.q, key)
                    self.assertEqual(state.__dict__[key], value,
                                    msg=error_msg)

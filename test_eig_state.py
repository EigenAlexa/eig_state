import unittest
from eig_state import StateExtractor, State, History, ConvHistory, ConvState
from eig_state import NamedEntityExtractor, StateManager
from pymongo import MongoClient


class TestConvHistory(unittest.TestCase):

    def setUp(self):
        self.history = ConvHistory()

    def tearDown(self):
        del self.history

    def test_update(self):
        test_text = "This is a test."
        test_state = ConvState(test_text, extractors=[])
        self.history.update(test_state)
        self.assertEqual(self.history.state, test_state)
        self.assertEqual(self.history.past_states, [])
        self.assertEqual(self.history.past_turns, [])
        self.assertIsInstance(self.history.current_turn, tuple)
        self.assertEqual(self.history.current_turn[0], test_text)

        test_text_2 = "This is a second test."
        new_state = ConvState(test_text_2, self.history, extractors=[])
        self.assertEqual(self.history.state, new_state)
        self.assertEqual(self.history.past_states[-1], test_state)
        self.assertEqual(self.history.past_turns[-1], (test_text, None))
        self.assertEqual(self.history.current_turn[0], test_text_2)

    def test_add_response(self):
        test_text = "This is a test."
        test_state = ConvState(test_text, extractors=[])
        self.history.update(test_state)
        response = "Hi There!"
        self.history.last_response = response

        self.assertEqual(self.history.current_turn[1], response)



class TestConvState(unittest.TestCase):

    def setUp(self):
        self.history = ConvHistory()

    def test_runs_conv_extractors(self):
        extractors = StateExtractor.get_extractors("conv")
        test_text = "This is a test!"
        test_state = ConvState(test_text, history=self.history)
        for extractor in extractors:
            for name in extractor.state_var_names:
                self.assertTrue(hasattr(test_state, name), 
                                msg="Extractor {} missing variable {}".format(extractor.__class__.__name__, name))

    def test_updates_history(self):
        test_text = "This is a test!"
        test_state = ConvState(test_text, self.history, extractors=[])
        self.assertEqual(self.history.last_question, test_text)
        self.assertEqual(self.history.state, test_state)

    def test_bad_history_input(self):
        test_text = "This is a test!"
        self.assertRaises(TypeError, ConvState, test_text, history=123)

class TestStateExtractors(unittest.TestCase):


    def extractor_util(self, test_cases):
        for state, history, output in test_cases:
            for key, val in output.items():
                self.assertEqual(state.__dict__[key], val)

    def test_NamedEntityExtractor(self):

        history = ConvHistory()
        exts = [NamedEntityExtractor()]

        test_cases = [
            (ConvState("James is at WeWork.", history, exts),
             history,
             {'nes': [
                        { 'name': 'WeWork', 'type': 'place' },
                        { 'name': 'James', 'type': 'person' }
                     ]
             }
            ),
            (ConvState("Phillip is in Irvine.", history, exts),
             history,
             {'nes': [
                        { 'name': 'Irvine', 'type': 'place' },
                        { 'name': 'Phillip', 'type': 'person' },
                        { 'name': 'WeWork', 'type': 'place' },
                        { 'name': 'James', 'type': 'person' }
                     ]
             }
            )
        ]
        self.extractor_util(test_cases)


class TestStateManager(unittest.TestCase):

    def setUp(self):
        self.sm = StateManager("userid", "convid")

    def tearDown(self):
        self.sm.mongo_client.drop_database('state_manager')

    def test_sm_connects_to_mongo(self):
        self.assertIsInstance(self.sm.mongo_client, MongoClient)
        self.assertTrue(self.sm.mongo_client.is_primary)

    def test_sm_can_write_to_mongo(self):
        test_doc = {'test_field':'test'}
        result = self.sm.mongo_client.test_db.test_col.insert_one(test_doc)
        self.assertTrue(result.acknowledged)
        doc = self.sm.mongo_client.test_db.test_col.find_one(result.inserted_id)
        self.assertEqual(doc, test_doc)

    def test_get_conv_history(self):
        test_state = {'q': 'What is your name?'}
        result = self.sm.mongo_client.state_manager.states.insert_one(test_state)
        self.assertTrue(result.acknowledged)
        test_state['_id'] = result.inserted_id
        test_conv = {'convid': 'convid',
                     'last_response': 'James',
                     'last_question': 'What is your name?',
                     'state': result.inserted_id,
                     'past_states': [],
                     'userid': 'userid1',
                     'past_turns': [("Who are you?", "I am James")]
                    }
        result = self.sm.mongo_client.state_manager.convs.insert_one(test_conv)
        self.assertTrue(result.acknowledged)

        conv_history = self.sm.get_conv_history(test_conv['convid'])
        self.assertIsInstance(conv_history, ConvHistory)
        for key, value in test_conv.items():
            if key != 'state':
                self.assertEqual(value, getattr(conv_history, key))
            else:
                state = getattr(conv_history, key)
                self.assertIsInstance(state, ConvState)
                for k, v in test_state.items():
                    print(k)
                    self.assertEqual(getattr(state, k), v)

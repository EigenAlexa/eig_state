import unittest

from eig_state import state as s
from eig_state import history as h
from eig_state import state_extractors as se
from eig_state import state_manager
from eig_state.tests import utils

from pymongo import MongoClient



class TestConvHistory(unittest.TestCase):

    def setUp(self):
        self.history = h.ConvHistory()

    def tearDown(self):
        del self.history

    def test_update(self):
        test_text = "This is a test."
        test_state = s.ConvState(test_text, extractors=[])
        self.history.update(test_state)
        self.assertEqual(self.history.state, test_state)
        self.assertEqual(self.history.past_states, [])
        self.assertEqual(self.history.past_turns, [])
        self.assertIsInstance(self.history.current_turn, tuple)
        self.assertEqual(self.history.current_turn[0], test_text)

        test_text_2 = "This is a second test."
        new_state = s.ConvState(test_text_2, extractors=[])
        new_state.run_extractors(self.history)
        self.assertEqual(self.history.state, new_state)
        self.assertEqual(self.history.past_states[-1], test_state)
        self.assertEqual(self.history.past_turns[-1], (test_text, None))
        self.assertEqual(self.history.current_turn[0], test_text_2)

    def test_add_response(self):
        test_text = "This is a test."
        test_state = s.ConvState(test_text, extractors=[])
        self.history.update(test_state)
        response = "Hi There!"
        self.history.last_response = response

        self.assertEqual(self.history.current_turn[1], response)



class TestConvState(unittest.TestCase):

    def setUp(self):
        self.history = h.ConvHistory()

    def test_runs_conv_extractors(self):
        test_text = "This is a test!"
        test_state = s.ConvState(test_text, extractors="conv")
        test_state.run_extractors(self.history)
        utils.test_runs_conv_extractors(self, test_state)

    def test_runs_user_extractors(self):
        test_state = s.UserState()
        test_state.run_extractors(h.UserHistory(), self.history)
        utils.test_runs_user_extractors(self, test_state)

    def test_updates_history(self):
        test_text = "This is a test!"
        test_state = s.ConvState(test_text, extractors=[])
        test_state.run_extractors(self.history)
        self.assertEqual(self.history.last_question, test_text)
        self.assertEqual(self.history.state, test_state)

    def test_bad_history_input(self):
        test_text = "This is a test!"
        state = s.ConvState(test_text, extractors=[])
        self.assertRaises(TypeError, state.run_extractors, history=123)

class TestStateExtractors(unittest.TestCase):


    def conv_extractor_util(self, test_cases):
        for state, history, output in test_cases:
            state.run_extractors(history)
            for key, val in output.items():
                self.assertEqual(getattr(state, key), val)

    def user_extractor_util(self, test_cases):
        for user_state, user_hist, conv_state, conv_hist, output in test_cases:
            conv_state.run_extractors(conv_hist)
            user_state.run_extractors(user_hist, conv_hist)
            for key, val in output.items():
                self.assertEqual(getattr(user_state, key), val)

    @unittest.skip("Not Implemented")
    def test_NamedEntityExtractor(self):

        history = h.ConvHistory()
        exts = [se.NamedEntityExtractor()]

        test_cases = [
            (s.ConvState("James is at WeWork.", exts),
             history,
             {'nes': [
                        { 'name': 'WeWork', 'type': 'place' },
                        { 'name': 'James', 'type': 'person' }
                     ]
             }
            ),
            (s.ConvState("Phillip is in Irvine.", exts),
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
        self.conv_extractor_util(test_cases)

    def test_ProfanityDetector(self):

        history = h.ConvHistory()
        exts = [se.ProfanityDetector()]

        test_cases = [
            (s.ConvState("Fuck you.", exts),
             history,
             {'has_swear': True}
            ),
            (s.ConvState("you are class", exts),
             history,
             {'has_swear': False}
            ),
            (s.ConvState("you are an ass.", exts),
             history,
             {'has_swear': True}
            ),
            (s.ConvState("fucker", exts),
             history,
             {'has_swear': True}
            ),
        ]
        self.conv_extractor_util(test_cases)

    def test_AdviceDetector(self):

        history = h.ConvHistory()
        exts = [se.AdviceDetector()]

        test_cases = [
            (s.ConvState("Should I invest in Amazon?", exts),
             history,
             {'asks_advice': True}
            ),
            (s.ConvState("Can you give me some stock market advice?", exts),
             history,
             {'asks_advice': True}
            ),
            #(s.ConvState("what do you think I should do with my money?", exts),
            # history,
            # {'asks_advice': True}
            #)
            # implement this feature
        ]

        self.conv_extractor_util(test_cases)

    @unittest.skip("Not Implemented")
    def test_UserNameExtractor(self):

        user_hist = h.UserHistory()
        conv_hist = h.ConvHistory()
        user_exts = [se.UserNameExtractor()]
        conv_exts = []

        test_cases = [
            (s.UserState(user_exts), user_hist,
             s.ConvState("My name is James", conv_exts),
             conv_hist,
             {'name':'James'}
            )
        ]

        self.user_extractor_util(test_cases)


class TestStateManager(unittest.TestCase):

    def setUp(self):
        sm = state_manager.StateManager("", "", database="test")
        self.test_state = {'question': 'What is your name?'}
        self.test_user_state = {'name': 'James'}
        conv_result = sm.state_col.insert_one(self.test_state)
        self.assertTrue(conv_result.acknowledged)
        user_result = sm.state_col.insert_one(self.test_user_state)
        self.assertTrue(user_result.acknowledged)
        self.test_state['_id'] = conv_result.inserted_id
        self.test_user_state['_id'] = user_result.inserted_id
        self.test_conv = {'convid': 'convid',
                     'last_response': 'James',
                     'last_question': 'What is your name?',
                     'state': conv_result.inserted_id,
                     'past_states': [],
                     'userid': "userid",
                     'past_turns': [("Who are you?", "I am James")]
                    }
        result = sm.conv_col.insert_one(self.test_conv)
        self.assertTrue(result.acknowledged)
        self.test_user = {'userid': 'userid',
                          'state': user_result.inserted_id,
                          'past_states': []
                         }
        result = sm.user_col.insert_one(self.test_user)
        self.assertTrue(result.acknowledged)
        self.sm = state_manager.StateManager("userid", "convid", database="test")

    def tearDown(self):
        self.sm.mongo_client.drop_database('test')

    def test_sm_connects_to_mongo(self):
        self.assertIsInstance(self.sm.mongo_client, MongoClient)
        self.assertTrue(self.sm.mongo_client.is_primary)

    def test_sm_can_write_to_mongo(self):
        test_doc = {'test_field':'test'}
        result = self.sm.db.test_col.insert_one(test_doc)
        self.assertTrue(result.acknowledged)
        doc = self.sm.db.test_col.find_one(result.inserted_id)
        self.assertEqual(doc, test_doc)

    def test_get_conv_history(self):
        conv_history = self.sm.get_conv_history(self.test_conv['convid'])
        self.assertIsInstance(conv_history, h.ConvHistory)
        for key, value in self.test_conv.items():
            if key != 'state':
                self.assertEqual(value, getattr(conv_history, key))
            else:
                state = getattr(conv_history, key)
                self.assertIsInstance(state, s.ConvState)
                for k, v in self.test_state.items():
                    print(k)
                    self.assertEqual(getattr(state, k), v)

    def test_get_user_history(self):
        user_history = self.sm.get_user_history(self.test_user['userid'])
        self.assertIsInstance(user_history, h.UserHistory)
        for key, value in self.test_user.items():
            if key != 'state':
                self.assertEqual(value, getattr(user_history, key))
            else:
                state = getattr(user_history, key)
                self.assertIsInstance(state, s.UserState)
                for k, v in self.test_user_state.items():
                    self.assertEqual(getattr(state, k), v)

    def test_next_round_updates_history(self):
        question = "Who are you?"
        self.sm.next_round(question)
        self.assertNotEqual(self.sm.conv_history.state, self.test_state)
        self.assertIsInstance(self.sm.conv_history.past_states[0], s.ConvState)
        self.assertEqual(self.sm.conv_history.state.question, question)
        utils.test_runs_conv_extractors(self, self.sm.conv_history.state)
        utils.test_runs_user_extractors(self, self.sm.user_history.state)

    def test_set_response_saves_history(self):
        question = "Who are you?"
        res = "eigen"
        self.sm.next_round(question)
        self.sm.set_response(res)
        conv_history = self.sm.get_conv_history(self.sm.conv_history.convid)
        user_history = self.sm.get_user_history(self.sm.user_history.userid)
        self.assertEqual(conv_history.state.question, question)
        self.assertIsInstance(conv_history.past_states[0], s.ConvState)
        self.assertEqual(conv_history.past_states[0].question,
                         self.test_state['question'])
        self.assertEqual(conv_history.last_response, res)

        self.assertIsInstance(user_history.past_states[0], s.UserState)

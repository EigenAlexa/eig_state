import unittest

from eig_state import state as s
from eig_state import history as h
from eig_state import state_extractors as se
from eig_state import state_manager
from eig_state.tests import utils

import boto3
from moto import mock_dynamodb2

def create_tables(dynamo):
    dynamo.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S',
            }
        ],
        KeySchema=[
            {
                'AttributeName':'id',
                'KeyType': 'HASH'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
        TableName='test_conversations'
    )
    dynamo.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S',
            }
        ],
        KeySchema=[
            {
                'AttributeName':'id',
                'KeyType': 'HASH'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
        TableName='test_states'
    )
    dynamo.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S',
            }
        ],
        KeySchema=[
            {
                'AttributeName':'id',
                'KeyType': 'HASH'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        },
        TableName='test_users'
    )

def setUpDynamo(cls):
   cls.dynamo = boto3.resource('dynamodb', region_name='us-east-1')
   #create_tables(cls.dynamo)
   cls.state_tbl = cls.dynamo.Table('test_states')
   cls.conv_tbl = cls.dynamo.Table('test_conversations')



class TestConvHistory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        setUpDynamo(cls)

    def setUp(self):
        self.history = h.ConvHistory("sessionid", self.state_tbl, "convid",
                                     "userid")

    def test_update(self):
        test_text = "This is a test."
        test_state = s.ConvState(test_text, extractors=[])
        test_state.changed = True
        self.history.update(test_state)
        self.assertEqual(self.history.state_list[-1], test_state)

        test_text_2 = "This is a second test."
        new_state = s.ConvState(test_text_2, extractors=[])
        new_state.run_extractors(self.history)
        self.assertEqual(self.history.state_list[-1], new_state)
        self.assertEqual(self.history.state_list[-2], test_state)
        self.assertEqual(self.history.state_list[-2].question, test_text)
        self.assertEqual(self.history.state_list[-1].question, test_text_2)

    def test_add_response(self):
        test_text = "This is a test."
        test_state = s.ConvState(test_text, extractors=[])
        test_state.changed = True
        self.history.update(test_state)
        response = "Hi There!"
        self.history.set_last_response(response)

        self.assertEqual(self.history.state_list[-1].response, response)



class TestConvState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        setUpDynamo(cls)

    def setUp(self):
        self.history = h.ConvHistory("sessionid", self.state_tbl, "convid",
                                     "userid")

    def test_runs_conv_extractors(self):
        test_text = "This is a test!"
        test_state = s.ConvState(test_text, extractors="conv")
        test_state.run_extractors(self.history)
        utils.test_runs_conv_extractors(self, test_state)

    def test_runs_user_extractors(self):
        test_state = s.UserState()
        test_state.run_extractors(h.UserHistory("userid", self.state_tbl), self.history)
        utils.test_runs_user_extractors(self, test_state)

    def test_updates_history(self):
        test_text = "This is a test!"
        test_state = s.ConvState(test_text, extractors=[])
        test_state.run_extractors(self.history)
        self.assertEqual(self.history.state_list[-1].question, test_text)
        self.assertEqual(self.history.state_list[-1], test_state)

    def test_bad_history_input(self):
        test_text = "This is a test!"
        state = s.ConvState(test_text, extractors=[])
        self.assertRaises(TypeError, state.run_extractors, history=123)

class TestStateExtractors(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        setUpDynamo(cls)

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

        history = h.ConvHistory("sessionid",
                                self.state_tbl,
                                "convid",
                                "userid")

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

        history = h.ConvHistory("sessionid",
                                self.state_tbl,
                                "convid",
                                "userid")

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

        history = h.ConvHistory("sessionid",
                                self.state_tbl,
                                "convid",
                                "userid")
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

        user_hist = h.UserHistory("sessionid",
                                  self.state_tbl)
        conv_hist = h.ConvHistory("sessionid",
                                  self.state_tbl,
                                  "convid",
                                  "userid")
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

    @classmethod
    def setUpClass(cls):
        setUpDynamo(cls)

    def setUp(self):
        self.sm = state_manager.StateManager("userid", "convid", "sessionid",
                                        state_tbl_name='test_states',
                                        user_tbl_name='test_users',
                                        conv_tbl_name='test_conversations')
        self.test_q = "hello"
        self.test_res  = "hi there"
        self.sm.next_round(self.test_q)
        self.sm.set_response(self.test_res)

    def test_sm_connects_to_dynamo(self):
        self.assertIsInstance(self.sm.dynamo,
                              boto3.resources.base.ServiceResource)
        self.assertEqual(self.sm.dynamo.meta.service_name, 'dynamodb')

    def test_sm_can_write_to_dynamo(self):
        test_item = {'id': '1', 'test_field':'test'}
        tbl = self.sm.get_table(self.sm.conv_tbl_name)
        response = tbl.put_item(Item=test_item)
        item = self.sm.retrieve_item(self.sm.conv_tbl_name, '1')
        self.assertEqual(item, test_item)

    def test_get_conv_history(self):
        conv_history = self.sm.get_conv_history("sessionid", "convid", "userid")
        self.assertIsInstance(conv_history, h.ConvHistory)
        self.assertEqual(conv_history.state_list[-1].question, self.test_q)
        self.assertEqual(conv_history.state_list[-1].response, self.test_res)

    def test_get_user_history(self):
        user_history = self.sm.get_user_history("userid")
        self.assertIsInstance(user_history, h.UserHistory)

    def test_next_round_updates_history(self):
        question = "Who are you?"
        self.sm.next_round(question)
        self.assertIsInstance(self.sm.conv_history.state_list[-2], s.ConvState)
        self.assertEqual(self.sm.conv_history.state_list[-1].question, question)
        utils.test_runs_conv_extractors(self,
                                        self.sm.conv_history.state_list[-1])
        utils.test_runs_user_extractors(self,
                                        self.sm.user_history.state_list[-1])

    def test_set_response_saves_history(self):
        question = "Who are you?"
        res = "eigen"
        self.sm.next_round(question)
        self.sm.set_response(res)
        conv_history = self.sm.get_conv_history("sessionid", "convid", "userid")
        user_history = self.sm.get_user_history("userid")
        self.assertEqual(conv_history.state_list[-1].question, question)
        self.assertEqual(conv_history.state_list[-1].response, res)
        self.assertIsInstance(conv_history.state_list[-2], s.ConvState)
        self.assertEqual(conv_history.state_list[-2].question,
                         self.test_q)
        self.assertEqual(conv_history.state_list[-2].response, self.test_res)

        self.assertIsInstance(user_history.state_list[-2], s.UserState)


from eig_state import state
from eig_state import history
import boto3

class StateManager:

    def __init__(self, userid, convid, sessionid, state_tbl_name='states',
                 user_tbl_name='users', conv_tbl_name='conversations'):
        self.state_tbl_name = state_tbl_name
        self.conv_tbl_name = conv_tbl_name
        self.user_tbl_name = user_tbl_name
        self._tbls = {}
        self.dynamo = boto3.resource('dynamodb', region_name='us-east-1')
        self.conv_history = self.get_conv_history(sessionid, convid, userid)
        self.user_history = self.get_user_history(userid)
        self.ready_for_q = True

    def retrieve_item(self, tbl_name, key):
        table = self.get_table(tbl_name)
        response = table.get_item(Key={'id': key})
        return 'Item' in response and response['Item']

    def get_table(self, tbl_name):
        table = self._tbls.get(tbl_name)
        if table is None:
            table = self.dynamo.Table(tbl_name)
            self._tbls[tbl_name] = table
        return table

    def get_conv_history(self, sessionid, convid, userid):
        """
        Get ConvHistory object from mongodb
        Should convert stateid in mongo, to State object by querying mongo for
        that state
        Should convert each of past_states into State objects
        if convid doesnt exist in mongo it should make a new doc in mongo and
        return new ConvHistory()
        """
        return self.get_history(sessionid, self.conv_tbl_name, history.ConvHistory,
                                state.ConvState, convid, userid)

    def get_user_history(self, userid):

        return self.get_history(userid, self.user_tbl_name, history.UserHistory,
                                state.UserState)

    def get_history(self, hist_id, tbl_name, cls, state_cls, *args):

        item = self.retrieve_item(tbl_name, hist_id)
        if item:
            state_list = self.get_state_list(item['state_list_id'], state_cls)
            print(state_list.states)
            item['state_list'] = state_list
            hist = cls.from_dict(item, self.get_table(self.state_tbl_name), *args)
        else:
            print("conv id not found, creating new doc")
            hist = cls(hist_id, self.get_table(self.state_tbl_name), *args)
            hist.save(self.get_table(tbl_name))
        return hist


    def get_state_list(self, _id, state_cls):
        item = self.retrieve_item(self.state_tbl_name, _id)
        if item:
            print(item)
            tbl = self.get_table(self.state_tbl_name)
            return state.StateList.from_dict(item, tbl, state_cls)
        raise ValueError("State id doesn't exist in dynamodb states table")

    def next_round(self, question):
        if not self.ready_for_q:
            raise RuntimeError("Must call set_response before you can call next_round again")
        conv_state = state.ConvState(question)
        user_state = state.UserState()
        conv_state.run_extractors(self.conv_history)
        user_state.run_extractors(self.user_history, self.conv_history)
        self.ready_for_q = False
        return self

    def set_response(self, response):
        if self.ready_for_q:
            raise RuntimeError("Must call next_round before you can call set_response again.")
        self.conv_history.set_last_response(response)
        self.conv_history.save(self.get_table(self.conv_tbl_name))
        self.user_history.save(self.get_table(self.user_tbl_name))
        self.ready_for_q = True


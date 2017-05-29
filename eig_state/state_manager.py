from pymongo import MongoClient
from eig_state import state
from eig_state import history

class StateManager:

    def __init__(self, userid, convid, database='state_manager'):
        self.mongo_client = MongoClient(host='mongo', port=27017)
        self.db = self.mongo_client[database]
        self.conv_col = self.db.convs
        self.state_col = self.db.states
        self.user_col = self.db.users
        self.conv_history = self.get_conv_history(convid)
        self.user_history = self.get_user_history(userid)
        self.has_response = True

    def get_conv_history(self, convid):
        """
        Get ConvHistory object from mongodb
        Should convert stateid in mongo, to State object by querying mongo for
        that state
        Should convert each of past_states into State objects
        if convid doesnt exist in mongo it should make a new doc in mongo and
        return new ConvHistory()
        """
        return self.get_history('convid', convid, self.conv_col, history.ConvHistory,
                                state.ConvState)

    def get_user_history(self, userid):

        return self.get_history('userid', userid, self.user_col, history.UserHistory,
                                state.UserState)

    def get_history(self, id_name, hist_id, col, cls, state_cls):

        obj = col.find_one({id_name: hist_id})
        if obj:
            state = self.get_state(obj['state'], state_cls)
            obj['state'] = state
            for i, past_state_id in enumerate(obj['past_states']):
                past_state = self.get_state(past_state_id, state_cls)
                obj['past_states'][i] = past_state
            hist = cls.from_mongo(obj)
        else:
            print("conv id not found, creating new doc")
            hist = cls()
            hist.save(col, self.state_col)
        return hist


    def get_state(self, _id, cls):
        state_obj = self.state_col.find_one(_id)
        if state_obj:
            return cls.from_mongo(state_obj)
        raise ValueError("State id doesn't exist in mongodb")

    def get_conv_state(self, _id):
        return self.get_state(_id, state.ConvState)

    def get_user_state(self, _id):
        return self.get_state(_id, state.UserState)

    def next_round(self, question):
        if not self.has_response:
            raise RuntimeError("Must call set_response before you can call next_round again")
        conv_state = state.ConvState(question)
        user_state = self.user_history.state
        conv_state.run_extractors(self.conv_history)
        user_state.run_extractors(self.user_history, self.conv_history)
        self.has_response = False
        return self

    def set_response(self, response):
        if self.has_response:
            raise RuntimeError("Must call next_round before you can call set_response again.")
        self.conv_history.last_response = response
        self.conv_history.save(self.conv_col, self.state_col)
        self.user_history.save(self.user_col, self.state_col)
        self.has_response = True


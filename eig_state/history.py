import copy

import eig_state

class History:

    def __init__(self, **kwargs):
        self.state = None
        #TODO make past_states lazily evaluated so they only get brought into
        #memory if they are called on
        self.past_states = []
        for key, value in kwargs.items():
            if isinstance(value, list) and value and isinstance(value[0], list):
                value = list(map(lambda x: tuple(x), value))
            setattr(self, key, value)

    def update(self, state):
        if isinstance(self.state, eig_state.state.State):
            if state.changed:
                self.past_states.append(self.state)
                self.state = state
        else:
            self.state = state

    @classmethod
    def from_mongo(cls, obj):
        """
        Parses mongo data and creates object
        """
        return cls(**obj)

    def save(self, col, state_col):
        """
        Saves this to mongo
        """
        doc = copy.copy(self.__dict__)
        if 'state' in doc and isinstance(doc['state'], eig_state.state.State):
            doc['state'].save(state_col)
            doc['state'] = doc['state']._id
        if 'past_states' in doc:
            doc['past_states'] = copy.copy(doc['past_states'])
            for i, state in enumerate(doc['past_states']):
                doc['past_states'][i] = state._id

        if hasattr(self, '_id'):
            col.replace_one({'_id': self._id}, doc)
        else:
            result = col.insert_one(doc)
            self._id = result.inserted_id

class ConvHistory(History):

    def __init__(self, **kwargs):
        self.last_response = None
        self.last_question = None
        self.past_turns = []
        self.userid = None
        super().__init__(**kwargs)


    @property
    def current_turn(self):
        return (self.last_question, self.last_response)

    def update(self, state):
        super().update(state)
        #TODO log error if past_turns doesnt have a response i.e. tuple
        # is (something, None)
        if self.last_question: #TODO change to some check on current_turn
            self.past_turns.append(self.current_turn)
        self.last_question = self.state.question
        self.last_response = None


class UserHistory(History):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)



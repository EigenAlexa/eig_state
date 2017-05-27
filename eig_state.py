from state_extractors import StateExtractor


class History:

    def __init__(self):
        self._state = None
        self.response = None
        self.question = None
        self.past_states = []
        self.past_turns = []
        self.user = None

    @property
    def state(self):
        return self._state

    @property
    def current_turn(self):
        return (self.question, self.response)

    def update(self, state):
        if isinstance(self.state, State):
            self.past_states.append(self.state)
        else:
            #TODO make it so it checks if it is a mongo id and then gets the
            # state from mongo
            pass
        self._state = state

        #TODO log error if past_turns doesnt have a response i.e. tuple
        # is (something, None)
        if self.question: #TODO change to some check on current_turn
            self.past_turns.append(self.current_turn)
        self.question = self.state.q
        self.response = None


class State:

    def __init__(self, history, question):
        """
            Run every StateExtractor that it should and then update history to
            push state to paststates and self as new state.
        """
        self.q = question

        for extractor_cls in StateExtractor.__subclasses__():
            extractor = extractor_cls()
            extractor(self, history, self.q)
        if isinstance(history, History):
            history.update(self)
        else:
            raise ValueError("history must be instance of History, not {}".format(type(history)))

class User:

    def __init__(self, userid):
        self._id = userid

    @property
    def userid(self):
        return self._id

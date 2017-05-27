import abc

class StateExtractor(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __call__(self, state, history, text):
        """
        Runs this extractors methods and updates state
        """

    @property
    @abc.abstractmethod
    def state_var_names(self):
        """
        Returns names of variables that this extractor will alter in state
        """

    @property
    @abc.abstractmethod
    def test_cases(self):
        """
        Returns list of test cases for this extractor, where each element of
        list is a tuple of (state, history, output).
        """


class SubjectExtractor(StateExtractor):

    def __init__(self):
        self._state_var_names = ["subject"]

    #TODO implement this method, currently just dummy method
    def __call__(self, state, history):
        for name in self.state_var_names:
            state.__dict__[name] = 'James'

    @property
    def state_var_names(self):
        return self._state_var_names

    @property
    def test_cases(self):

        test_input_output = [
            ('James is busy.', {'subject': 'James'}),
            ('George is sleeping.', {'subject': 'George'})]

        return [ (State(None, input_text), History(), output) for input_text,
                output in test_input_output ]


class State:

    def __init__(self, history, question):
        """
            Run every StateExtractor that it should and then update history to
            push state to paststates and self as new state.
        """
        self.q = question

        for extractor_cls in StateExtractor.__subclasses__():
            extractor = extractor_cls()
            extractor(self, history)

        if isinstance(history, History):
            history.update(self)
        elif history is not None:
            raise ValueError("history must be instance of History, not {}".format(type(history)))


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


class User:

    def __init__(self, userid):
        self._id = userid

    @property
    def userid(self):
        return self._id


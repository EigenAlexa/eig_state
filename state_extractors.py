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

class SubjectExtractor(StateExtractor):

    def __init__(self):
        self._state_var_names = ["subject"]

    #TODO implement this method, currently just dummy method
    def __call__(self, state, history, q):
        for name in self.state_var_names:
            state.__dict__[name] = None

    @property
    def state_var_names(self):
        return self._state_var_names

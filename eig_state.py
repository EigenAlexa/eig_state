import abc
import inspect
from pymongo import MongoClient

class StateExtractor(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __call__(self, state, history):
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
    def type(self):
        """
        Returns type of the extractor, i.e. convextractor or userextractor
        """

    @classmethod
    def get_extractors(cls, extractor_type):
        extractors = []
        for extractor in cls.__subclasses__():
            ext = extractor()
            if ext.type == extractor_type:
                extractors.append(ext)
        return extractors


class State:

    def __init__(self, history=None, extractors=[], from_mongo=False, **kwargs):

        if from_mongo:
            for key, value in kwargs.items():
                setattr(self, key, value)
        else:
            if isinstance(history, History):
                if isinstance(extractors, list):
                    for extractor in extractors:
                        extractor(self, history)
                elif isinstance(extractors, str):
                    for extractor in StateExtractor.get_extractors(extractors):
                        extractor(self, history)
                else:
                    raise TypeError("extractor must be either list of extractors, or a string extractor type.")

                history.update(self)

            elif history is not None:
                raise TypeError("history must be instance of History, not {}".format(type(history)))

    @classmethod
    def from_mongo(cls, obj):
        """
        Parses mongo data dict into State object
        """
        return cls(from_mongo=True, **obj)

class ConvState(State):

    def __init__(self, question=None, history=None, extractors=None,
                 from_mongo=False, **kwargs):
        self.question = question
        if isinstance(extractors, list):
            super().__init__(history, extractors, from_mongo, **kwargs)
        else:
            super().__init__(history, "conv", from_mongo, **kwargs)

class UserState(State):
    pass


class History:

    def __init__(self, **kwargs):
        self._state = None
        self.past_states = []
        self._id = None
        for key, value in kwargs.items():
            try:
                if isinstance(value, list) and value and isinstance(value[0],
                                                                    list):
                    value = list(map(lambda x: tuple(x), value))
                setattr(self, key, value)
            except AttributeError:
                if key == 'state':
                    self._state = value
    @property
    def state(self):
        return self._state

    def update(self, state):
        if isinstance(self.state, State):
            self.past_states.append(self.state)
        else:
            #TODO make it so it checks if it is a mongo id and then gets the
            # state from mongo
            pass
        self._state = state

    @classmethod
    def from_mongo(cls, obj):
        """
        Parses mongo data and creates object
        """
        return cls(**obj)


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
    pass


class NamedEntityExtractor(StateExtractor):

    def __init__(self):
        #TODO setup named entity extractor here
        pass

    @property
    def type(self):
        return "conv"

    @property
    def state_var_names(self):
        return ["nes"]

    def __call__(self, state, history):
        if history.past_states:
            state.nes = history.past_states[-1].nes
        else:
            state.nes = {}


class StateManager:

    def __init__(self, userid, convid):
        self.mongo_client = MongoClient(host='mongo', port=27017)
        #conv_history = self.get_conv_history(convid)
        #user = self.get_user(userid)

    def get_conv_history(self, convid):
        """
        Get ConvHistory object from mongodb
        Should convert stateid in mongo, to State object by querying mongo for
        that state
        Should convert each of past_states into State objects
        if convid doesnt exist in mongo it should make a new doc in mongo and
        return new ConvHistory()
        """
        conv_col = self.mongo_client.state_manager.convs
        conv_obj = conv_col.find_one({'convid':convid})
        print(conv_obj)
        if conv_obj:
            state = self.get_conv_state(conv_obj['state'])
            conv_obj['state'] = state
            conv_hist = ConvHistory.from_mongo(conv_obj)
        else:
            print("conv id not found, creating new doc")
            conv_hist = ConvHistory()
        return conv_hist

    def get_user(self, userid):
        """
        Get UserHistory object from mongodb
        """
        mongo_obj = None
        return UserHistory().from_mongo(mongo_obj)

    def get_state(self, _id, cls):
        print(_id)
        state_col = self.mongo_client.state_manager.states
        state_obj = state_col.find_one(_id)
        if state_obj:
            return cls.from_mongo(state_obj)
        raise ValueError("State id doesn't exist in mongodb")

    def get_conv_state(self, _id):
        return self.get_state(_id, ConvState)

    def get_user_state(self, _id):
        return self.get_state(_id, UserState)

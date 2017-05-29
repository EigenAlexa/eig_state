import abc
import copy
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

    def __init__(self, extractors=[], **kwargs):

        self.extractors = extractors
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run_extractors(self, history, *args):
        changed = False
        if isinstance(history, History):
            if isinstance(self.extractors, list):
                for extractor in self.extractors:
                    change = extractor(self, history, *args)
                    changed = changed or change
            elif isinstance(self.extractors, str):
                for extractor in StateExtractor.get_extractors(self.extractors):
                    change = extractor(self, history, *args)
                    changed = changed or change
            else:
                raise TypeError("extractor must be either list of extractors, or a string extractor type.")

            #TODO this is a shitty way of doing this, should make it run some
            #sort of diff on the objects or something
            self.changed = changed
            if history.past_states:
                if hasattr(self, 'question'):
                    self.changed |= self.question != history.past_states[-1].question
            else:
                self.changed = True
            history.update(self)

        elif history is not None:
            raise TypeError("history must be instance of History, not {}".format(type(history)))

    @classmethod
    def from_mongo(cls, obj):
        """
        Parses mongo data dict into State object
        """
        return cls(**obj)

    def save(self, col):
        """
        Saves object to mongo
        """
        #TODO make it so this only saves if there is a change
        if hasattr(self, '_id'):
            col.replace_one({'_id': self._id}, self.__dict__)
        else:
            result = col.insert_one(self.__dict__)
            self._id = result.inserted_id

class ConvState(State):

    def __init__(self, question=None, extractors=None, **kwargs):
        self.question = question
        if isinstance(extractors, list):
            super().__init__(extractors, **kwargs)
        else:
            super().__init__("conv", **kwargs)

class UserState(State):

    def __init__(self, extractors=None, **kwargs):
        if isinstance(extractors, list):
            super().__init__(extractors, **kwargs)
        else:
            super().__init__("user", **kwargs)

    def run_extractors(self, user_hist, conv_hist):
        super().run_extractors(user_hist, conv_hist)


class History:

    def __init__(self, **kwargs):
        self.state = None
        self.past_states = []
        for key, value in kwargs.items():
            if isinstance(value, list) and value and isinstance(value[0], list):
                value = list(map(lambda x: tuple(x), value))
            setattr(self, key, value)

    def update(self, state):
        if isinstance(self.state, State):
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
        if 'state' in doc and isinstance(doc['state'], State):
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
            return True
        else:
            state.nes = {}
            return False

class UserNameExtractor(StateExtractor):

    def __init__(self):
        pass

    @property
    def type(self):
        return "user"

    @property
    def state_var_names(self):
        return ["name"]

    def __call__(self, state, user_hist, conv_history):
        if user_hist.past_states:
            state.name = user_hist.past_states[-1].name
            return True
        else:
            state.name = "UserName"
            return False

class StateManager:

    def __init__(self, userid, convid, database='state_manager'):
        self.mongo_client = MongoClient(host='mongo', port=27017)
        self.db = self.mongo_client[database]
        self.conv_col = self.db.convs
        self.state_col = self.db.states
        self.user_col = self.db.users
        self.conv_history = self.get_conv_history(convid)
        self.user_history = self.get_user_history(userid)

    def get_conv_history(self, convid):
        """
        Get ConvHistory object from mongodb
        Should convert stateid in mongo, to State object by querying mongo for
        that state
        Should convert each of past_states into State objects
        if convid doesnt exist in mongo it should make a new doc in mongo and
        return new ConvHistory()
        """
        return self.get_history('convid', convid, self.conv_col, ConvHistory,
                                ConvState)

    def get_user_history(self, userid):

        return self.get_history('userid', userid, self.user_col, UserHistory,
                                UserState)

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
        return self.get_state(_id, ConvState)

    def get_user_state(self, _id):
        return self.get_state(_id, UserState)

    def next_round(self, question):
        conv_state = ConvState(question)
        user_state = self.user_history.state
        conv_state.run_extractors(self.conv_history)
        user_state.run_extractors(self.user_history, self.conv_history)
        self.conv_history.save(self.conv_col, self.state_col)
        self.user_history.save(self.user_col, self.state_col)
        return self

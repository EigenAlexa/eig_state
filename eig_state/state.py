from eig_state import state_extractors as se
from eig_state import history as h

class State:

    def __init__(self, extractors=[], **kwargs):

        self.extractors = extractors
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run_extractors(self, history, *args):
        changed = False
        if isinstance(history, h.History):
            if isinstance(self.extractors, list):
                for extractor in self.extractors:
                    change = extractor(self, history, *args)
                    changed = changed or change
            elif isinstance(self.extractors, str):
                for extractor in se.StateExtractor.get_extractors(self.extractors):
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



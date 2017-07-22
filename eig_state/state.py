import collections
import uuid
from eig_state import state_extractors as se
from eig_state import history as h
from eig_state.core import DynamoBackedObject

class State(DynamoBackedObject):

    def __init__(self, extractors=[], **kwargs):
        _id = str(uuid.uuid1())
        super().__init__(_id)
        self.extractors = extractors

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

            if history.state_list:
                changed |= self != history.state_list[-1]
            else:
                changed = True
            self.changed = changed
            history.update(self)

        elif history is not None:
            raise TypeError("history must be instance of History, not {}".format(type(history)))

class StateList(DynamoBackedObject, collections.abc.MutableSequence):

    def __init__(self, _id, table, state_cls):
        if _id is None:
            _id = str(uuid.uuid1())
        DynamoBackedObject.__init__(self, _id)
        self.states = {}
        self.state_ids = []
        self.register_saver('state_ids', self.state_saver)
        self.tbl = table
        self.state_cls = state_cls

    def state_saver(self, item):
        item['state_ids'] = self.state_ids
        for state_id in self.states:
            state = self.states[state_id]
            if isinstance(state, State):
                state.save(self.tbl)
        return item

    def __getitem__(self, key):
        _id = self.state_ids[key]
        return (_id in self.states and self.states[_id]) or self.get_state(_id)

    def get_state(self, _id):
        response = self.tbl.get_item(Key={'id': _id})
        return self.state_cls.from_dict(response['Item'])

    def __setitem__(self, key, value):
        if isinstance(value, State):
            _id = value.id
            self.states[_id] = value
            self.state_ids[key] = _id
        elif isinstance(value, str):
            self.state_ids[key] = value

    def __delitem__(self, key):
        del self.states[self.state_ids[key]]

    def insert(self, key, value):
        if isinstance(value, State):
            self.state_ids.insert(key, value.id)
            print(self.states)
            self.states[value.id] = value
        elif isinstance(value, str):
            self.state_ids.insert(key, value)

    def append(self, value):
        self.insert(len(self), value)

    def __contains__(self, item):
        query = item
        if isinstance(item, State):
            query = item.id
        return query in self.state_ids

    def __len__(self):
        return len(self.state_ids)

    def __iter__(self):
        for key in range(len(self)):
            yield self.__getitem__(key)

    def __nonzero__(self):
        return len(self) != 0

    def repeat_last(self):
        self.state_ids.append(self.state_ids[-1])


class ConvState(State):

    def __init__(self, question=None, extractors=None, **kwargs):
        self.question = question
        if isinstance(extractors, list):
            super().__init__(extractors, **kwargs)
        else:
            super().__init__(extractors="conv", **kwargs)
        self.register_saver('question')

class UserState(State):

    def __init__(self, extractors=None, **kwargs):
        if isinstance(extractors, list):
            super().__init__(extractors, **kwargs)
        else:
            super().__init__(extractors="user", **kwargs)

    def run_extractors(self, user_hist, conv_hist):
        super().run_extractors(user_hist, conv_hist)



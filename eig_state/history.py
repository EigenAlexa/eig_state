import eig_state
from eig_state.core import DynamoBackedObject

class History(DynamoBackedObject):

    def __init__(self, _id, state_tbl, state_cls):
        self.state_list = eig_state.state.StateList(None, state_tbl, state_cls)
        super().__init__(_id)
        #TODO make past_states lazily evaluated so they only get brought into
        #memory if they are called on
        self.state_tbl = state_tbl
        self.register_saver('state_list_id', self.state_list_saver)

    def update(self, state):
        if isinstance(state, eig_state.state.State):
            if state.changed:
                self.state_list.append(state)
            else:
                self.state_list.repeat_last()

    def state_list_saver(self, item):
        item['state_list_id'] = self.state_list.id
        self.state_list.save(self.state_tbl)
        return item

class ConvHistory(History):

    def __init__(self, _id, state_tbl, convid, userid, **kwargs):
        super().__init__(_id, state_tbl, eig_state.state.ConvState, **kwargs)
        self.userid = userid
        self.register_saver('userid')
        self.convid = convid
        self.register_saver('convid')

    def set_last_response(self, response):
        self.state_list[-1].response = response
        self.state_list[-1].register_saver('response')

class UserHistory(History):

    def __init__(self, _id, state_tbl, **kwargs):
        super().__init__(_id, state_tbl, eig_state.state.UserState, **kwargs)



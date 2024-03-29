import abc
from eig_state.swear_words import words as swears
from eig_state.swear_words import phrases
import re


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

    def __call__(self, state, history):
        for var in self.state_var_names:
            state.register_saver(var)

## NOT IMPLEMENTED
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
        super().__call__(state, history)
        if history.state_list:
            state.nes = history.state_list[-1].nes
            return True
        else:
            state.nes = {}
            return False


## NOT IMPLEMENTED
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
        super().__call__(state, user_hist)
        if user_hist.state_list:
            state.name = user_hist.state_list[-1].name
            return True
        else:
            state.name = "UserName"
            return False

class ProfanityDetector(StateExtractor):

    @property
    def type(self):
        return "conv"

    @property
    def state_var_names(self):
        return ['has_swear']

    def __call__(self, state, history):
        super().__call__(state, history)
        state.has_swear = self.contains_profanity(state.question)
        return True

    def contains_profanity(self, text):
        words = re.split(";|,|\:|\.|\?|\-|\!| ", text)
        has_swear = any(word.lower().startswith(swear) and word.lower().endswith(swear) for word in words for swear in swears)
        has_bad_phrase = any(phrase in text for phrase in phrases)
        return has_swear or has_bad_phrase

class AdviceDetector(StateExtractor):

    @property
    def type(self):
        return "conv"

    @property
    def state_var_names(self):
        return ['asks_advice']

    def __call__(self, state, history):
        super().__call__(state, history)
        state.asks_advice = "should i" in state.question.lower()
        state.asks_advice |= "advice" in state.question.lower()
        return True

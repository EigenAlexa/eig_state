import abc
from swear_words import words as swears
from swear_words import phrases
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

class ProfanityDetector(StateExtractor):

    @property
    def type(self):
        return "conv"

    @property
    def state_var_names(self):
        return ['has_swear']

    def __call__(self, state, history):
        state.has_swear = self.contains_profanity(state.question)
        return True

    def contains_profanity(self, text):
        words = re.split(";|,|\:|\.|\?|\-|\!| ", text)
        has_swear = any(word.lower().startswith(swear) and word.lower().endswith(swear) for word in words for swear in swears)
        has_bad_phrase = any(phrase in text for phrase in phrases)
        return has_swear or has_bad_phrase


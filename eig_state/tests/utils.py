from eig_state import state_extractors as se

def test_runs_conv_extractors(test_case, test_state):
    test_runs_extractors(test_case, test_state, "conv")

def test_runs_user_extractors(test_case, test_state):
    test_runs_extractors(test_case, test_state, "user")

def test_runs_extractors(test_case, test_state, extractor_type):
    extractors = se.StateExtractor.get_extractors(extractor_type)
    for extractor in extractors:
        for name in extractor.state_var_names:
            test_case.assertTrue(hasattr(test_state, name),
                                 msg="Extractor {} missing state var {}"
                                 .format(extractor.__class__.__name__, name))
            test_case.assertTrue(name in test_state.savers)

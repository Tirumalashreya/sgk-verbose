from agents.term_dictionary import load_terms, sarvam_keyterms, term_fidelity


def test_loads_terms_from_all_categories():
    terms = load_terms()
    assert len(terms) > 50
    assert len(terms) == len(set(terms))  # deduplicated


def test_sarvam_keyterms_respects_length_and_count_limits():
    kts = sarvam_keyterms(limit=10, max_len=20)
    assert len(kts) <= 10
    assert all(len(t) <= 20 for t in kts)


def test_fidelity_is_zero_for_empty_or_off_topic_text():
    assert term_fidelity("") == 0.0
    assert term_fidelity("the quick brown fox jumps") == 0.0


def test_fidelity_rises_with_known_terms_present():
    terms = load_terms()
    sample = " ".join(terms[:5]) * 20  # long enough that 5 distinct hits isn't trivially 1.0
    assert 0.0 < term_fidelity(sample) <= 1.0

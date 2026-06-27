from battle.catch_chain import CatchChain


def test_same_species_grows_the_chain():
    c = CatchChain()
    assert c.record_catch(99) == 1  # Kingler
    assert c.record_catch(99) == 2
    assert c.record_catch(99) == 3
    assert c.count == 3
    assert c.species == 99


def test_different_species_restarts_at_one():
    c = CatchChain()
    c.record_catch(99)
    c.record_catch(99)  # Kingler chain at 2
    assert c.record_catch(98) == 1  # Krabby breaks it -> fresh chain
    assert c.species == 98
    # going back to the old species starts ITS chain over, not resumes at 2
    assert c.record_catch(99) == 1


def test_length_for_only_applies_to_the_chained_species():
    c = CatchChain()
    c.record_catch(99)
    c.record_catch(99)
    assert c.length_for(99) == 2  # the chained species -> boost applies
    assert c.length_for(98) == 0  # a different species -> no Repeat boost
    assert c.length_for(None) == 0


def test_fresh_chain_is_zero():
    c = CatchChain()
    assert c.count == 0
    assert c.length_for(99) == 0


def test_chain_survives_non_catch_encounters():
    # KO'ing / fleeing don't call record_catch, so the chain is untouched between
    # catches -- only catching another species breaks it (in-game rule).
    c = CatchChain()
    c.record_catch(99)
    c.record_catch(99)
    # (a battle ends without a catch -- nothing is recorded)
    assert c.length_for(99) == 2
    assert c.record_catch(99) == 3


def test_import_and_basic_behavior():
    import main

    assert main.greet("World")[-1] == "World"
    assert main.check_value(None) is False
    assert main.check_value("x") is False


def test_literal_comparison_is_fixed():
    import main

    # Faulty fixture uses `is` for literal comparison; pactfix should rewrite to `==`.
    # Use a non-interned string to make this deterministic.
    val = ''.join(['t', 'e', 's', 't'])
    assert main.check_value(val) is True

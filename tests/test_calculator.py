def add(a, b):
    return a + b


def test_add_returns_sum():
    assert add(2, 3) == 5


def test_add_with_negative_numbers():
    assert add(2, -3) == -1

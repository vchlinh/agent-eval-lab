import pytest

from stats import moving_average


def test_basic_window_2():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_window_1_returns_values_as_floats():
    assert moving_average([1, 2, 3], 1) == [1.0, 2.0, 3.0]


def test_window_equals_length():
    assert moving_average([2, 4, 6], 3) == [4.0]


@pytest.mark.parametrize("window", [0, -1, -5])
def test_non_positive_window_raises_value_error(window):
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], window)


def test_window_larger_than_values_returns_empty_list():
    assert moving_average([1, 2, 3], 5) == []


def test_empty_values_returns_empty_list():
    assert moving_average([], 3) == []

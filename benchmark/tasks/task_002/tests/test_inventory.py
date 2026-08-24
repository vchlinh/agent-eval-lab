import pytest

from inventory import Inventory


def test_returns_items_at_or_below_threshold():
    inv = Inventory()
    inv.add("bolts", 3)
    inv.add("screws", 50)
    inv.add("nuts", 5)
    assert inv.low_stock(5) == ["bolts", "nuts"]


def test_sorted_alphabetically():
    inv = Inventory()
    inv.add("zinc", 1)
    inv.add("aluminum", 1)
    assert inv.low_stock(10) == ["aluminum", "zinc"]


def test_excludes_items_above_threshold():
    inv = Inventory()
    inv.add("screws", 50)
    assert inv.low_stock(5) == []


def test_boundary_quantity_equal_to_threshold_is_included():
    inv = Inventory()
    inv.add("bolts", 5)
    assert inv.low_stock(5) == ["bolts"]


def test_zero_quantity_after_full_removal_is_excluded():
    inv = Inventory()
    inv.add("bolts", 3)
    inv.remove("bolts", 3)
    assert inv.quantity_of("bolts") == 0
    assert inv.low_stock(100) == []


def test_empty_inventory_returns_empty_list():
    inv = Inventory()
    assert inv.low_stock(10) == []


def test_negative_threshold_returns_empty_list():
    inv = Inventory()
    inv.add("bolts", 3)
    assert inv.low_stock(-1) == []


def test_existing_methods_still_work():
    inv = Inventory()
    inv.add("bolts", 5)
    inv.add("bolts", 2)
    assert inv.quantity_of("bolts") == 7
    inv.remove("bolts", 3)
    assert inv.quantity_of("bolts") == 4
    with pytest.raises(ValueError):
        inv.remove("bolts", 100)

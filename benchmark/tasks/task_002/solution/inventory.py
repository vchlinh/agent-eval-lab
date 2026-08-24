class Inventory:
    """Tracks item quantities in a simple stockroom."""

    def __init__(self):
        self._stock = {}

    def add(self, item, quantity):
        self._stock[item] = self._stock.get(item, 0) + quantity

    def remove(self, item, quantity):
        if self._stock.get(item, 0) < quantity:
            raise ValueError(f"not enough stock of {item}")
        self._stock[item] -= quantity

    def quantity_of(self, item):
        return self._stock.get(item, 0)

    def low_stock(self, threshold):
        return sorted(item for item, qty in self._stock.items() if 0 < qty <= threshold)

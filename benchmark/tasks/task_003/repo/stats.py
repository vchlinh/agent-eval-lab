def moving_average(values, window):
    """Return the moving average of `values` over the given `window` size."""
    result = []
    for i in range(len(values) - window + 1):
        chunk = values[i:i + window]
        result.append(sum(chunk) / window)
    return result

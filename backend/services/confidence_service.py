def estimate_confidence(scores: list[float]) -> float:
    """Baseline helper; replace with a calibrated score once retrieval is implemented."""
    if not scores:
        return 0.0
    return max(0.0, min(1.0, float(max(scores))))

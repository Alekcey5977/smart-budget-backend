def get_crossed_thresholds(old_amount, old_total, new_amount, new_total):
    """
    Возвращает список пересечённых порогов прогресса.
    Пороги: 25%, 50%, 80%, 100%.
    Порог считается пересечённым если old_progress < порог <= new_progress.
    """
    if old_total <= 0 or new_total <= 0:
        return []

    old_progress = (old_amount / old_total) * 100
    new_progress = (new_amount / new_total) * 100

    thresholds = [25, 50, 80, 100]
    return [t for t in thresholds if old_progress < t <= new_progress]

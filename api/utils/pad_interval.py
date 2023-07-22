from api.config import (
    default_seconds_to_capture,
)

# adds or subtracts from end_seconds to get target_seconds
def pad_interval(start_seconds, end_seconds, **kwargs):
    target_seconds: int = kwargs.get(
        'target_seconds', default_seconds_to_capture)

    difference = end_seconds - start_seconds

    if difference < target_seconds:
        end_seconds += (target_seconds - difference)
    elif difference > target_seconds:
        end_seconds -= (difference - target_seconds)

    return start_seconds, end_seconds

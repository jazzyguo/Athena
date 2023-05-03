from typing import List, TypedDict, Tuple

Frames = List[Tuple[int, int]]


CalculatedFrame = TypedDict(
    'CalculatedFrame', {'interval': Tuple[int, int], 'db_level': int}
)

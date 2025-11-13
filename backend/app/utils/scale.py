import numpy as np
from typing import List


class ScoreScaler:
    @staticmethod
    def z_score_normalize(scores: List[float]) -> List[float]:
        if not scores:
            return []

        arr = np.array(scores, dtype=np.float32)
        mean = arr.mean()
        std = arr.std()

        if std == 0:
            return [0.0] * len(scores)

        return ((arr - mean) / std).tolist()


    @staticmethod
    def bm25_scale(scores: List[float]) -> List[float]:

        if not scores:
            return []

        arr = np.array(scores, dtype=np.float32)
        mean = arr.mean()
        std = arr.std()

        if std == 0:
            return [1.0] * len(scores)

        z = (arr - mean) / std
        return (1 / (1 + np.exp(-z))).tolist()

    @staticmethod
    def min_max_scale(scores: List[float]) -> List[float]:
        if not scores:
            return []

        arr = np.array(scores, dtype=np.float32)
        mn = arr.min()
        mx = arr.max()

        if mn == mx:
            return [1.0] * len(scores)

        return ((arr - mn) / (mx - mn)).tolist()

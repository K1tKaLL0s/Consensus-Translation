from dataclasses import dataclass
from math import isclose


@dataclass(frozen=True)
class AppSettings:
    translation_char_limit: int = 1000
    training_char_limit: int | None = None
    alpha: float = 0.5
    beta: float = 0.3
    gamma: float = 0.2
    confidence_threshold: float = 0.92

    def __post_init__(self) -> None:
        for name, value in (("alpha", self.alpha), ("beta", self.beta), ("gamma", self.gamma)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")

        weight_sum = self.alpha + self.beta + self.gamma
        if not isclose(weight_sum, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("alpha + beta + gamma must be approximately 1")

        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be within [0, 1]")

        if self.translation_char_limit <= 0:
            raise ValueError("translation_char_limit must be greater than 0")

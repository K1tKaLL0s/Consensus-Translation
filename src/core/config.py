from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    translation_char_limit: int = 1000
    training_char_limit: int | None = None
    alpha: float = 0.5
    beta: float = 0.3
    gamma: float = 0.2
    confidence_threshold: float = 0.92

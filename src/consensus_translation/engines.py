class LocalEngineA:
    def translate(self, text: str) -> tuple[str, float]:
        return (f"A::{text}", 0.45)


class LocalEngineB:
    def translate(self, text: str) -> tuple[str, float]:
        return (f"B::{text}", 0.4)

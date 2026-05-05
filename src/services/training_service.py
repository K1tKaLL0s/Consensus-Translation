def chunk_training_text(text: str, chunk_size: int = 4000) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

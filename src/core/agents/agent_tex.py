import re

from sklearn.feature_extraction.text import TfidfVectorizer


def extract_candidate_terms(text: str) -> list[str]:
    if not text or not text.strip():
        return []

    chunks = [part.strip() for part in re.split(r"[。！？\n]+", text) if part.strip()]
    if len(chunks) == 1:
        chunks = [chunks[0], chunks[0]]

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    matrix = vectorizer.fit_transform(chunks)
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()

    ranked_indices = scores.argsort()[::-1]
    results: list[str] = []
    for idx in ranked_indices:
        term = terms[idx].strip()
        if not term:
            continue
        results.append(term)
        if len(results) >= 10:
            break
    return results

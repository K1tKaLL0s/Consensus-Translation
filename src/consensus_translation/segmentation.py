from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    id: str
    text: str


@dataclass(frozen=True)
class Sentence:
    id: str
    text: str
    segment_id: str


@dataclass(frozen=True)
class Token:
    id: str
    text: str
    sentence_id: str
    priority_term: bool


@dataclass(frozen=True)
class HierarchyTree:
    segments: list[Segment]
    sentences: list[Sentence]
    tokens: list[Token]


def build_hierarchy(text: str, domain_terms: set[str] | None = None) -> HierarchyTree:
    terms = domain_terms or set()
    segments: list[Segment] = []
    sentences: list[Sentence] = []
    tokens: list[Token] = []
    token_index = 1

    raw_segments = [part.strip() for part in text.split("。") if part.strip()]
    for seg_num, segment_text in enumerate(raw_segments, start=1):
        segment_id = f"seg-{seg_num}"
        sentence_id = f"sent-{seg_num}"

        segment = Segment(id=segment_id, text=segment_text)
        sentence = Sentence(id=sentence_id, text=segment_text, segment_id=segment_id)
        segments.append(segment)
        sentences.append(sentence)

        seen_token_texts: set[str] = set()

        base_tokens = segment_text.replace("，", " ").split()
        for base_token in base_tokens:
            is_priority = base_token in terms
            tokens.append(
                Token(
                    id=f"tok-{token_index}",
                    text=base_token,
                    sentence_id=sentence_id,
                    priority_term=is_priority,
                )
            )
            token_index += 1
            seen_token_texts.add(base_token)

        for term in terms:
            if " " not in term:
                continue
            if term in segment_text and term not in seen_token_texts:
                tokens.append(
                    Token(
                        id=f"tok-{token_index}",
                        text=term,
                        sentence_id=sentence_id,
                        priority_term=True,
                    )
                )
                token_index += 1
                seen_token_texts.add(term)

    return HierarchyTree(segments=segments, sentences=sentences, tokens=tokens)

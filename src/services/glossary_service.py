def normalize_source_name(source_name: str) -> str:
    normalized = source_name.strip()
    if not normalized:
        raise ValueError("source_name must not be empty")
    return normalized


def validate_export_format(fmt: str) -> str:
    supported_formats = {"csv", "xlsx", "json"}
    if fmt not in supported_formats:
        raise ValueError("unsupported export format")
    return fmt


def parse_glossary_lines(lines: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        matched = False
        for separator in ("=", ",", "\t"):
            if separator not in line:
                continue
            left, right = line.split(separator, 1)
            term = left.strip()
            translation = right.strip()
            if term:
                entries.append({"term": term, "translation": translation})
            matched = True
            break

        if not matched:
            entries.append({"term": line, "translation": ""})
    return entries

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

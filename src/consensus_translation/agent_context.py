from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ContextBudget:
    max_context_tokens: int
    reserved_output_tokens: int = 512

    @property
    def available_input_tokens(self) -> int:
        return max(self.max_context_tokens - self.reserved_output_tokens, 0)


@dataclass(frozen=True)
class ContextSlice:
    index: int
    text: str
    estimated_tokens: int
    fits_current_task: bool


@dataclass(frozen=True)
class ContextSlicePlan:
    estimated_input_tokens: int
    available_input_tokens: int
    slices: list[ContextSlice]

    @property
    def initial_text(self) -> str:
        return "\n\n".join(
            item.text for item in self.slices if item.fits_current_task
        ).strip()

    @property
    def pending_text(self) -> str:
        return "\n\n".join(
            item.text for item in self.slices if not item.fits_current_task
        ).strip()


def estimate_context_tokens(text: str) -> int:
    cjk_chars = re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text)
    ascii_words = re.findall(r"[A-Za-z0-9]+", text)
    return len(cjk_chars) + len(ascii_words)


def _split_units(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if paragraphs:
        return paragraphs
    sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?])", text) if part.strip()]
    return sentences or ([text.strip()] if text.strip() else [])


def _split_unit_to_budget(unit: str, max_tokens: int) -> list[str]:
    if max_tokens <= 0 or estimate_context_tokens(unit) <= max_tokens:
        return [unit]

    chunks: list[str] = []
    current = ""
    for char in unit:
        candidate = f"{current}{char}"
        if current and estimate_context_tokens(candidate) > max_tokens:
            chunks.append(current.strip())
            current = char
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks


def plan_context_slices(text: str, budget: ContextBudget) -> ContextSlicePlan:
    available = budget.available_input_tokens
    used = 0
    slices: list[ContextSlice] = []
    normalized_units: list[str] = []
    for unit in _split_units(text):
        normalized_units.extend(_split_unit_to_budget(unit, available))

    for index, unit in enumerate(normalized_units):
        token_count = estimate_context_tokens(unit)
        fits = token_count > 0 and used + token_count <= available
        if fits:
            used += token_count
        slices.append(
            ContextSlice(
                index=index,
                text=unit,
                estimated_tokens=token_count,
                fits_current_task=fits,
            )
        )
    return ContextSlicePlan(
        estimated_input_tokens=estimate_context_tokens(text),
        available_input_tokens=available,
        slices=slices,
    )

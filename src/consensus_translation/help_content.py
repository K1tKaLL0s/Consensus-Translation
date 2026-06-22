from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_TOPIC_ORDER: tuple[str, ...] = (
    "quick-start",
    "connectors",
    "providers",
    "runtime-troubleshooting",
    "privacy-and-licenses",
)

TOPIC_TITLES: dict[str, str] = {
    "quick-start": "快速开始",
    "connectors": "连接器",
    "providers": "Provider 与评估器",
    "runtime-troubleshooting": "运行时排障",
    "privacy-and-licenses": "隐私与许可",
}

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "quick-start": ("开始", "翻译", "工作台", "人工确认", "导出"),
    "connectors": (
        "连接器",
        "Textractor",
        "LunaTranslator",
        "GalTransl",
        "OCR",
        "剪贴板",
        "文件夹",
    ),
    "providers": ("provider", "API", "OpenAI compatible", "COMET", "评估器"),
    "runtime-troubleshooting": ("Tesseract", "COMET", "E盘", "诊断", "runtime"),
    "privacy-and-licenses": ("隐私", "DPAPI", "Apache-2.0", "license", "NLLB"),
}


@dataclass(frozen=True)
class HelpTopic:
    topic_id: str
    title: str
    keywords: tuple[str, ...]
    markdown: str


@dataclass(frozen=True)
class HelpSearchResult:
    topic_id: str
    title: str
    markdown: str
    score: int


class HelpIndex:
    def __init__(self, topics: list[HelpTopic]) -> None:
        self._topics = topics

    @classmethod
    def load_default(cls, docs_root: str | Path | None = None) -> "HelpIndex":
        root = Path(docs_root) if docs_root else Path(__file__).resolve().parents[2]
        help_root = root / "docs" / "help"
        topics: list[HelpTopic] = []
        for topic_id in DEFAULT_TOPIC_ORDER:
            path = help_root / f"{topic_id}.md"
            markdown = path.read_text(encoding="utf-8") if path.exists() else ""
            topics.append(
                HelpTopic(
                    topic_id=topic_id,
                    title=TOPIC_TITLES[topic_id],
                    keywords=TOPIC_KEYWORDS[topic_id],
                    markdown=markdown,
                )
            )
        return cls(topics)

    def topic_ids(self) -> list[str]:
        return [topic.topic_id for topic in self._topics]

    def topics(self) -> list[HelpTopic]:
        return list(self._topics)

    def get(self, topic_id: str) -> HelpTopic:
        for topic in self._topics:
            if topic.topic_id == topic_id:
                return topic
        raise KeyError(f"help topic not found: {topic_id}")

    def search(self, query: str, limit: int = 10) -> list[HelpSearchResult]:
        normalized = query.casefold().strip()
        if not normalized:
            return [
                HelpSearchResult(
                    topic_id=topic.topic_id,
                    title=topic.title,
                    markdown=topic.markdown,
                    score=1,
                )
                for topic in self._topics[:limit]
            ]

        results: list[HelpSearchResult] = []
        for topic in self._topics:
            title = topic.title.casefold()
            keywords = tuple(keyword.casefold() for keyword in topic.keywords)
            body = topic.markdown.casefold()
            score = 0
            if normalized == title:
                score += 100
            if normalized in title:
                score += 50
            for keyword in keywords:
                if normalized == keyword:
                    score += 80
                elif normalized in keyword:
                    score += 40
            if normalized in body:
                score += 10 + body.count(normalized)
            if score:
                results.append(
                    HelpSearchResult(
                        topic_id=topic.topic_id,
                        title=topic.title,
                        markdown=topic.markdown,
                        score=score,
                    )
                )
        return sorted(results, key=lambda item: (-item.score, self.topic_ids().index(item.topic_id)))[:limit]

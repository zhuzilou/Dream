from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CardSection:
    title: str
    items: List[str] = field(default_factory=list)


@dataclass
class StructuredCard:
    title: str
    conclusion: str
    sections: List[CardSection] = field(default_factory=list)
    metadata: Optional[Dict[str, str]] = None


def render_markdown(card: StructuredCard) -> str:
    """将结构化卡片渲染为飞书 Markdown。"""
    lines = []
    if card.conclusion:
        lines.append(f"**结论先行**：{card.conclusion}")
        lines.append("")

    if card.metadata:
        timestamp = card.metadata.get("data_timestamp")
        if timestamp:
            lines.append(f"**数据时点**：{timestamp}")
            lines.append("")

    for section in card.sections:
        lines.append(f"**{section.title}**")
        if section.items:
            for item in section.items:
                lines.append(f"- {item}")
        else:
            lines.append("- 暂无")
        lines.append("")

    return "\n".join(lines).strip()

#!/usr/bin/env python3
"""
Generate a Markdown insight report from raw issue data and LLM classification results.

Usage:
    generate_report.py --repo owner/repo --days 7 \
        --raw issues_raw.json --classify classification.json \
        -o docs/repo_insight_20260530.md

No external Python dependencies (stdlib only).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

CATEGORY_CN = {
    "rfc": "RFC/正式提案",
    "design": "架构设计",
    "breaking": "破坏性变更",
    "governance": "社区治理",
    "ecosystem": "生态影响",
    "roadmap": "路线图/规划",
    "perf": "性能大改",
    "security": "安全架构",
    "other": "其他关注",
}

SIGNIFICANCE_CN = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


def load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_classification_map(classifications: list[dict]) -> dict[int, dict]:
    """Build a lookup: issue_number -> classification dict."""
    return {c["number"]: c for c in classifications}


def generate_report(
    repo: str,
    days: int,
    raw_issues: list[dict],
    classifications: list[dict],
    output_path: str,
) -> str:
    class_map = build_classification_map(classifications)
    noteworthy = [c for c in classifications if c.get("is_noteworthy")]
    noteworthy.sort(key=lambda c: {"high": 0, "medium": 1, "low": 2}.get(c.get("significance", "low"), 2))

    raw_map = {i["number"]: i for i in raw_issues}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    since = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Stats
    cat_counts: dict[str, int] = {}
    sig_counts: dict[str, int] = {}
    for n in noteworthy:
        cat = n.get("category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        sig = n.get("significance", "low")
        sig_counts[sig] = sig_counts.get(sig, 0) + 1

    lines = []
    lines.append(f"# {repo} 社区洞察报告")
    lines.append("")
    lines.append(f"**仓库**: `{repo}` | **时间范围**: 最近 {days} 天 | **生成时间**: {now}")
    lines.append("")

    # Overview
    lines.append("## 概览统计")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总 Issue 数 | {len(raw_issues)} |")
    lines.append(f"| 值得关注 | {len(noteworthy)} |")
    lines.append("")

    if cat_counts:
        lines.append("### 按分类分布")
        lines.append("")
        lines.append("| 分类 | 数量 |")
        lines.append("|------|------|")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {CATEGORY_CN.get(cat, cat)} | {count} |")
        lines.append("")

    if sig_counts:
        lines.append("### 按重要程度")
        lines.append("")
        lines.append("| 重要程度 | 数量 |")
        lines.append("|----------|------|")
        for sig in ["high", "medium", "low"]:
            if sig in sig_counts:
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sig, "")
                lines.append(f"| {icon} {SIGNIFICANCE_CN.get(sig, sig)} | {sig_counts[sig]} |")
        lines.append("")

    # Placeholder for LLM-written insights
    lines.append("## 核心洞察")
    lines.append("")
    lines.append("<!-- LLM_INSIGHT_PLACEHOLDER -->")
    lines.append("*（此章节由大模型分析完成后填充）*")
    lines.append("")

    # Detailed table
    lines.append("## 值得关注的 Issue")
    lines.append("")
    if noteworthy:
        lines.append("| # | 标题 | 分类 | 重要程度 | 判断理由 |")
        lines.append("|---|------|------|----------|----------|")
        for n in noteworthy:
            num = n["number"]
            title = n.get("title", "")
            issue = raw_map.get(num, {})
            url = issue.get("url", "")
            title_link = f"[{title}]({url})" if url else title
            cat = CATEGORY_CN.get(n.get("category", "other"), n.get("category", "other"))
            sig_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(n.get("significance", "low"), "")
            sig = f"{sig_icon} {SIGNIFICANCE_CN.get(n.get('significance', 'low'), n.get('significance', 'low'))}"
            reason = n.get("reason", "")
            lines.append(f"| #{num} | {title_link} | {cat} | {sig} | {reason} |")
    else:
        lines.append("*本期未发现值得关注的 Issue。*")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*报告由 github-community-insight 技能生成 | 数据来源: GitHub Issues API*")

    content = "\n".join(lines)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


def main():
    parser = argparse.ArgumentParser(description="Generate community insight MD report")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/repo format")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    parser.add_argument("--raw", required=True, help="Path to raw issues JSON")
    parser.add_argument("--classify", required=True, help="Path to classification JSON")
    parser.add_argument("-o", "--output", required=True, help="Output MD file path")
    args = parser.parse_args()

    raw = load_json(args.raw)
    classifications = load_json(args.classify)

    content = generate_report(args.repo, args.days, raw, classifications, args.output)
    print(f"Report saved to {args.output} ({len(raw)} issues, {sum(1 for c in classifications if c.get('is_noteworthy'))} noteworthy)", file=sys.stderr)
    print(content)


if __name__ == "__main__":
    main()

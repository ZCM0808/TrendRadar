# coding=utf-8
"""
通知内容渲染模块

提供多平台通知内容渲染功能，生成格式化的推送消息
"""

from datetime import datetime
from typing import Dict, List, Optional, Callable

from trendradar.report.formatter import format_title_for_platform


# 默认区域顺序
DEFAULT_REGION_ORDER = ["worldmonitor", "hotlist", "rss", "new_items", "standalone", "ai_analysis", "github"]


def render_feishu_content(
    report_data: Dict,
    update_info: Optional[Dict] = None,
    mode: str = "daily",
    separator: str = "---",
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[list] = None,
    show_new_section: bool = True,
    github_items: Optional[list] = None,
    worldmonitor_data: Optional[Dict] = None,
) -> str:
    """渲染飞书通知内容（支持热榜+RSS合并+GitHub+World Monitor）

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        update_info: 版本更新信息（可选）
        mode: 报告模式 ("daily", "incremental", "current")
        separator: 内容分隔符
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now()）
        rss_items: RSS 条目列表（可选，用于合并推送）
        show_new_section: 是否显示新增热点区域
        github_items: GitHub 项目列表（可选，用于合并推送）
        worldmonitor_data: World Monitor 全球态势情报数据（可选）

    Returns:
        格式化的飞书消息内容
    """
    if region_order is None:
        region_order = DEFAULT_REGION_ORDER

    # World Monitor 全球态势内容
    worldmonitor_content = ""
    if worldmonitor_data:
        worldmonitor_content = _render_worldmonitor_section_feishu(worldmonitor_data, separator)

    # 生成热点词汇统计部分
    stats_content = ""
    if report_data["stats"]:
        stats_content += "📊 **热点词汇统计**\n\n"

        total_count = len(report_data["stats"])

        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]

            sequence_display = f"<font color='grey'>[{i + 1}/{total_count}]</font>"

            if count >= 10:
                stats_content += f"🔥 {sequence_display} **{word}** : <font color='red'>{count}</font> 条\n"
            elif count >= 5:
                stats_content += f"📈 {sequence_display} **{word}** : <font color='orange'>{count}</font> 条\n"
            else:
                stats_content += f"📌 {sequence_display} **{word}** : {count} 条\n"

            for j, title_data in enumerate(stat["titles"], 1):
                formatted_title = format_title_for_platform(
                    "feishu", title_data, show_source=True
                )
                stats_content += f"  {j}. {formatted_title}\n"

    # 生成新增新闻部分
    new_titles_content = ""
    if show_new_section and report_data["new_titles"]:
        new_titles_content += (
            f"🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        )

        for source_data in report_data["new_titles"]:
            new_titles_content += (
                f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n"
            )

            for j, title_data in enumerate(source_data["titles"], 1):
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "feishu", title_data_copy, show_source=False
                )
                new_titles_content += f"  {j}. {formatted_title}\n"

            new_titles_content += "\n"

    # RSS 内容
    rss_content = ""
    if rss_items:
        rss_content = _render_rss_section_feishu(rss_items, separator)

    # GitHub 内容
    github_content = ""
    if github_items:
        github_content = _render_github_section_feishu(github_items, separator)

    # 准备各区域内容映射
    region_contents = {
        "worldmonitor": worldmonitor_content,
        "hotlist": stats_content,
        "new_items": new_titles_content,
        "rss": rss_content,
        "github": github_content,
    }

    # 按 region_order 顺序组装内容
    text_content = ""
    for region in region_order:
        content = region_contents.get(region, "")
        if content:
            if text_content:
                text_content += f"\n{separator}\n\n"
            text_content += content

    if not text_content:
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        text_content = f"📭 {mode_text}\n\n"

    if report_data["failed_ids"]:
        if text_content and "暂无匹配" not in text_content:
            text_content += f"\n{separator}\n\n"

        text_content += "⚠️ **数据获取失败的平台：**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • <font color='red'>{id_value}</font>\n"

    # 获取当前时间
    now = get_time_func() if get_time_func else datetime.now()
    text_content += (
        f"\n\n<font color='grey'>更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}</font>"
    )

    if update_info:
        text_content += f"\n<font color='grey'>TrendRadar 发现新版本 {update_info['remote_version']}，当前 {update_info['current_version']}</font>"

    return text_content


def render_dingtalk_content(
    report_data: Dict,
    update_info: Optional[Dict] = None,
    mode: str = "daily",
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[list] = None,
    show_new_section: bool = True,
    github_items: Optional[list] = None,
    worldmonitor_data: Optional[Dict] = None,
) -> str:
    """渲染钉钉通知内容（支持热榜+RSS合并+GitHub+World Monitor）

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        update_info: 版本更新信息（可选）
        mode: 报告模式 ("daily", "incremental", "current")
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now()）
        rss_items: RSS 条目列表（可选，用于合并推送）
        show_new_section: 是否显示新增热点区域
        github_items: GitHub 项目列表（可选，用于合并推送）
        worldmonitor_data: World Monitor 全球态势情报数据（可选）

    Returns:
        格式化的钉钉消息内容
    """
    if region_order is None:
        region_order = DEFAULT_REGION_ORDER

    # World Monitor 全球态势内容
    worldmonitor_content = ""
    if worldmonitor_data:
        worldmonitor_content = _render_worldmonitor_section_markdown(worldmonitor_data)

    total_titles = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )
    now = get_time_func() if get_time_func else datetime.now()

    # 头部信息
    header_content = f"**总新闻数：** {total_titles}\n\n"
    header_content += f"**时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    header_content += "**类型：** 热点分析报告\n\n"
    header_content += "---\n\n"

    # 生成热点词汇统计部分
    stats_content = ""
    if report_data["stats"]:
        stats_content += "📊 **热点词汇统计**\n\n"

        total_count = len(report_data["stats"])

        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]

            sequence_display = f"[{i + 1}/{total_count}]"

            if count >= 10:
                stats_content += f"🔥 {sequence_display} **{word}** : **{count}** 条\n"
            elif count >= 5:
                stats_content += f"📈 {sequence_display} **{word}** : **{count}** 条\n"
            else:
                stats_content += f"📌 {sequence_display} **{word}** : {count} 条\n"

            for j, title_data in enumerate(stat["titles"], 1):
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data, show_source=True
                )
                stats_content += f"  {j}. {formatted_title}\n"

    # 生成新增新闻部分
    new_titles_content = ""
    if show_new_section and report_data["new_titles"]:
        new_titles_content += (
            f"🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        )

        for source_data in report_data["new_titles"]:
            new_titles_content += f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"

            for j, title_data in enumerate(source_data["titles"], 1):
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data_copy, show_source=False
                )
                new_titles_content += f"  {j}. {formatted_title}\n"

            new_titles_content += "\n"

    # RSS 内容
    rss_content = ""
    if rss_items:
        rss_content = _render_rss_section_markdown(rss_items)

    # GitHub 内容
    github_content = ""
    if github_items:
        github_content = _render_github_section_markdown(github_items)

    # 准备各区域内容映射
    region_contents = {
        "worldmonitor": worldmonitor_content,
        "hotlist": stats_content,
        "new_items": new_titles_content,
        "rss": rss_content,
        "github": github_content,
    }

    # 按 region_order 顺序组装内容
    text_content = header_content
    has_content = False
    for region in region_order:
        content = region_contents.get(region, "")
        if content:
            if has_content:
                text_content += "\n---\n\n"
            text_content += content
            has_content = True

    if not has_content:
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        text_content += f"📭 {mode_text}\n\n"

    if report_data["failed_ids"]:
        if "暂无匹配" not in text_content:
            text_content += "\n---\n\n"

        text_content += "⚠️ **数据获取失败的平台：**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • **{id_value}**\n"

    text_content += f"\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"

    if update_info:
        text_content += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"

    return text_content



# === RSS 内容渲染辅助函数（用于合并推送） ===

def _render_rss_section_feishu(rss_items: list, separator: str = "---") -> str:
    """渲染 RSS 内容区块（飞书格式，用于合并推送）"""
    if not rss_items:
        return ""

    # 按 feed_id 分组
    feeds_map: Dict[str, list] = {}
    for item in rss_items:
        feed_id = item.get("feed_id", "unknown")
        if feed_id not in feeds_map:
            feeds_map[feed_id] = []
        feeds_map[feed_id].append(item)

    text_content = f"📰 **RSS 订阅更新** (共 {len(rss_items)} 条)\n"

    for feed_id, items in feeds_map.items():
        feed_name = items[0].get("feed_name", feed_id) if items else feed_id

        text_content += f"**{feed_name}** ({len(items)} 条)\n"

        for i, item in enumerate(items, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            published_at = item.get("published_at", "")

            if url:
                text_content += f"  {i}. [{title}]({url})"
            else:
                text_content += f"  {i}. {title}"

            if published_at:
                text_content += f" <font color='grey'>- {published_at}</font>"

            text_content += "\n"

        text_content += "\n"

    return text_content.rstrip("\n")


def _render_rss_section_markdown(rss_items: list) -> str:
    """渲染 RSS 内容区块（通用 Markdown 格式，用于合并推送）"""
    if not rss_items:
        return ""

    # 按 feed_id 分组
    feeds_map: Dict[str, list] = {}
    for item in rss_items:
        feed_id = item.get("feed_id", "unknown")
        if feed_id not in feeds_map:
            feeds_map[feed_id] = []
        feeds_map[feed_id].append(item)

    text_content = f"📰 **RSS 订阅更新** (共 {len(rss_items)} 条)\n"

    for feed_id, items in feeds_map.items():
        feed_name = items[0].get("feed_name", feed_id) if items else feed_id

        text_content += f"**{feed_name}** ({len(items)} 条)\n"

        for i, item in enumerate(items, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            published_at = item.get("published_at", "")

            if url:
                text_content += f"  {i}. [{title}]({url})"
            else:
                text_content += f"  {i}. {title}"

            if published_at:
                text_content += f" `{published_at}`"

            text_content += "\n"

        text_content += "\n"

    return text_content.rstrip("\n")


# === GitHub 内容渲染辅助函数（用于合并推送） ===

def _render_github_section_feishu(github_items: list, separator: str = "---") -> str:
    """渲染 GitHub 内容区块（飞书格式，用于合并推送）"""
    if not github_items:
        return ""

    text_content = f"🐙 **GitHub 热门项目** (共 {len(github_items)} 个)\n"

    for i, item in enumerate(github_items, 1):
        title = item.get("title", "")
        url = item.get("url", "")
        description = item.get("description", "")
        language = item.get("language", "")
        stars = item.get("stars", 0)

        if url:
            text_content += f"  {i}. [{title}]({url})"
        else:
            text_content += f"  {i}. {title}"

        if description:
            text_content += f"\n      <font color='grey'>{description[:100]}{'...' if len(description) > 100 else ''}</font>"

        meta_parts = []
        if language:
            meta_parts.append(f"📋 {language}")
        if stars:
            meta_parts.append(f"⭐ {stars}")
        if meta_parts:
            text_content += f"\n      <font color='grey'>{' · '.join(meta_parts)}</font>"

        text_content += "\n"

    return text_content.rstrip("\n")


def _render_github_section_markdown(github_items: list) -> str:
    """渲染 GitHub 内容区块（通用 Markdown 格式，用于合并推送）"""
    if not github_items:
        return ""

    text_content = f"🐙 **GitHub 热门项目** (共 {len(github_items)} 个)\n"

    for i, item in enumerate(github_items, 1):
        title = item.get("title", "")
        url = item.get("url", "")
        description = item.get("description", "")
        language = item.get("language", "")
        stars = item.get("stars", 0)

        if url:
            text_content += f"  {i}. [{title}]({url})"
        else:
            text_content += f"  {i}. {title}"

        if description:
            desc_short = description[:100] + ("..." if len(description) > 100 else "")
            text_content += f"\n      {desc_short}"

        meta_parts = []
        if language:
            meta_parts.append(f"📋 {language}")
        if stars:
            meta_parts.append(f"⭐ {stars}")
        if meta_parts:
            text_content += f"\n      {' · '.join(meta_parts)}"

        text_content += "\n"

    return text_content.rstrip("\n")


# === World Monitor 内容渲染辅助函数（用于战略情报推送） ===

def _render_worldmonitor_section_feishu(wm_data: Dict, separator: str = "---") -> str:
    """渲染 World Monitor 全球态势情报（飞书格式）"""
    if not wm_data:
        return ""

    lines = ["🌍 **World Monitor 全球地缘与宏观战略情报**\n"]

    summary = wm_data.get("summary", "")
    if summary:
        lines.append(f"⚡ **战略研判速览**：<font color='orange'>{summary}</font>\n")

    cii = wm_data.get("cii", [])
    if cii:
        lines.append("🛡️ **国家不稳定风险 (CII 指数 Top)**")
        for item in cii:
            name = item.get("name", "")
            score = item.get("score", 0)
            advisory = item.get("advisory", "")
            trend = item.get("trend", "平稳")
            lines.append(f"  • **{name}**: <font color='red'>{score:.1f}分</font> | {advisory} | 趋势: {trend}")
        lines.append("")

    chokepoints = wm_data.get("chokepoints", [])
    if chokepoints:
        lines.append("🚢 **全球海上战略咽喉通航状态**")
        for cp in chokepoints:
            name = cp.get("name", "")
            badge = cp.get("badge", "")
            desc = cp.get("desc", "")
            lines.append(f"  • **{name}**: {badge}\n    <font color='grey'>{desc}</font>")
        lines.append("")

    markets = wm_data.get("markets", [])
    if markets:
        lines.append("📈 **核心大宗商品与宏观金融指标**")
        for m in markets:
            name = m.get("name", "")
            price = m.get("price", 0)
            chg = m.get("change", 0)
            unit = m.get("unit", "")
            sign = "+" if chg > 0 else ""
            color = "red" if chg > 0 else "green"
            lines.append(f"  • **{name}**: {price:,.2f} {unit} (<font color='{color}'>{sign}{chg:.2f}%</font>)")
        lines.append("")

    return "\n".join(lines).strip()


def _render_worldmonitor_section_markdown(wm_data: Dict) -> str:
    """渲染 World Monitor 全球态势情报（通用 Markdown 格式）"""
    if not wm_data:
        return ""

    lines = ["🌍 **World Monitor 全球地缘与宏观战略情报**\n"]

    summary = wm_data.get("summary", "")
    if summary:
        lines.append(f"> ⚡ **战略研判速览**：{summary}\n")

    cii = wm_data.get("cii", [])
    if cii:
        lines.append("🛡️ **国家不稳定风险 (CII 指数 Top)**")
        for item in cii:
            name = item.get("name", "")
            score = item.get("score", 0)
            advisory = item.get("advisory", "")
            trend = item.get("trend", "平稳")
            lines.append(f"  • **{name}**: {score:.1f}分 | {advisory} | 趋势: {trend}")
        lines.append("")

    chokepoints = wm_data.get("chokepoints", [])
    if chokepoints:
        lines.append("🚢 **全球海上战略咽喉通航状态**")
        for cp in chokepoints:
            name = cp.get("name", "")
            badge = cp.get("badge", "")
            desc = cp.get("desc", "")
            lines.append(f"  • **{name}**: {badge}\n    `{desc}`")
        lines.append("")

    markets = wm_data.get("markets", [])
    if markets:
        lines.append("📈 **核心大宗商品与宏观金融指标**")
        for m in markets:
            name = m.get("name", "")
            price = m.get("price", 0)
            chg = m.get("change", 0)
            unit = m.get("unit", "")
            sign = "+" if chg > 0 else ""
            lines.append(f"  • **{name}**: {price:,.2f} {unit} ({sign}{chg:.2f}%)")
        lines.append("")

    return "\n".join(lines).strip()

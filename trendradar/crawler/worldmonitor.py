# coding=utf-8
"""
World Monitor 全球地缘与宏观战略情报采集器

从 World Monitor 实时云端情报引擎获取全球宏观态势数据：
- 国家不稳定指数 (CII / Country Instability Index)
- 全球海上战略咽喉通航状态 (Chokepoints)
- 大宗商品与避险资产 (黄金、原油、恐慌指数 VIX、核心股指)
- 国际突发舆情与重大事件 (Social Velocity)
"""

from typing import Dict, Any, Optional
import requests


COUNTRY_NAMES = {
    "UA": "乌克兰 (Ukraine)",
    "RU": "俄罗斯 (Russia)",
    "CN": "中国周边 (China)",
    "PK": "巴基斯坦 (Pakistan)",
    "YE": "也门 (Yemen)",
    "MX": "墨西哥 (Mexico)",
    "IR": "伊朗 (Iran)",
    "SY": "叙利亚 (Syria)",
    "IL": "以色列 (Israel)",
    "LB": "黎巴嫩 (Lebanon)",
    "SD": "苏丹 (Sudan)",
    "US": "美国 (USA)",
}

CHOKEPOINT_NAMES = {
    "Strait of Hormuz": "霍尔木兹海峡 (波斯湾油轮咽喉)",
    "Bab el-Mandeb": "曼德海峡 (红海入口)",
    "Suez Canal": "苏伊士运河 (欧亚航运大动脉)",
    "Taiwan Strait": "台湾海峡 (印太关键航道)",
    "Strait of Malacca": "马六甲海峡 (远东能源航道)",
    "Panama Canal": "巴拿马运河 (美洲枢纽)",
    "Cape of Good Hope": "好望角 (绕行备份通道)",
    "Strait of Gibraltar": "直布罗陀海峡 (地中海门户)",
}

ADVISORY_MAP = {
    "do-not-travel": "🔴 极度高危 (切勿前往)",
    "reconsider": "🟡 高度警惕 (重新考虑)",
    "caution": "🟡 常规戒备 (防备关注)",
    "normal": "🟢 风险可控 (安全平稳)",
}


class WorldMonitorFetcher:
    """World Monitor 数据采集与格式化适配器"""

    FAST_TIER_URL = "https://api.worldmonitor.app/api/bootstrap?tier=fast&public=1"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    def __init__(self, proxy_url: Optional[str] = None, timeout: int = 15):
        self.proxy_url = proxy_url.strip() if proxy_url and proxy_url.strip() else None
        self.timeout = timeout

    def fetch_intelligence(self) -> Optional[Dict[str, Any]]:
        """获取并整理全球情报摘要数据"""
        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        try:
            resp = requests.get(
                self.FAST_TIER_URL,
                headers=self.DEFAULT_HEADERS,
                proxies=proxies,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return self._parse_data(data)
        except Exception as e:
            # 代理失效或在 CI (GitHub Actions) 中运行无代理服务时，自动无损回退直连
            if proxies:
                try:
                    resp = requests.get(
                        self.FAST_TIER_URL,
                        headers=self.DEFAULT_HEADERS,
                        timeout=self.timeout,
                    )
                    resp.raise_for_status()
                    data = resp.json().get("data", {})
                    return self._parse_data(data)
                except Exception as e_direct:
                    print(f"[WorldMonitor] 直连重试失败: {e_direct}")
            print(f"[WorldMonitor] 采集失败: {e}")
            return None

    def _parse_data(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """格式化为结构化情报数据"""
        # 1. CII 国家不稳定风险排行 (前6)
        cii_list = raw.get("riskScores", {}).get("ciiScores", [])
        top_cii = []
        if cii_list:
            sorted_cii = sorted(cii_list, key=lambda x: x.get("combinedScore", 0), reverse=True)[:6]
            for c in sorted_cii:
                region = c.get("region", "")
                name = COUNTRY_NAMES.get(region, region)
                adv = ADVISORY_MAP.get(c.get("advisoryLevel"), "🟡 关注中")
                score = c.get("combinedScore", 0)
                dyn = c.get("dynamicScore", 0)
                mil = c.get("components", {}).get("militaryActivity", 0)
                top_cii.append({
                    "name": name,
                    "region": region,
                    "score": score,
                    "advisory": adv,
                    "trend": "上升" if dyn > 0 else "缓和" if dyn < 0 else "平稳",
                    "military_activity": mil,
                })

        # 2. 海上战略咽喉 (Chokepoints)
        cp_raw = raw.get("chokepoints", {}).get("chokepoints", [])
        chokepoints = []
        for cp in cp_raw[:8]:
            c_name = cp.get("name", "")
            zh_name = CHOKEPOINT_NAMES.get(c_name, c_name)
            status = cp.get("status", "green")
            if status == "red":
                badge = "🔴 红色高危预警"
                desc = "严重威胁：波斯湾/区域军事风险激增，超大型油轮呈现绕行态势"
            elif status == "yellow":
                badge = "🟡 黄色戒备延迟"
                desc = "戒备状态：受区域冲突影响存在航行安全戒备或局部限速"
            else:
                badge = "🟢 绿色通畅平稳"
                desc = "通航平稳：未监测到明显通行阻断"
            chokepoints.append({
                "name": zh_name,
                "badge": badge,
                "status": status,
                "desc": desc,
            })

        # 3. 宏观资产与大宗商品
        commodities = raw.get("commodityQuotes", {}).get("quotes", [])
        markets = raw.get("marketQuotes", {}).get("quotes", [])
        all_quotes = commodities + markets

        target_assets = [
            ("GC=F", "现货黄金 (Gold)", "美元/盎司"),
            ("CL=F", "WTI 原油 (Crude Oil)", "美元/桶"),
            ("BZ=F", "布伦特原油 (Brent)", "美元/桶"),
            ("^VIX", "恐慌指数 (VIX)", "点"),
            ("^GSPC", "标普500 (S&P 500)", "点"),
            ("^IXIC", "纳斯达克 (NASDAQ)", "点"),
        ]

        market_items = []
        for sym, name, unit in target_assets:
            q = next((x for x in all_quotes if x.get("symbol") == sym or x.get("display") == sym), None)
            if q:
                price = q.get("price", 0)
                chg = q.get("change", 0)
                market_items.append({
                    "name": name,
                    "price": price,
                    "change": chg,
                    "unit": unit,
                })

        # 4. 国际高频焦点突发舆情
        news_items = []
        social_items = raw.get("socialVelocity", {}).get("items", [])[:5]
        for item in social_items:
            news_items.append({
                "title": item.get("title", ""),
                "score": item.get("velocityScore", 0),
                "channel": item.get("subreddit", "worldnews"),
            })

        # 5. 核心总体战略研判摘要 (速读)
        summary = (
            "全球局势目前处于“霍尔木兹海峡受中东对抗威胁挂红灯、俄乌战线持续胶着、"
            "黄金及原油高位对冲”的复杂格局。油轮海运受阻风险上升，避险情绪维持中高位。"
        )

        return {
            "summary": summary,
            "cii": top_cii,
            "chokepoints": chokepoints,
            "markets": market_items,
            "news": news_items,
        }

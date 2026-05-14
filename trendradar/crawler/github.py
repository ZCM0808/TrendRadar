# coding=utf-8
"""
GitHub 热门项目爬虫模块

负责从 GitHub API 搜索热门项目，支持：
- 按关键词搜索
- 按星标数筛选
- 按语言筛选
- 代理支持
"""

import json
import random
import time
from typing import Dict, List, Tuple, Optional

import requests


class GitHubFetcher:
    """GitHub 数据获取器"""

    # GitHub Search API
    SEARCH_API_URL = "https://api.github.com/search/repositories"

    # 默认请求头
    DEFAULT_HEADERS = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "TrendRadar-GitHub-Crawler/1.0",
    }

    def __init__(
        self,
        token: Optional[str] = None,
        proxy_url: Optional[str] = None,
    ):
        """
        初始化 GitHub 获取器

        Args:
            token: GitHub Personal Access Token（可选，提高速率限制）
            proxy_url: 代理服务器 URL（可选）
        """
        self.token = token
        self.proxy_url = proxy_url
        self.headers = self.DEFAULT_HEADERS.copy()

        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def search_repositories(
        self,
        keyword: str,
        min_stars: int = 100,
        max_stars: Optional[int] = None,
        language: Optional[str] = None,
        pushed_after: Optional[str] = None,
        per_page: int = 100,
        page: int = 1,
    ) -> Tuple[List[Dict], int]:
        """
        搜索仓库

        Args:
            keyword: 搜索关键词
            min_stars: 最低星标数
            max_stars: 最高星标数
            language: 编程语言
            pushed_after: 最后更新时间（格式：YYYY-MM-DD）
            per_page: 每页数量
            page: 页码

        Returns:
            (项目列表, 总数)
        """
        query_parts = [keyword]

        if min_stars:
            query_parts.append(f"stars:>={min_stars}")
        if max_stars:
            query_parts.append(f"stars:<={max_stars}")
        if language:
            query_parts.append(f"language:{language}")
        if pushed_after:
            query_parts.append(f"pushed:>{pushed_after}")

        query = " ".join(query_parts)

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(per_page, 100),
            "page": page,
        }

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        try:
            response = requests.get(
                self.SEARCH_API_URL,
                headers=self.headers,
                params=params,
                proxies=proxies,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("items", []), data.get("total_count", 0)
            elif response.status_code == 403:
                print(f"⚠️ GitHub API 速率限制，等待 60 秒...")
                time.sleep(60)
                return [], 0
            else:
                print(f"❌ GitHub API 错误: {response.status_code}")
                return [], 0
        except Exception as e:
            print(f"❌ GitHub API 请求异常: {e}")
            return [], 0

    def crawl_github_projects(
        self,
        keywords: List[str],
        min_stars: int = 100,
        total_per_keyword: int = 50,
        language: Optional[str] = None,
        pushed_after: Optional[str] = None,
        request_interval: int = 2000,
    ) -> Tuple[Dict, Dict, List]:
        """
        爬取 GitHub 热门项目

        Args:
            keywords: 关键词列表
            min_stars: 最低星标数
            total_per_keyword: 每个关键词扫描数量
            language: 编程语言
            pushed_after: 最近更新时间
            request_interval: 请求间隔（毫秒）

        Returns:
            (结果字典, ID到名称的映射, 失败ID列表) 元组
        """
        results = {}
        id_to_name = {}
        failed_ids = []

        for keyword in keywords:
            print(f"🔍 扫描关键词: {keyword}")
            all_projects = []
            page = 1

            while len(all_projects) < total_per_keyword:
                projects, total_count = self.search_repositories(
                    keyword=keyword,
                    min_stars=min_stars,
                    language=language,
                    pushed_after=pushed_after,
                    per_page=100,
                    page=page,
                )

                if not projects:
                    break

                all_projects.extend(projects)
                print(f"  📦 已获取 {len(all_projects)} / {total_count} 个项目")

                if len(projects) < 100:
                    break

                page += 1
                time.sleep(request_interval / 1000)

            # 处理结果
            for project in all_projects[:total_per_keyword]:
                repo_id = str(project.get("id", ""))
                name = project.get("full_name", "")
                description = project.get("description") or "无描述"
                stars = project.get("stargazers_count", 0)
                url = project.get("html_url", "")
                language = project.get("language") or "未知"

                id_to_name[repo_id] = name

                # 构建标题（类似热榜格式）
                title = f"[{stars}⭐] {name}"

                results[title] = {
                    "ranks": [stars],  # 用星标数作为排名
                    "url": url,
                    "mobileUrl": url,
                    "description": description,
                    "language": language,
                    "stars": stars,
                }

            time.sleep(request_interval / 1000)

        print(f"✅ GitHub 扫描完成，共获取 {len(results)} 个项目")
        return results, id_to_name, failed_ids


def create_github_fetcher(config: Dict) -> GitHubFetcher:
    """
    创建 GitHub 获取器

    Args:
        config: 配置字典

    Returns:
        GitHubFetcher 实例
    """
    return GitHubFetcher(
        token=config.get("github_token"),
        proxy_url=config.get("proxy_url"),
    )

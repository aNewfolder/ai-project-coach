#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
daily_radar.py - GitHub AI 热门项目每日筛选并推送飞书

功能：
1. 抓取 GitHub Trending (Python) 和 GitHub API 搜索 AI 相关项目
2. 获取每个项目的详细信息（Stars、README、周增长等）
3. 通过 DeepSeek 大模型筛选出 5 个最值得推荐的项目
4. 推送富文本消息到飞书群
5. 维护推荐历史，避免重复推荐

依赖：Python 3.10+，仅使用标准库 + requests
"""

import os
import sys
import json
import re
import base64
import time
import datetime
import argparse
import logging
from typing import List, Dict, Any, Optional, Tuple

import requests

# ==================== 配置常量 ====================
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 30

GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_PER_PAGE = 50           # 搜索 API 每页结果数
GITHUB_TRENDING_URL = "https://github.com/trending/python?since=daily"
REQUEST_TIMEOUT = 15                  # 普通请求超时
REQUEST_RETRY = 3                     # 重试次数
RATE_LIMIT_SLEEP = 1                  # 遇到限流时等待秒数

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 辅助函数 ====================
def load_dotenv(path=".env"):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if 'export ' in line:
                    line = line.replace('export ', '')
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"\'')

def get_env_var(name: str) -> str:
    """从环境变量获取配置，缺失则退出"""
    value = os.environ.get(name)
    if not value:
        logger.error(f"缺少环境变量: {name}")
        sys.exit(1)
    return value


# def load_feishu_webhook() -> str:
#     """从 ~/.openclaw/config/feishu.json 读取飞书 webhook URL"""
#     config_path = os.path.expanduser("~/.openclaw/config/feishu.json")
#     try:
#         with open(config_path, 'r', encoding='utf-8') as f:
#             config = json.load(f)
#         webhook = config.get("feishu_webhook_url")
#         if not webhook:
#             raise ValueError("feishu_webhook_url 不存在")
#         return webhook
#     except Exception as e:
#         logger.error(f"读取飞书配置文件失败: {e}")
#         sys.exit(1)

def load_feishu_webhook() -> str:
    """临时测试：直接返回已知的飞书 webhook URL"""
    # 请替换成你的真实 Webhook 地址
    return "https://open.feishu.cn/open-apis/bot/v2/hook/9bfabace-0aee-4fd7-b0fd-01da4ac9b034"

def read_history(history_path: str) -> List[str]:
    """读取已推荐的历史项目列表（repo_full_name）"""
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("recommended", [])
    except Exception as e:
        logger.warning(f"读取历史文件失败: {e}，将视为空历史")
        return []


def write_history(history_path: str, recommended: List[str]):
    """更新历史文件，追加新的推荐项目"""
    existing = read_history(history_path)
    updated = list(dict.fromkeys(existing + recommended))  # 去重保留顺序
    try:
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump({"recommended": updated}, f, indent=2, ensure_ascii=False)
        logger.info(f"历史文件已更新: {history_path}")
    except Exception as e:
        logger.error(f"写入历史文件失败: {e}")


def safe_request(method: str, url: str, headers: Optional[Dict] = None,
                 params: Optional[Dict] = None, json_data: Optional[Dict] = None,
                 retries: int = REQUEST_RETRY) -> requests.Response:
    """带重试的请求封装"""
    for attempt in range(retries):
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=REQUEST_TIMEOUT
            )
            # GitHub API 限流处理
            if resp.status_code == 403 and 'rate limit' in resp.text.lower():
                logger.warning("触发 GitHub API 限流，等待 %d 秒后重试", RATE_LIMIT_SLEEP)
                time.sleep(RATE_LIMIT_SLEEP)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求失败 (尝试 {attempt+1}/{retries}): {e}")
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # 退避
    raise RuntimeError(f"请求 {url} 重试 {retries} 次后仍失败")


# ==================== 抓取候选项目 ====================
def fetch_trending_projects(github_token: str) -> List[Dict]:
    """从 GitHub Trending 页面解析项目 (Python)"""
    headers = {"User-Agent": "daily-radar-script", "Accept": "text/html"}
    resp = safe_request("GET", GITHUB_TRENDING_URL, headers=headers)
    html = resp.text

    # 正则提取每个仓库卡片
    # 匹配格式: <article class="Box-row"> ... <h2><a href="/owner/repo">...</a></h2> ... <p>描述</p> ... <span>xxx stars today</span>
    pattern = re.compile(
        r'<h2 class="h3 lh-condensed">\s*<a[^>]+href="/([^/]+)/([^"]+)"[^>]*>.*?</a>\s*</h2>'
        r'.*?<p class="col-9 color-fg-muted my-1 pr-4">(.*?)</p>'
        r'.*?<span class="d-inline-block float-sm-right">\s*([\d,]+)\s+stars today\s*</span>',
        re.DOTALL | re.IGNORECASE
    )
    projects = []
    for match in pattern.finditer(html):
        owner = match.group(1)
        repo = match.group(2)
        full_name = f"{owner}/{repo}"
        description = re.sub(r'\s+', ' ', match.group(3)).strip()
        today_stars_str = match.group(4).replace(',', '')
        try:
            today_stars = int(today_stars_str)
        except ValueError:
            today_stars = 0
        projects.append({
            "full_name": full_name,
            "stars": None,          # 待后续 API 填充
            "weekly_growth": today_stars,   # 近似作为周增长（至少是今日）
            "description": description,
            "source": "trending"
        })
        if len(projects) >= 25:   # trending 最多取前 25 个
            break

    logger.info(f"从 Trending 抓取到 {len(projects)} 个项目")
    return projects


def search_github_api_projects(github_token: str) -> List[Dict]:
    """通过 GitHub 搜索 API 获取 AI 相关热门项目"""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "daily-radar-script"
    }
    # 查询条件：topic 包含 AI/ML/LLM/深度学习
    query = "ai OR machine-learning OR llm OR deep-learning"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": GITHUB_SEARCH_PER_PAGE
    }
    url = f"{GITHUB_API_BASE}/search/repositories"
    resp = safe_request("GET", url, headers=headers, params=params)
    data = resp.json()
    items = data.get("items", [])
    projects = []
    for item in items:
        full_name = item["full_name"]
        # 避免重复抓取太多，初步存储基本信息
        projects.append({
            "full_name": full_name,
            "stars": item["stargazers_count"],
            "weekly_growth": None,   # 后续通过 stargazers API 单独计算
            "description": item.get("description", ""),
            "source": "api_search"
        })
    logger.info(f"从 GitHub API 搜索到 {len(projects)} 个项目")
    return projects


def fetch_repo_details(github_token: str, full_name: str) -> Dict:
    """获取仓库详细信息：stars, forks, language, updated_at, readme 内容（前3000字符）"""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "daily-radar-script"
    }
    # 仓库基本信息
    repo_url = f"{GITHUB_API_BASE}/repos/{full_name}"
    repo_resp = safe_request("GET", repo_url, headers=headers)
    repo_data = repo_resp.json()

    # README
    readme_content = ""
    readme_url = f"{GITHUB_API_BASE}/repos/{full_name}/readme"
    try:
        readme_resp = safe_request("GET", readme_url, headers=headers)
        readme_json = readme_resp.json()
        if "content" in readme_json:
            decoded = base64.b64decode(readme_json["content"]).decode("utf-8", errors="ignore")
            readme_content = decoded[:3000]   # 截取前3000字符
    except Exception as e:
        logger.debug(f"获取 README 失败 {full_name}: {e}")

    return {
        "full_name": full_name,
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "language": repo_data.get("language", "Unknown"),
        "description": repo_data.get("description", ""),
        "updated_at": repo_data.get("updated_at", ""),
        "readme_snippet": readme_content,
    }


def fetch_weekly_star_growth(github_token: str, full_name: str) -> Optional[int]:
    """
    获取项目最近 7 天内获得的星标数量（近似）
    通过获取 stargazers 列表的前 100 条，统计最近 7 天内的星标数
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.star+json",
        "User-Agent": "daily-radar-script"
    }
    url = f"{GITHUB_API_BASE}/repos/{full_name}/stargazers"
    params = {"per_page": 100, "page": 1}
    try:
        resp = safe_request("GET", url, headers=headers, params=params)
        stargazers = resp.json()
        if not isinstance(stargazers, list):
            return None
        week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        count = 0
        for star in stargazers:
            # 条目中包含 "starred_at" 字段（需要 Accept: application/vnd.github.v3.star+json）
            starred_at = star.get("starred_at")
            if starred_at:
                star_time = datetime.datetime.fromisoformat(starred_at.replace('Z', '+00:00'))
                if star_time > week_ago:
                    count += 1
        return count
    except Exception as e:
        logger.debug(f"获取周增长失败 {full_name}: {e}")
        return None


def merge_and_enrich(github_token: str,
                     trending_projs: List[Dict],
                     api_projs: List[Dict]) -> List[Dict]:
    """
    合并 trending 和 API 项目，去重（优先保留 trending 中的 weekly_growth），
    并补全 stars、readme 等详细信息
    """
    merged = {}
    # 先添加 trending 项目
    for proj in trending_projs:
        full_name = proj["full_name"]
        merged[full_name] = {
            "full_name": full_name,
            "stars": None,
            "weekly_growth": proj.get("weekly_growth"),
            "description": proj.get("description", ""),
            "source": "trending"
        }
    # 再添加 API 项目，如果已存在则保留 trending 的 weekly_growth
    for proj in api_projs:
        full_name = proj["full_name"]
        if full_name in merged:
            # 如果 trending 没有 stars 值，用 API 的补上
            if merged[full_name]["stars"] is None:
                merged[full_name]["stars"] = proj.get("stars")
            # 描述优先用 trending 的（更简洁），如果没有才用 API 的
            if not merged[full_name]["description"]:
                merged[full_name]["description"] = proj.get("description", "")
        else:
            merged[full_name] = {
                "full_name": full_name,
                "stars": proj.get("stars"),
                "weekly_growth": None,
                "description": proj.get("description", ""),
                "source": "api_search"
            }

    # 现在为每个项目获取详细信息和补充周增长（如果缺失）
    enriched = []
    for full_name, info in merged.items():
        logger.info(f"获取详细信息: {full_name}")
        try:
            details = fetch_repo_details(github_token, full_name)
            # 如果 stars 还是空，用 API 的值
            if info["stars"] is None:
                info["stars"] = details["stars"]
            # 如果 weekly_growth 为空，尝试计算周增长
            if info["weekly_growth"] is None:
                growth = fetch_weekly_star_growth(github_token, full_name)
                info["weekly_growth"] = growth if growth is not None else 0
            # 合并所有信息
            final = {
                "full_name": full_name,
                "stars": info["stars"],
                "weekly_growth": info["weekly_growth"],
                "description": details["description"] if details["description"] else info["description"],
                "language": details["language"],
                "forks": details["forks"],
                "updated_at": details["updated_at"],
                "readme_snippet": details["readme_snippet"],
                "source": info["source"]
            }
            enriched.append(final)
        except Exception as e:
            logger.error(f"获取 {full_name} 详细信息失败: {e}，跳过该项目")
            continue
        # 礼貌延时，避免 API 限流
        time.sleep(0.2)
    return enriched


def filter_excluded_by_history(projects: List[Dict], history: List[str]) -> List[Dict]:
    """过滤掉已经推荐过的项目"""
    filtered = [p for p in projects if p["full_name"] not in history]
    logger.info(f"历史已推荐 {len(history)} 个，剩余候选 {len(filtered)} 个")
    return filtered


# ==================== DeepSeek 筛选 ====================
def call_deepseek_selection(projects: List[Dict], api_key: str) -> List[Dict]:
    """
    调用 DeepSeek 模型，从候选项目中选出 5 个最值得推荐的
    返回解析后的 JSON 列表
    """
    # 准备候选项目列表，去除过长的 README 片段（保留前 800 字符以供判断 Installation 等）
    candidates = []
    for p in projects:
        candidates.append({
            "repo_full_name": p["full_name"],
            "stars": p["stars"],
            "weekly_growth": p["weekly_growth"],
            "description": p["description"][:200] if p["description"] else "",
            "language": p.get("language", "Unknown"),
            "readme_preview": p["readme_snippet"][:800]   # 供模型检查安装指南等
        })

    prompt = f"""你是一个面向大学生的 AI 项目推荐专家。请从以下候选项目中选出 5 个最值得推荐的：
- 2 个"经典必跑"：星标>10K，长期稳定，文档完善，对大学生有实用价值
- 3 个"近期飙升"：近 7 天星标增长最快，有部署指引，非纯论文复现

排除标准：
- 纯 SDK/库/框架（如 PyTorch、TensorFlow 本身）
- 没有 Installation / Quick Start / Getting Started 章节的项目
- 纯论文复现类项目（README 主要是论文引用和复现步骤）

候选项目列表（JSON 格式）：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

请严格以 JSON 格式返回，包含 5 个项目，每个项目包含以下字段：
{{
    "repo_full_name": "owner/repo",
    "category": "classic" 或 "trending",
    "stars": 数字,
    "weekly_growth": 数字或null,
    "one_liner": "一句话中文功能描述（不超过30字）",
    "tech_stack": "主要技术栈",
    "deploy_difficulty": 1-5的数字,
    "student_value": "对大学生的价值（一段话）"
}}
不要输出任何其他文字，只输出 JSON 数组。"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个严谨的推荐专家，只返回合法的 JSON。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}   # DeepSeek 支持 JSON 模式
    }
    url = f"{DEEPSEEK_API_BASE}/chat/completions"
    resp = safe_request("POST", url, headers=headers, json_data=payload, retries=2)
    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # 尝试提取 JSON 部分（防止模型输出额外说明）
    json_match = re.search(r'\[.*]', content, re.DOTALL)
    if json_match:
        content = json_match.group(0)
    try:
        selected = json.loads(content)
        if isinstance(selected, dict) and "recommendations" in selected:
            # 兼容某些模型嵌套输出
            selected = selected["recommendations"]
        if not isinstance(selected, list):
            raise ValueError("返回的不是数组")
        # 确保每个项目都有必要字段
        for item in selected:
            if "repo_full_name" not in item:
                raise ValueError("缺少 repo_full_name")
        return selected[:5]
    except Exception as e:
        logger.error(f"解析 DeepSeek 返回失败: {e}\n原始内容: {content}")
        # 降级：返回前 5 个按星标排序的项目作为兜底
        logger.warning("使用降级策略：按星标排序取前5")
        fallback = []
        for p in sorted(projects, key=lambda x: x["stars"] or 0, reverse=True)[:5]:
            fallback.append({
                "repo_full_name": p["full_name"],
                "category": "trending",
                "stars": p["stars"],
                "weekly_growth": p["weekly_growth"],
                "one_liner": p["description"][:30],
                "tech_stack": p.get("language", "Unknown"),
                "deploy_difficulty": 3,
                "student_value": "无详细说明"
            })
        return fallback


# ==================== 飞书消息推送 ====================
def build_feishu_post_message(selected: List[Dict], date_str: str) -> Dict:
    """
    构建飞书富文本消息 (post 类型)
    格式要求：
    🤖 今日 AI 项目推荐 | {日期}
    ━━━ 🏆 经典必跑 ━━━
    1️⃣ 项目名 ⭐ 星标数
    一句话描述
    技术栈：xxx
    部署难度：⭐⭐⭐
    对你的价值：xxx
    ... 近期飙升同理
    """
    # 分离 classic 和 trending
    classic = [p for p in selected if p.get("category") == "classic"]
    trending = [p for p in selected if p.get("category") == "trending"]

    # 飞书 post 消息的内容是一个二维数组，每个元素是一个段落（由 tag 对象数组组成）
    content = []

    # 标题行
    title_text = f"🤖 今日 AI 项目推荐 | {date_str}"
    content.append([{"tag": "text", "text": title_text}])
    content.append([{"tag": "text", "text": ""}])  # 空行

    # 经典必跑区块
    if classic:
        content.append([{"tag": "text", "text": "━━━ 🏆 经典必跑 ━━━"}])
        for idx, proj in enumerate(classic, start=1):
            name = proj["repo_full_name"]
            stars = proj.get("stars", 0)
            stars_str = f"{stars:,}"
            one_liner = proj.get("one_liner", "")
            tech_stack = proj.get("tech_stack", "未知")
            difficulty = proj.get("deploy_difficulty", 3)
            stars_emoji = "⭐" * difficulty
            student_value = proj.get("student_value", "")

            lines = [
                f"{idx}️⃣ {name} ⭐ {stars_str}",
                f"{one_liner}",
                f"技术栈：{tech_stack}",
                f"部署难度：{stars_emoji}",
                f"对你的价值：{student_value}",
                ""
            ]
            for line in lines:
                if line.strip() or line == "":
                    content.append([{"tag": "text", "text": line}])
    else:
        content.append([{"tag": "text", "text": "━━━ 🏆 经典必跑 ━━━ 无"}])

    # 近期飙升区块
    if trending:
        content.append([{"tag": "text", "text": "━━━ 🔥 近期飙升 ━━━"}])
        for idx, proj in enumerate(trending, start=1):
            name = proj["repo_full_name"]
            stars = proj.get("stars", 0)
            weekly = proj.get("weekly_growth")
            stars_str = f"{stars:,}"
            growth_str = f"（本周 +{weekly}）" if weekly else ""
            one_liner = proj.get("one_liner", "")
            tech_stack = proj.get("tech_stack", "未知")
            difficulty = proj.get("deploy_difficulty", 3)
            stars_emoji = "⭐" * difficulty
            student_value = proj.get("student_value", "")

            lines = [
                f"{idx}️⃣ {name} ⭐ {stars_str} {growth_str}",
                f"{one_liner}",
                f"技术栈：{tech_stack}",
                f"部署难度：{stars_emoji}",
                f"对你的价值：{student_value}",
                ""
            ]
            for line in lines:
                if line.strip() or line == "":
                    content.append([{"tag": "text", "text": line}])
    else:
        content.append([{"tag": "text", "text": "━━━ 🔥 近期飙升 ━━━ 无"}])

    # 结尾补充交互提示
    content.append([{"tag": "text", "text": "━━━"}])
    content.append([{"tag": "text", "text": "粘贴代码，保存。✅ 验收标准：回复「跑 编号」启动自动部署 🚀"}])

    # 飞书 post 消息结构
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"AI项目推荐 {date_str}",
                    "content": content
                }
            }
        }
    }


def send_feishu_message(webhook_url: str, message: Dict) -> bool:
    """发送飞书消息，返回是否成功"""
    try:
        resp = requests.post(webhook_url, json=message, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0:
            logger.info("飞书消息发送成功")
            return True
        else:
            logger.error(f"飞书返回错误: {result}")
            return False
    except Exception as e:
        logger.error(f"发送飞书消息失败: {e}")
        return False


# ==================== 主流程 ====================
def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="GitHub AI 项目每日雷达，推送到飞书")
    parser.add_argument("--history", type=str, default="recommended_history.json",
                        help="推荐历史文件路径，默认为当前目录下的 recommended_history.json")
    args = parser.parse_args()

    # 读取配置
    github_token = get_env_var("GITHUB_TOKEN")
    deepseek_key = get_env_var("DEEPSEEK_API_KEY")
    feishu_webhook = load_feishu_webhook()
    history_path = args.history

    # 1. 抓取候选
    ##logger.info("开始抓取 Trending 项目...")
    ##trending = fetch_trending_projects(github_token)
    logger.info("跳过 Trending 抓取（直接使用 API 搜索）...")
    trending = []  # 临时置空

    logger.info("开始搜索 GitHub API 项目...")
    api_search = search_github_api_projects(github_token)

    # 2. 合并、去重、补全详细信息及周增长
    logger.info("合并候选列表并获取详细信息...")
    merged = merge_and_enrich(github_token, trending, api_search)
    logger.info(f"共获得 {len(merged)} 个有效候选项目")

    # 3. 过滤已推荐历史
    history = read_history(history_path)
    candidates = filter_excluded_by_history(merged, history)
    if len(candidates) < 5:
        logger.error(f"候选项目不足 5 个（{len(candidates)}），无法进行推荐")
        sys.exit(1)

    # 4. DeepSeek 筛选
    logger.info("调用 DeepSeek 进行智能筛选...")
    selected = call_deepseek_selection(candidates, deepseek_key)
    logger.info(f"DeepSeek 选中 {len(selected)} 个项目: {[s['repo_full_name'] for s in selected]}")

    # 5. 构建飞书消息并推送
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    feishu_msg = build_feishu_post_message(selected, today_str)
    success = send_feishu_message(feishu_webhook, feishu_msg)
    if not success:
        logger.error("飞书推送失败，但历史仍会记录（避免重复推送时丢失）")

    # 6. 更新历史文件
    recommended_names = [p["repo_full_name"] for p in selected]
    write_history(history_path, recommended_names)
    logger.info("任务完成")


if __name__ == "__main__":
    main()
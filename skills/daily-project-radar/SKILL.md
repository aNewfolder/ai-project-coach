---
name: daily-project-radar
description: |
每日 AI 项目推荐雷达。每天早上 8:00 自动运行，
从 GitHub Trending 抓取 AI/ML 相关热门项目，
筛选出 5 个项目（2 个经典高星 + 3 个近期飙升），
生成中文简介并推送到飞书群。
触发条件：每日定时执行，或用户手动发送"推荐项目"、"今日推荐"。
version: 1.0.0
author: your-team-name
permissions: 网络访问、文件读写
---
# Daily Project Radar
## 核心能力
每天自动从 GitHub 发现对大学生有实用价值的 AI 项目。
## 执行流程
### 1. 抓取 GitHub Trending
访问 GitHub Trending 页面（https://github.com/trending?since=daily），
筛选语言为 Python，获取当日热门项目列表。
同时通过 GitHub API 搜索近 7 天内星标增长最快的 AI 项目：
- 搜索条件：topic:ai OR topic:machine-learning OR topic:llm，stars:>100，pushed:>{7
天前的日期}
- 按星标数排序
### 2. 获取项目详情
对每个候选项目，通过 GitHub API 获取：
- 星标数、fork 数、最近提交时间
- README 内容（前 3000 字）
- 主要编程语言
- 项目描述
### 3. AI 智能筛选
将候选项目信息发送给 DeepSeek，按以下标准筛选和评分：
**经典高星项目（选 2 个）标准：**
- 星标 > 10K
- 最近 30 天有活跃提交
- README 中有明确的部署/安装指引
- 对大学生有实用价值（能学到 AI 核心概念或实用技能）
- 不是纯 SDK/库（如 PyTorch 本身）
**近期飙升项目（选 3 个）标准：**
- 过去 7 天星标增长 > 500 或增长率 > 20%
- README 中有 Quick Start / Installation 章节
- 非纯论文复现类项目
- 对大学生有学习价值
**排除规则：**
- 已在 assets/recommended_history.json 中推荐过的项目
- README 中无部署指引的项目
- 纯 SDK/库/框架（推荐基于它们的应用，而非框架本身）
### 4. 生成推荐卡片
对选出的 5 个项目，生成中文推荐消息，格式包含：
- 项目名 + 星标数（飙升项目标注周增长量）
- 一句话功能描述
- 技术栈
- 部署难度（1-5 星）
- 对大学生的价值
### 5. 推送到飞书
通过飞书 Webhook 发送推荐消息到群组。
### 6. 更新推荐历史
将本次推荐的项目添加到 assets/recommended_history.json，避免未来重复推荐。
## 定时任务
每天北京时间 08:00 自动执行。
使用 Linux crontab 配置：0 8 * * *
---
name: auto-deploy-engine
description: |
  自动部署 GitHub AI 项目并生成零基础保姆级教程。
  用户提供一个 GitHub 项目 URL，本技能会：
  1. 分析项目 README，提取部署步骤
  2. SSH 连接到 AutoDL GPU 服务器
  3. 逐步执行部署命令，记录每一步的命令和输出
  4. 在关键步骤自动截取终端截图
  5. 如遇报错自动尝试修复（最多 3 次）
  6. 验证项目核心功能是否正常运行
  7. 生成一份面向零基础小白的 Markdown 教程（含截图）
  8. 通过飞书通知用户教程已生成
  触发条件：用户发送"跑"、"部署"、"跑一下"加上 GitHub URL，
  或发送项目编号（如"跑 1"引用每日推荐中的项目）。
version: 1.0.0
author: ai-project-coach-team
permissions: 网络访问、SSH、文件读写
---

# Auto Deploy Engine

## 核心能力

当用户指定一个 GitHub 项目 URL 时，自动在远程 GPU 服务器上完成部署，
并生成一篇面向零基础用户的保姆级部署教程。

## 执行流程

### 第一阶段：分析项目

1. 使用 GitHub API 获取项目的 README.md 内容
2. 调用大模型分析 README，提取部署步骤
3. 生成部署计划

### 第二阶段：执行部署

1. SSH 连接到 AutoDL 服务器（使用 ~/.ssh/config 中的 autodl 配置）
2. 进入工作目录 /root/projects/
3. 按照部署计划逐步执行命令
4. 每执行一条关键命令后记录输出并截图
5. 如果报错，调用大模型分析并自动修复（最多 3 次）

### 第三阶段：验证功能

根据项目类型执行验证命令，确认部署成功。

### 第四阶段：生成教程

整合所有步骤、截图、报错解决方案为一篇完整 Markdown 教程。

### 第五阶段：通知用户

通过飞书 Webhook 通知用户教程已生成。

## SSH 连接配置

使用 ~/.ssh/config 中的 Host autodl 配置进行连接。

## 截图方法

使用 script + ansi2html + wkhtmltoimage 工具链将终端输出渲染为 PNG 截图。

## 文件输出位置

- 截图存放：/root/screenshots/{项目名}/
- 教程存放：~/ai-project-coach/tutorials/{项目名}/tutorial.md
- 教程截图：~/ai-project-coach/tutorials/{项目名}/screenshots/

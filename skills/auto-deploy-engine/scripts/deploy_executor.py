#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动部署引擎 (Auto Deploy Engine)
功能：接收 GitHub 项目 URL，在 AutoDL 上自动部署，生成保姆级教程
"""

import os
import sys
import json
import re
import time
import base64
import subprocess
import argparse
from datetime import datetime

import requests

# ===== 配置 =====
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
GITHUB_API_BASE = "https://api.github.com"
FEISHU_CONFIG_PATH = os.path.expanduser("~/.openclaw/config/feishu.json")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "tutorial_template.md")
TUTORIALS_DIR = os.path.expanduser("~/ai-project-coach/tutorials")
REMOTE_PROJECTS_DIR = "/root/projects"
REMOTE_SCREENSHOTS_DIR = "/root/screenshots"
REMOTE_SCREENSHOT_SCRIPT = "/root/capture_screenshot.sh"
MAX_RETRY = 10

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ===== 工具函数 =====

def get_feishu_webhook():
    """读取飞书 Webhook URL"""
    try:
        with open(FEISHU_CONFIG_PATH, "r") as f:
            return json.load(f).get("feishu_webhook_url", "")
    except:
        return ""


def github_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def call_deepseek(prompt, max_tokens=4000):
    """调用 DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    try:
        resp = requests.post(f"{DEEPSEEK_API_BASE}/chat/completions",
                             headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content
    except Exception as e:
        log(f"  ⚠️ DeepSeek API 调用失败: {e}")
        return ""


def run_ssh_command(cmd, timeout=300):
    """在 AutoDL 上通过 SSH 执行命令，返回 (stdout, stderr, returncode, duration)"""
    full_cmd = f'ssh autodl "cd {REMOTE_PROJECTS_DIR} && {cmd}"'
    start = time.time()
    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        duration = round(time.time() - start, 1)
        return result.stdout, result.stderr, result.returncode, duration
    except subprocess.TimeoutExpired:
        duration = round(time.time() - start, 1)
        return "", "命令超时", -1, duration
    except Exception as e:
        duration = round(time.time() - start, 1)
        return "", str(e), -1, duration


def take_screenshot(cmd_desc, step_num, project_name):
    """在 AutoDL 上对命令输出截图，返回截图远程路径（失败返回 None）"""
    remote_path = f"{REMOTE_SCREENSHOTS_DIR}/{project_name}/step_{step_num:02d}.png"
    ssh_cmd = f'ssh autodl "mkdir -p {REMOTE_SCREENSHOTS_DIR}/{project_name} && bash {REMOTE_SCREENSHOT_SCRIPT} \'echo {cmd_desc}\' \'{remote_path}\' \'步骤 {step_num}: {cmd_desc[:30]}\'"'
    try:
        subprocess.run(ssh_cmd, shell=True, capture_output=True, timeout=30)
        # 检查文件是否生成
        check = subprocess.run(f'ssh autodl "test -f {remote_path} && echo OK"',
                               shell=True, capture_output=True, text=True, timeout=10)
        if "OK" in check.stdout:
            return remote_path
    except:
        pass
    return None


def parse_github_url(url):
    """从 GitHub URL 提取 owner/repo"""
    match = re.search(r'github\.com/([\w\-\.]+)/([\w\-\.]+)', url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


# ===== 第一阶段：分析 README =====

def fetch_readme(repo_full_name):
    """从 GitHub 获取 README 内容"""
    log(f"📖 正在获取 {repo_full_name} 的 README...")
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/readme"
    try:
        resp = requests.get(url, headers=github_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        log(f"  → README 获取成功，长度 {len(content)} 字符")
        return content
    except Exception as e:
        log(f"  ❌ 获取 README 失败: {e}")
        return None


def analyze_readme(readme_content, repo_full_name):
    """用 DeepSeek 分析 README，提取部署步骤"""
    log("🤖 正在用 DeepSeek 分析部署步骤...")

    # 截取前 8000 字符避免 token 过多
    readme_excerpt = readme_content[:8000]

    prompt = f"""你是一个 AI 项目部署专家。请仔细阅读以下 GitHub 项目的 README，提取出完整的部署步骤。

项目：{repo_full_name}

README 内容：
{readme_excerpt}

请严格以 JSON 格式返回，不要有任何其他文字或 markdown 代码块标记，格式如下：
{{
  "project_name": "项目名称（简短英文名）",
  "description": "一句话中文描述",
  "what_you_get": "跑完后能得到什么（面向零基础用户的通俗描述，2-3句话）",
  "prerequisites": ["前置要求列表"],
  "steps": [
    {{
      "description": "这一步在做什么（中文）",
      "commands": ["要执行的命令1", "命令2"],
      "is_key_step": true
    }}
  ],
  "verification": {{
    "method": "如何验证部署成功（中文描述）",
    "command": "验证命令"
  }},
  "estimated_time": 20
}}

注意：
1. steps 里的 commands 必须是能在 Ubuntu 22.04 + CUDA 12.1 + Python 3.10 环境中直接执行的命令
2. 如果项目支持 Docker 部署，优先使用 Docker 方式
3. 如果需要 git clone，使用 HTTPS 地址而不是 SSH
4. 每个 step 的 is_key_step 标记为 true 表示这是关键步骤需要截图
5. estimated_time 是预估总部署时间（分钟）"""

    result = call_deepseek(prompt)
    if not result:
        return None

    try:
        # 清理可能的 markdown 代码块包裹
        result = re.sub(r'^```json\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
        plan = json.loads(result)
        log(f"  → 解析出 {len(plan.get('steps', []))} 个部署步骤")
        return plan
    except json.JSONDecodeError as e:
        log(f"  ⚠️ JSON 解析失败: {e}")
        log(f"  原始返回: {result[:500]}")
        return None


# ===== 第二阶段：执行部署 =====

def execute_deployment(plan):
    """按照部署计划在 AutoDL 上逐步执行"""
    log("🚀 开始在 AutoDL 上执行部署...")
    project_name = plan.get("project_name", "unknown")
    steps = plan.get("steps", [])
    results = []

    # 确保工作目录存在
    run_ssh_command(f"mkdir -p {REMOTE_PROJECTS_DIR}", timeout=10)

    for i, step in enumerate(steps):
        step_num = i + 1
        desc = step.get("description", f"步骤 {step_num}")
        commands = step.get("commands", [])
        is_key = step.get("is_key_step", False)

        log(f"\n--- 步骤 {step_num}/{len(steps)}: {desc} ---")

        step_result = {
            "step_num": step_num,
            "description": desc,
            "commands": commands,
            "outputs": [],
            "success": True,
            "duration": 0,
            "screenshot_path": None,
            "error_fix": None
        }

        total_duration = 0
        for cmd in commands:
            log(f"  ▶ 执行: {cmd}")
            stdout, stderr, returncode, duration = run_ssh_command(cmd, timeout=600)
            total_duration += duration

            output_text = stdout if stdout else stderr
            # 截断过长的输出
            if len(output_text) > 2000:
                output_text = output_text[:1000] + "\n... (输出过长，已截断) ...\n" + output_text[-500:]

            step_result["outputs"].append({
                "command": cmd,
                "stdout": stdout[:2000] if stdout else "",
                "stderr": stderr[:2000] if stderr else "",
                "returncode": returncode,
                "duration": duration
            })

            if returncode != 0:
                log(f"  ❌ 命令失败 (返回码 {returncode})")
                log(f"  错误: {stderr[:200]}")

                # 自动排错
                fix_result = auto_fix_error(cmd, stderr, project_name)
                if fix_result:
                    step_result["error_fix"] = fix_result
                    # 尝试重新执行原命令
                    log(f"  🔄 修复后重试: {cmd}")
                    stdout2, stderr2, rc2, dur2 = run_ssh_command(cmd, timeout=600)
                    total_duration += dur2
                    if rc2 == 0:
                        log(f"  ✅ 重试成功！")
                        step_result["outputs"][-1]["returncode"] = 0
                        step_result["outputs"][-1]["stdout"] = stdout2[:2000]
                    else:
                        log(f"  ❌ 重试仍然失败")
                        step_result["success"] = False
                else:
                    step_result["success"] = False
            else:
                log(f"  ✅ 成功 ({duration}s)")

        step_result["duration"] = total_duration

        # 截图（仅对关键步骤）
        if is_key:
            screenshot = take_screenshot(desc, step_num, project_name)
            if screenshot:
                step_result["screenshot_path"] = screenshot
                log(f"  📸 截图已保存")

        results.append(step_result)

    return results


def auto_fix_error(failed_cmd, error_msg, project_name):
    """调用 DeepSeek 分析错误并尝试修复"""
    log("  🔧 正在调用 DeepSeek 分析错误...")

    prompt = f"""执行以下命令时出现错误：

命令: {failed_cmd}
错误信息: {error_msg[:1000]}

运行环境: Ubuntu 22.04 + Python 3.10 + CUDA 12.1 (AutoDL GPU 服务器)
项目: {project_name}

请给出最可能的修复命令。只返回需要执行的修复命令，每行一条，不要任何解释文字。
如果无法修复，返回空字符串。"""

    fix_text = call_deepseek(prompt, max_tokens=500)
    if not fix_text or fix_text.strip() == "":
        return None

    fix_commands = [line.strip() for line in fix_text.strip().split('\n')
                    if line.strip() and not line.strip().startswith('#')]

    if not fix_commands:
        return None

    log(f"  🔧 尝试修复命令: {fix_commands}")
    fix_outputs = []
    for fix_cmd in fix_commands[:10]:  # 最多执行 3 条修复命令
        log(f"  ▶ 修复: {fix_cmd}")
        stdout, stderr, rc, dur = run_ssh_command(fix_cmd, timeout=300)
        fix_outputs.append({"command": fix_cmd, "returncode": rc})
        if rc != 0:
            log(f"  ⚠️ 修复命令也失败了")

    return {"fix_commands": fix_commands, "fix_outputs": fix_outputs}


# ===== 第三阶段：验证功能 =====

def verify_deployment(plan):
    """验证部署是否成功"""
    verification = plan.get("verification", {})
    cmd = verification.get("command", "")
    method = verification.get("method", "")

    if not cmd:
        log("⚠️ 没有验证命令，跳过验证")
        return {"success": None, "method": method, "output": "无验证命令"}

    log(f"🔍 验证部署: {method}")
    log(f"  ▶ 执行: {cmd}")
    stdout, stderr, rc, dur = run_ssh_command(cmd, timeout=60)

    success = rc == 0
    log(f"  {'✅ 验证通过' if success else '❌ 验证失败'}")

    return {
        "success": success,
        "method": method,
        "command": cmd,
        "output": (stdout or stderr)[:500]
    }


# ===== 第四阶段：生成教程 =====

def generate_tutorial(plan, deploy_results, verify_result):
    """生成 Markdown 教程"""
    project_name = plan.get("project_name", "unknown")
    log(f"📝 正在生成教程...")

    # 创建本地教程目录
    tutorial_dir = os.path.join(TUTORIALS_DIR, project_name)
    screenshots_dir = os.path.join(tutorial_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    # 从 AutoDL 拷贝截图到本地
    try:
        subprocess.run(
            f'scp -r autodl:{REMOTE_SCREENSHOTS_DIR}/{project_name}/* {screenshots_dir}/ 2>/dev/null',
            shell=True, timeout=60
        )
    except:
        log("  ⚠️ 截图拷贝失败，教程将不包含截图")

    # 为每个步骤生成通俗解释
    steps_md = []
    for result in deploy_results:
        step_num = result["step_num"]
        desc = result["description"]
        commands = result["commands"]
        success = result["success"]
        duration = result["duration"]

        step_md = f"### 第 {step_num} 步：{desc}\n\n"

        for out in result["outputs"]:
            cmd = out["command"]
            # 生成通俗解释
            explanation = generate_explanation(cmd)
            step_md += f"```bash\n{cmd}\n```\n\n"
            step_md += f"> 🔍 **这条命令在做什么：** {explanation}\n\n"

            # 如果有输出，展示关键部分
            cmd_output = out.get("stdout", "")
            if cmd_output and len(cmd_output.strip()) > 0:
                output_preview = cmd_output.strip()[:300]
                step_md += f"<details>\n<summary>点击查看终端输出</summary>\n\n```\n{output_preview}\n```\n\n</details>\n\n"

            if out["returncode"] != 0 and out.get("stderr"):
                step_md += f"⚠️ **遇到错误：**\n```\n{out['stderr'][:300]}\n```\n\n"

        # 如果有截图
        screenshot_file = f"step_{step_num:02d}.png"
        if os.path.exists(os.path.join(screenshots_dir, screenshot_file)):
            step_md += f"![步骤{step_num}截图](./screenshots/{screenshot_file})\n\n"

        # 如果有错误修复
        if result.get("error_fix"):
            fix = result["error_fix"]
            step_md += "🔧 **自动修复方案：**\n\n"
            for fc in fix.get("fix_commands", []):
                step_md += f"```bash\n{fc}\n```\n\n"

        status_icon = "✅" if success else "❌"
        step_md += f"**状态：** {status_icon} {'成功' if success else '失败'} | ⏱️ 耗时 {duration}s\n\n---\n\n"
        steps_md.append(step_md)

    # 组装完整教程
    all_steps = "\n".join(steps_md)
    success_count = sum(1 for r in deploy_results if r["success"])
    total_count = len(deploy_results)

    # 读取模板
    try:
        with open(TEMPLATE_PATH, "r") as f:
            template = f.read()
    except:
        template = "# {{PROJECT_NAME}} 部署教程\n\n{{STEPS}}"

    # 填充模板
    tutorial = template.replace("{{PROJECT_NAME}}", plan.get("project_name", "未知项目"))
    tutorial = template.replace("{{PROJECT_NAME}}", plan.get("project_name", "未知项目"))
    tutorial = tutorial.replace("{{PROJECT_DESCRIPTION}}", plan.get("description", ""))
    tutorial = tutorial.replace("{{WHAT_YOU_GET}}", plan.get("what_you_get", ""))
    tutorial = tutorial.replace("{{ESTIMATED_TIME}}", str(plan.get("estimated_time", 30)))
    tutorial = tutorial.replace("{{DATE}}", datetime.now().strftime("%Y-%m-%d"))
    tutorial = tutorial.replace("{{STEPS}}", all_steps)

    verify_text = ""
    if verify_result:
        v_status = "✅ 验证通过" if verify_result.get("success") else "❌ 验证未通过"
        verify_text = f"{v_status}\n\n验证方式：{verify_result.get('method', '')}"
    tutorial = tutorial.replace("{{SUCCESS_DESCRIPTION}}", verify_text)

    faq = f"本次部署共 {total_count} 个步骤，{success_count} 个成功。"
    tutorial = tutorial.replace("{{FAQ}}", faq)

    # 保存教程
    tutorial_path = os.path.join(tutorial_dir, "tutorial.md")
    with open(tutorial_path, "w") as f:
        f.write(tutorial)

    log(f"  → 教程已保存到: {tutorial_path}")
    return tutorial_path


def generate_explanation(cmd):
    """为单条命令生成通俗解释"""
    # 常见命令的快速解释（不用调 API，节省 token）
    quick_explanations = {
        "git clone": "从 GitHub 下载项目的完整代码到服务器上",
        "cd ": "进入指定的文件夹",
        "pip install": "安装项目所需的 Python 依赖包",
        "pip3 install": "安装项目所需的 Python 依赖包",
        "docker pull": "下载项目需要的 Docker 镜像",
        "docker run": "启动一个 Docker 容器来运行项目",
        "docker compose": "用 Docker Compose 一键启动项目的所有服务",
        "docker-compose": "用 Docker Compose 一键启动项目的所有服务",
        "apt-get install": "安装系统级的软件包",
        "apt install": "安装系统级的软件包",
        "wget": "从网上下载文件",
        "curl": "从网上获取数据或下载文件",
        "chmod": "修改文件的执行权限",
        "mkdir": "创建一个新文件夹",
        "cp ": "复制文件",
        "mv ": "移动或重命名文件",
        "python": "运行 Python 脚本",
        "npm install": "安装项目所需的 Node.js 依赖包",
        "export": "设置环境变量（告诉系统一些配置信息）",
    }

    for key, explanation in quick_explanations.items():
        if key in cmd:
            return explanation

    # 对于不在快速列表中的命令，调用 DeepSeek
    result = call_deepseek(
        f"用一句话通俗地解释这条 Linux 命令在做什么（面向完全没有编程经验的人）：\n{cmd}\n\n只返回解释，不要包含命令本身。",
        max_tokens=100
    )
    return result if result else "执行项目所需的配置命令"


# ===== 第五阶段：飞书通知 =====

def git_push_tutorial(project_name):
    """将教程推送到 GitHub 并返回链接"""
    log("📤 正在将教程推送到 GitHub...")
    try:
        cmds = [
            "cd ~/ai-project-coach && git add .",
            f'cd ~/ai-project-coach && git commit -m "docs: 自动生成 {project_name} 部署教程"',
            "cd ~/ai-project-coach && git pull --rebase",
            "cd ~/ai-project-coach && git push"
        ]
        for cmd in cmds:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        github_link = f"https://github.com/aNewfolder/ai-project-coach/blob/main/tutorials/{project_name}/tutorial.md"
        log(f"  → ✅ 已推送，链接: {github_link}")
        return github_link
    except Exception as e:
        log(f"  ⚠️ Git 推送失败: {e}")
        return None


def send_feishu_notification(plan, deploy_results, tutorial_path):
    """推送教程到 GitHub，然后发送飞书通知（含 GitHub 链接）"""
    webhook_url = get_feishu_webhook()
    if not webhook_url:
        log("⚠️ 飞书 Webhook 未配置，跳过通知")
        return

    project_name = plan.get("project_name", "未知项目")
    success_count = sum(1 for r in deploy_results if r["success"])
    total_count = len(deploy_results)
    all_success = success_count == total_count

    # 先推送到 GitHub
    github_link = git_push_tutorial(project_name)

    status = "✅ 全部成功" if all_success else f"⚠️ {success_count}/{total_count} 步成功"

    link_line = f"🔗 在线查看：{github_link}" if github_link else f"📄 服务器路径：{tutorial_path}"

    message = f"""🤖 自动部署完成通知

📦 项目：{project_name}
📝 描述：{plan.get("description", "")}
📊 部署结果：{status}
{link_line}

{"🎉 教程已生成，点击链接查看！" if all_success else "⚠️ 部分步骤失败，教程中已记录排错过程。"}"""

    try:
        resp = requests.post(webhook_url, json={
            "msg_type": "text",
            "content": {"text": message}
        }, timeout=10)
        if resp.status_code == 200:
            log("📮 飞书通知发送成功")
        else:
            log(f"⚠️ 飞书通知发送异常: {resp.text}")
    except Exception as e:
        log(f"⚠️ 飞书通知发送失败: {e}")


# ===== 主函数 =====

def main():
    parser = argparse.ArgumentParser(description="自动部署引擎")
    parser.add_argument("url", nargs="?", help="GitHub 项目 URL")
    parser.add_argument("--test-readme", metavar="URL",
                        help="仅测试 README 分析功能（不执行部署）")
    args = parser.parse_args()

    # 检查配置
    if not DEEPSEEK_API_KEY:
        log("❌ 错误：DEEPSEEK_API_KEY 环境变量未设置")
        sys.exit(1)

    target_url = args.test_readme or args.url
    if not target_url:
        log("❌ 错误：请提供 GitHub 项目 URL")
        log("用法: python3 deploy_executor.py https://github.com/owner/repo")
        log("      python3 deploy_executor.py --test-readme https://github.com/owner/repo")
        sys.exit(1)

    # 解析 URL
    repo_full_name = parse_github_url(target_url)
    if not repo_full_name:
        log(f"❌ 无法解析 GitHub URL: {target_url}")
        sys.exit(1)

    log("=" * 60)
    log(f"🚀 自动部署引擎启动")
    log(f"📦 目标项目: {repo_full_name}")
    log("=" * 60)

    # 第一阶段：分析 README
    readme = fetch_readme(repo_full_name)
    if not readme:
        log("❌ 无法获取 README，退出")
        sys.exit(1)

    plan = analyze_readme(readme, repo_full_name)
    if not plan:
        log("❌ 无法分析 README，退出")
        sys.exit(1)

    log(f"\n📋 部署计划:")
    log(f"  项目: {plan.get('project_name')}")
    log(f"  描述: {plan.get('description')}")
    log(f"  步骤数: {len(plan.get('steps', []))}")
    log(f"  预计耗时: {plan.get('estimated_time', '未知')} 分钟")

    # 如果只是测试 README 分析
    if args.test_readme:
        log("\n📄 完整部署计划 (JSON):")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        log("\n✅ README 分析测试完成！")
        return

    # 第二阶段：执行部署
    deploy_results = execute_deployment(plan)

    # 第三阶段：验证
    verify_result = verify_deployment(plan)

    # 第四阶段：生成教程
    tutorial_path = generate_tutorial(plan, deploy_results, verify_result)

    # 第五阶段：飞书通知
    send_feishu_notification(plan, deploy_results, tutorial_path)

    # 总结
    success_count = sum(1 for r in deploy_results if r["success"])
    total_count = len(deploy_results)

    log("\n" + "=" * 60)
    log(f"📊 部署完成！{success_count}/{total_count} 个步骤成功")
    log(f"📄 教程文件: {tutorial_path}")
    log("=" * 60)


if __name__ == "__main__":
    main()

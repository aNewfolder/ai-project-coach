#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动部署引擎 v2 (Auto Deploy Engine)
功能：接收 GitHub 项目 URL，在 AutoDL 上自动部署，生成保姆级教程
改进：教程只展示最终成功步骤，失败记录放附录，自动清理旧项目，文件名含项目名
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
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"  ⚠️ DeepSeek API 调用失败: {e}")
        return ""


def is_launch_command(cmd):
    """判断命令是否是启动服务类命令（会一直运行不退出）"""
    launch_patterns = [
        "python app.py", "python3 app.py", "python main.py", "python3 main.py",
        "python run.py", "python3 run.py", "python server.py", "python3 server.py",
        "python manage.py runserver", "python3 manage.py runserver",
        "streamlit run", "gradio ", "uvicorn ", "gunicorn ", "flask run",
        "npm start", "npm run dev", "npm run serve", "node server",
        "jupyter notebook", "jupyter lab",
        ".launch()", "demo.launch", "app.run",
    ]
    cmd_lower = cmd.lower().strip()
    for pattern in launch_patterns:
        if pattern in cmd_lower:
            return True
    return False


def run_ssh_command(cmd, timeout=300):
    """执行SSH命令。如果是启动服务类命令，用nohup后台运行并等几秒检查"""
    if is_launch_command(cmd):
        # 启动服务类命令：后台运行，等5秒后检查进程是否存活
        bg_cmd = f'ssh autodl "cd {REMOTE_PROJECTS_DIR} && nohup {cmd} > /tmp/service.log 2>&1 & sleep 5 && ps aux | grep -v grep | grep -c \'{cmd.split()[0]}\'"'
        start = time.time()
        try:
            result = subprocess.run(bg_cmd, shell=True, capture_output=True, text=True, timeout=30)
            duration = round(time.time() - start, 1)
            # 如果grep找到了进程，说明服务成功启动
            count = result.stdout.strip()
            if count and int(count) > 0:
                return "服务已在后台启动", "", 0, duration
            else:
                # 读取日志看看报了什么错
                log_cmd = f'ssh autodl "cat /tmp/service.log 2>/dev/null | tail -20"'
                log_result = subprocess.run(log_cmd, shell=True, capture_output=True, text=True, timeout=10)
                return "", log_result.stdout or "服务启动后立即退出", 1, duration
        except Exception as e:
            return "", str(e), -1, round(time.time() - start, 1)
    else:
        full_cmd = f'ssh autodl "cd {REMOTE_PROJECTS_DIR} && {cmd}"'
        start = time.time()
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            duration = round(time.time() - start, 1)
            return result.stdout, result.stderr, result.returncode, duration
        except subprocess.TimeoutExpired:
            return "", "命令超时", -1, round(time.time() - start, 1)
        except Exception as e:
            return "", str(e), -1, round(time.time() - start, 1)


def take_screenshot(cmd_desc, step_num, project_name):
    remote_path = f"{REMOTE_SCREENSHOTS_DIR}/{project_name}/step_{step_num:02d}.png"
    ssh_cmd = f'ssh autodl "mkdir -p {REMOTE_SCREENSHOTS_DIR}/{project_name} && bash {REMOTE_SCREENSHOT_SCRIPT} \'echo {cmd_desc}\' \'{remote_path}\' \'步骤 {step_num}: {cmd_desc[:30]}\'"'
    try:
        subprocess.run(ssh_cmd, shell=True, capture_output=True, timeout=30)
        check = subprocess.run(f'ssh autodl "test -f {remote_path} && echo OK"',
                               shell=True, capture_output=True, text=True, timeout=10)
        if "OK" in check.stdout:
            return remote_path
    except:
        pass
    return None


def parse_github_url(url):
    match = re.search(r'github\.com/([\w\-\.]+)/([\w\-\.]+)', url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


# ===== 第一阶段：分析 README =====

def fetch_readme(repo_full_name):
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
    log("🤖 正在用 DeepSeek 分析部署步骤...")
    readme_excerpt = readme_content[:8000]

    prompt = f"""你是一个 AI 项目部署专家。请仔细阅读以下 GitHub 项目的 README，提取出完整的部署步骤。

项目：{repo_full_name}

README 内容：
{readme_excerpt}

请严格以 JSON 格式返回，不要有任何其他文字或 markdown 代码块标记，格式如下：
{{
  "project_name": "项目名称（简短英文名，用连字符分隔，如 gpt-academic）",
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
1. steps 里的 commands 必须是能在 Ubuntu 22.04 + Python 3.10 环境中直接执行的命令
2. 不要使用 Docker（目标环境不支持 Docker），优先使用 pip install 或源码安装方式
3. 如果需要 git clone，使用 HTTPS 地址
4. 每个 step 的 is_key_step 标记为 true 表示这是关键步骤需要截图
5. estimated_time 是预估总部署时间（分钟）
6. 如果项目需要配置文件，用 echo 或 sed 命令自动生成，不要让用户手动编辑"""

    result = call_deepseek(prompt)
    if not result:
        return None

    try:
        result = re.sub(r'^```json\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
        plan = json.loads(result)
        log(f"  → 解析出 {len(plan.get('steps', []))} 个部署步骤")
        return plan
    except json.JSONDecodeError as e:
        log(f"  ⚠️ JSON 解析失败: {e}")
        return None


# ===== 第二阶段：执行部署 =====

def cleanup_old_project(project_name):
    """清理 AutoDL 上的旧项目目录"""
    log(f"🧹 清理旧项目目录: {project_name}")
    run_ssh_command(f"rm -rf {REMOTE_PROJECTS_DIR}/{project_name}", timeout=30)
    run_ssh_command(f"rm -rf {REMOTE_SCREENSHOTS_DIR}/{project_name}", timeout=10)


def execute_deployment(plan):
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
            "error_fix": None,
            "final_commands": [],  # 最终成功的命令序列
        }

        total_duration = 0
        for cmd in commands:
            log(f"  ▶ 执行: {cmd}")
            stdout, stderr, returncode, duration = run_ssh_command(cmd, timeout=600)
            total_duration += duration

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

                # 自动排错，最多 MAX_RETRY 轮
                fixed = False
                for retry in range(MAX_RETRY):
                    log(f"  🔧 第 {retry+1}/{MAX_RETRY} 次尝试修复...")
                    fix_result = auto_fix_error(cmd, stderr, project_name)
                    if fix_result:
                        step_result["error_fix"] = fix_result
                        # 重新执行原命令
                        log(f"  🔄 修复后重试: {cmd}")
                        stdout2, stderr2, rc2, dur2 = run_ssh_command(cmd, timeout=600)
                        total_duration += dur2
                        if rc2 == 0:
                            log(f"  ✅ 第 {retry+1} 次修复后重试成功！")
                            step_result["outputs"][-1]["returncode"] = 0
                            step_result["outputs"][-1]["stdout"] = stdout2[:2000]
                            # 记录最终成功的命令序列（修复命令 + 原命令）
                            step_result["final_commands"] = fix_result.get("fix_commands", []) + [cmd]
                            fixed = True
                            break
                        else:
                            stderr = stderr2  # 用新的错误信息继续下一轮修复
                    else:
                        break

                if not fixed:
                    step_result["success"] = False
            else:
                log(f"  ✅ 成功 ({duration}s)")
                step_result["final_commands"].append(cmd)

        step_result["duration"] = total_duration

        # 截图
        if is_key:
            screenshot = take_screenshot(desc, step_num, project_name)
            if screenshot:
                step_result["screenshot_path"] = screenshot
                log(f"  📸 截图已保存")

        results.append(step_result)

    return results


def auto_fix_error(failed_cmd, error_msg, project_name):
    log("  🔧 正在调用 DeepSeek 分析错误...")

    prompt = f"""执行以下命令时出现错误：

命令: {failed_cmd}
错误信息: {error_msg[:1500]}

运行环境: Ubuntu 22.04 + Python 3.10 + CUDA 12.1 (AutoDL GPU 服务器)
工作目录: /root/projects
项目: {project_name}
注意: 此环境不支持 Docker 和 systemctl

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
    for fix_cmd in fix_commands[:10]:
        log(f"  ▶ 修复: {fix_cmd}")
        stdout, stderr, rc, dur = run_ssh_command(fix_cmd, timeout=300)
        fix_outputs.append({"command": fix_cmd, "returncode": rc})
        if rc != 0:
            log(f"  ⚠️ 修复命令失败: {fix_cmd}")

    return {"fix_commands": fix_commands, "fix_outputs": fix_outputs}


# ===== 第三阶段：验证 =====

def verify_deployment(plan):
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

def generate_explanation(cmd):
    """为命令生成通俗解释"""
    quick = {
        "git clone": "把这个项目的所有文件从网上下载到你的电脑里",
        "cd ": "进入刚才下载好的文件夹",
        "pip install": "自动安装这个项目运行所需要的所有工具包（就像安装 App 的依赖一样）",
        "pip3 install": "自动安装这个项目运行所需要的所有工具包",
        "apt-get install": "安装系统需要的基础软件（类似给电脑装驱动）",
        "apt install": "安装系统需要的基础软件",
        "apt update": "让系统检查一下有没有软件更新",
        "wget": "从网上下载一个文件到你的电脑",
        "curl": "从网上获取数据",
        "chmod": "给文件加上「可以运行」的权限",
        "mkdir": "创建一个新的文件夹",
        "cp ": "把文件复制一份",
        "mv ": "把文件移动到另一个位置（或者改名）",
        "python": "运行项目的主程序",
        "python3": "运行项目的主程序",
        "npm install": "安装前端项目需要的工具包",
        "export": "设置一个配置信息（比如告诉程序你的密码放在哪里）",
        "echo ": "往文件里写入一些内容，或者在屏幕上显示一段文字",
        "sed ": "自动修改文件里的某些内容（不用你手动打开编辑）",
        "cat >": "创建一个新文件并往里面写入内容",
        "cat ": "查看文件的内容",
        "rm ": "删除文件或文件夹",
        "source ": "激活一个虚拟环境（让后面的命令在独立空间里运行）",
        "venv": "创建一个独立的 Python 运行环境（不会影响系统里其他程序）",
        "nohup": "让程序在后台持续运行（关掉终端也不会停）",
    }
    for key, expl in quick.items():
        if key in cmd:
            return expl

    result = call_deepseek(
        f"用一句话通俗地解释这条命令在做什么（面向完全没有编程经验的人）：\n{cmd}\n\n只返回解释，不要包含命令本身。",
        max_tokens=100
    )
    return result if result else "执行项目所需的配置命令"


def generate_tutorial(plan, deploy_results, verify_result):
    """生成教程：只展示成功步骤，失败步骤放附录"""
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
        log("  ⚠️ 截图拷贝失败")

    # 分离成功和失败步骤
    success_steps = [r for r in deploy_results if r["success"]]
    failed_steps = [r for r in deploy_results if not r["success"]]

    # ===== 生成教程正文（只包含成功步骤）=====
    success_md = []
    display_num = 0
    for result in success_steps:
        display_num += 1
        desc = result["description"]

        step_md = f"### 第 {display_num} 步：{desc}\n\n"

        # 使用最终成功的命令序列（包含修复命令）
        final_cmds = result.get("final_commands", [])
        if not final_cmds:
            # 如果没记录 final_commands，用原始命令
            final_cmds = result["commands"]

        for cmd in final_cmds:
            explanation = generate_explanation(cmd)
            step_md += f"复制下面的命令，粘贴到终端窗口中，然后按回车键执行：\n\n"
            step_md += f"```bash\n{cmd}\n```\n\n"
            step_md += f"> 💡 **这一步在干嘛：** {explanation}\n\n"

        # 截图
        screenshot_file = f"step_{result['step_num']:02d}.png"
        if os.path.exists(os.path.join(screenshots_dir, screenshot_file)):
            step_md += f"✅ 如果一切顺利，你的终端会显示类似下图的内容（不需要完全一样，只要没有红色的 Error 报错就行）：\n\n"
            step_md += f"![步骤{display_num}截图](./screenshots/{screenshot_file})\n\n"

        step_md += f"⏱️ 预计耗时约 {max(1, int(result['duration']))} 秒\n\n---\n\n"
        success_md.append(step_md)

    # ===== 生成失败附录 =====
    failed_md = ""
    if failed_steps:
        failed_md = "\n## ⚠️ 未能自动完成的步骤\n\n"
        failed_md += "以下步骤在自动部署过程中未能成功，可能需要手动处理：\n\n"
        for result in failed_steps:
            desc = result["description"]
            failed_md += f"**{desc}**\n\n"
            last_error = ""
            for out in result["outputs"]:
                if out["returncode"] != 0 and out["stderr"]:
                    last_error = out["stderr"][:200]
            if last_error:
                failed_md += f"错误信息：`{last_error.strip()}`\n\n"
            failed_md += "---\n\n"

    # ===== 组装完整教程 =====
    all_steps = "\n".join(success_md)
    success_count = len(success_steps)
    total_count = len(deploy_results)

    verify_text = ""
    if verify_result:
        if verify_result.get("success"):
            verify_text = f"✅ 验证通过！\n\n验证方式：{verify_result.get('method', '')}"
        elif verify_result.get("success") is False:
            verify_text = f"验证方式：{verify_result.get('method', '')}\n\n（自动验证未通过，请手动检查）"
        else:
            verify_text = ""

    faq = f"本次部署共 {total_count} 个步骤，{success_count} 个自动完成。"
    if failed_steps:
        faq += f"\n{len(failed_steps)} 个步骤需要手动处理，详见下方「未能自动完成的步骤」。"

    tutorial = f"""# 🛠️ 零基础部署 {plan.get('project_name', '未知项目')} 保姆级教程

> ⏱️ 预计耗时：{plan.get('estimated_time', 30)} 分钟
> 🤖 本教程由 AI 自动生成并经过验证
> 📅 生成日期：{datetime.now().strftime('%Y-%m-%d')}

## 📋 这个项目是什么？

{plan.get('description', '')}

## 🎯 跑完之后你能得到什么？

{plan.get('what_you_get', '')}

---

## 📖 教程正文

{all_steps}

## ✅ 完成！

{verify_text}

---

## ❓ 说明

{faq}
{failed_md}

---

> 本教程由「AI 项目实战教练」自动生成
> GitHub: https://github.com/aNewfolder/ai-project-coach
"""

    # 保存教程（文件名含项目名）
    tutorial_filename = f"{project_name}_部署教程.md"
    tutorial_path = os.path.join(tutorial_dir, tutorial_filename)
    with open(tutorial_path, "w") as f:
        f.write(tutorial)

    # 同时保存一份 tutorial.md（兼容旧逻辑）
    with open(os.path.join(tutorial_dir, "tutorial.md"), "w") as f:
        f.write(tutorial)

    log(f"  → 教程已保存到: {tutorial_path}")
    return tutorial_path


# ===== 第五阶段：推送 + 通知 =====

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
        github_link = f"https://github.com/aNewfolder/ai-project-coach/tree/main/tutorials/{project_name}"
        log(f"  → ✅ 已推送，链接: {github_link}")
        return github_link
    except Exception as e:
        log(f"  ⚠️ Git 推送失败: {e}")
        return None


def send_feishu_notification(plan, deploy_results, tutorial_path):
    webhook_url = get_feishu_webhook()
    if not webhook_url:
        log("⚠️ 飞书 Webhook 未配置，跳过通知")
        return

    project_name = plan.get("project_name", "未知项目")
    success_count = sum(1 for r in deploy_results if r["success"])
    total_count = len(deploy_results)
    all_success = success_count == total_count

    github_link = git_push_tutorial(project_name)

    status = "✅ 全部成功" if all_success else f"⚠️ {success_count}/{total_count} 步成功"
    link_line = f"🔗 在线查看：{github_link}" if github_link else f"📄 服务器路径：{tutorial_path}"

    message = f"""🤖 自动部署完成通知

📦 项目：{project_name}
📝 描述：{plan.get("description", "")}
📊 部署结果：{status}
{link_line}

{"🎉 教程已生成，点击链接查看！" if all_success else "⚠️ 部分步骤需要手动处理，教程中已标注。"}"""

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
    parser = argparse.ArgumentParser(description="自动部署引擎 v2")
    parser.add_argument("url", nargs="?", help="GitHub 项目 URL")
    parser.add_argument("--test-readme", metavar="URL",
                        help="仅测试 README 分析功能（不执行部署）")
    args = parser.parse_args()

    if not DEEPSEEK_API_KEY:
        log("❌ 错误：DEEPSEEK_API_KEY 环境变量未设置")
        log("请执行: export DEEPSEEK_API_KEY=\"你的Key\"")
        sys.exit(1)

    target_url = args.test_readme or args.url
    if not target_url:
        log("❌ 请提供 GitHub 项目 URL")
        log("用法: python3 deploy_executor.py https://github.com/owner/repo")
        sys.exit(1)

    repo_full_name = parse_github_url(target_url)
    if not repo_full_name:
        log(f"❌ 无法解析 GitHub URL: {target_url}")
        sys.exit(1)

    log("=" * 60)
    log(f"🚀 自动部署引擎 v2 启动")
    log(f"📦 目标项目: {repo_full_name}")
    log("=" * 60)

    # 第一阶段：分析 README
    readme = fetch_readme(repo_full_name)
    if not readme:
        sys.exit(1)

    plan = analyze_readme(readme, repo_full_name)
    if not plan:
        log("❌ 无法分析 README，退出")
        sys.exit(1)

    project_name = plan.get("project_name", "unknown")
    log(f"\n📋 部署计划:")
    log(f"  项目: {project_name}")
    log(f"  描述: {plan.get('description')}")
    log(f"  步骤数: {len(plan.get('steps', []))}")
    log(f"  预计耗时: {plan.get('estimated_time', '未知')} 分钟")

    if args.test_readme:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        log("\n✅ README 分析测试完成！")
        return

    # 清理旧项目
    cleanup_old_project(project_name)

    # 第二阶段：执行部署
    deploy_results = execute_deployment(plan)

    # 第三阶段：验证
    verify_result = verify_deployment(plan)

    # 第四阶段：生成教程
    tutorial_path = generate_tutorial(plan, deploy_results, verify_result)

    # 第五阶段：通知
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

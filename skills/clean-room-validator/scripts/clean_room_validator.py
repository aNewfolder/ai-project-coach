#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
干净房间验证器 (Clean Room Validator)
功能:在 AutoDL 上创建干净环境,逐步执行教程命令,验证教程可行性
替代方案:使用 Python venv 替代 Docker(AutoDL 不支持 Docker daemon)
"""
import os
import sys
import re
import json
import time
import subprocess
import argparse
from datetime import datetime
import requests

# ===== 全局配置 =====
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
CLEAN_ROOM_DIR = "/root/clean_room_test"
CLEAN_ROOM_VENV = f"{CLEAN_ROOM_DIR}/venv"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def call_deepseek(prompt, max_tokens=2000):
    if not DEEPSEEK_API_KEY:
        log("⚠️ DEEPSEEK_API_KEY 未配置")
        return ""
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
        resp = requests.post(f"{DEEPSEEK_API_BASE}/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"⚠️ DeepSeek API 调用失败: {e}")
        return ""

def run_ssh(cmd, timeout=300):
    full_cmd = f'ssh -p 23127 root@connect.bjb1.seetacloud.com "{cmd}"'
    start = time.time()
    try:
        proc = subprocess.run(full_cmd, shell=True, text=True, capture_output=True, timeout=timeout)
        cost = round(time.time() - start, 1)
        return proc.stdout, proc.stderr, proc.returncode, cost
    except subprocess.TimeoutExpired:
        return "", "命令超时", -1, round(time.time() - start,1)
    except Exception as e:
        return "", str(e), -2, round(time.time() - start,1)

def parse_tutorial(filepath):
    log(f"📖 正在解析教程: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    commands = []
    current_title = ""
    lines = content.splitlines()
    in_code = False
    code_buf = []
    for line in lines:
        h_match = re.match(r'^##\s+(.*)', line)
        if h_match:
            current_title = h_match.group(1).strip()
        if re.match(r'^```(bash|shell)?\s*$', line.strip()):
            in_code = True
            code_buf = []
            continue
        if line.strip() == "```" and in_code:
            in_code = False
            for code_line in code_buf:
                cl = code_line.strip()
                if cl and not cl.startswith("#"):
                    commands.append({
                        "step": len(commands)+1,
                        "context": current_title,
                        "command": cl
                    })
            continue
        if in_code:
            code_buf.append(line)
    log(f" 提取了 {len(commands)} 条命令")
    for item in commands:
        log(f" [{item['step']}] {item['command'][:60]}")
    return commands

def setup_clean_env():
    log("🏠 正在初始化干净虚拟环境")
    run_ssh(f"rm -rf {CLEAN_ROOM_DIR}")
    out, err, rc, cost = run_ssh(f"mkdir -p {CLEAN_ROOM_DIR} && python3 -m venv {CLEAN_ROOM_VENV}")
    if rc != 0:
        log(f"venv 创建失败: {err}")
        return False
    log(" ✅ 虚拟环境创建成功")
    return True

def execute_all_commands(cmd_list):
    log(f"🔄 开始批量执行 {len(cmd_list)} 条命令")
    results = []
    for item in cmd_list:
        step = item["step"]
        ctx = item["context"]
        cmd_raw = item["command"]
        log(f"\n--- 步骤{step}: {ctx} ---")
        log(f" ▶ 执行: {cmd_raw}")
        activate_wrap = f"source {CLEAN_ROOM_VENV}/bin/activate && {cmd_raw}"
        stdout, stderr, retcode, dur = run_ssh(activate_wrap)
        ok = retcode == 0
        status = "✅成功" if ok else "❌失败"
        log(f" {status} | 耗时{dur}s")
        if not ok and stderr:
            log(f" 错误片段: {stderr[:150]}")
        results.append({
            "step": step,
            "context": ctx,
            "command": cmd_raw,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": retcode,
            "duration": dur,
            "success": ok
        })
    return results

def generate_report(results, tutorial_path):
    log("📊 生成验证报告")
    total = len(results)
    success_cnt = sum(1 for r in results if r["success"])
    fail_cnt = total - success_cnt
    if fail_cnt == 0:
        conclusion = "全部通过：教程步骤均可正常执行"
    elif fail_cnt / total <= 0.3:
        conclusion = f"部分异常：{fail_cnt}个步骤出错，需要修补"
    else:
        conclusion = f"验证不通过：{fail_cnt}/{total}步骤失败"

    md = f"""# 干净环境验证报告
验证时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标教程：{tutorial_path}

## 整体结论
**{conclusion}**

## 步骤执行明细
|步骤|命令预览|结果|耗时|备注|
|---|---|---|---|---|
"""
    for r in results:
        cmd_short = r["command"][:50] + ("..." if len(r["command"])>50 else "")
        tag = "✅" if r["success"] else "❌"
        note = ""
        if not r["success"]:
            note = "执行报错"
        md += f"|{r['step']}|`{cmd_short}`|{tag}|{r['duration']}s|{note}|\n"

    if fail_cnt > 0:
        md += "\n## 失败步骤详情\n"
        for r in results:
            if not r["success"]:
                md += f"""
### 步骤{r['step']}：{r['context']}
执行命令：
```bash
{r['command']}

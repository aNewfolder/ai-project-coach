import requests
import os
import traceback

def load_md(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print("读取md文件失败：", traceback.format_exc())
        return None

def call_deepseek(content):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误：未读取到DEEPSEEK_API_KEY环境变量")
        return None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"""你是服务器部署安全审计专家，分析下面这份Ubuntu部署教程：
1. 找出所有安全漏洞、风险操作、不规范命令
2. 给出每一处问题的修补方案
3. 输出清晰markdown报告
部署文档内容：
{content}
"""
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "timeout": 30
    }
    try:
        res = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("调用DeepSeek接口失败：", traceback.format_exc())
        return None

def main():
    import sys
    if len(sys.argv) < 2:
        print("用法：python3 clean_room_validator.py 教程md文件路径")
        return
    md_path = sys.argv[1]
    doc_text = load_md(md_path)
    if not doc_text:
        return
    print("✅ 文档读取完成，开始AI安全分析...")
    report = call_deepseek(doc_text)
    if report:
        print("\n==================== 安全分析报告 ====================\n")
        print(report)

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print("脚本全局异常：", traceback.format_exc())

#!/bin/bash
# 用法: ./capture_screenshot.sh "要执行的命令" "输出截图路径" "步骤描述"

COMMAND="$1"
OUTPUT_PATH="$2"
STEP_DESC="$3"

# 确保输出目录存在
mkdir -p "$(dirname "$OUTPUT_PATH")"

# 创建临时文件
TEMP_LOG=$(mktemp /tmp/step_output_XXXXXX.log)
TEMP_HTML=$(mktemp /tmp/step_output_XXXXXX.html)

# 执行命令并录制输出（保留颜色）
script -q -c "$COMMAND" "$TEMP_LOG" 2>&1

# 将终端输出转换为 HTML
cat "$TEMP_LOG" | python -c "
import sys
from ansi2html import Ansi2HTMLConverter
conv = Ansi2HTMLConverter(dark_bg=True, scheme='xterm')
html = conv.convert(sys.stdin.read())
print(html)
" > "$TEMP_HTML"

# 注入自定义样式（让截图更像真实终端）
python -c "
with open('$TEMP_HTML', 'r') as f:
    content = f.read()

title_bar = '''
<div style=\"background:#3c3c3c;padding:8px 16px;border-radius:8px 8px 0 0;
     display:flex;align-items:center;gap:8px;\">
  <div style=\"width:12px;height:12px;border-radius:50%;background:#ff5f57;\"></div>
  <div style=\"width:12px;height:12px;border-radius:50%;background:#febc2e;\"></div>
  <div style=\"width:12px;height:12px;border-radius:50%;background:#28c840;\"></div>
  <span style=\"color:#999;margin-left:12px;font-size:13px;\">$STEP_DESC</span>
</div>
'''

content = content.replace('<body', '<body style=\"margin:0;padding:0;\"')
content = content.replace('<pre', '<pre style=\"margin:0;padding:16px;border-radius:0 0 8px 8px;font-size:14px;line-height:1.5;\"')
content = content.replace('<body style=\"margin:0;padding:0;\">', '<body style=\"margin:0;padding:0;\">' + title_bar)

with open('$TEMP_HTML', 'w') as f:
    f.write(content)
"

# 将 HTML 渲染为 PNG 截图
xvfb-run --auto-servernum wkhtmltoimage \
  --width 900 \
  --quality 90 \
  "$TEMP_HTML" "$OUTPUT_PATH"

# 清理临时文件
rm -f "$TEMP_LOG" "$TEMP_HTML"

echo "截图已保存到: $OUTPUT_PATH"

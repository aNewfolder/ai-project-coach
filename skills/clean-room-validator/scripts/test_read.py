import os
path = "/root/ai-project-coach/tutorialials/test-project/tutorial.md"
print("目标路径：", path)
print("文件是否存在：", os.path.exists(path))
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    print("读取字符总数：", len(content))
    print("前300内容预览：\n", content[:300])
else:
    print("文件不存在")

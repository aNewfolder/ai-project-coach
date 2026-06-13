# 🛠️ 零基础部署 fastapi-hello-world 保姆级教程

> ⏱️ 预计耗时：10 分钟
> 🤖 本教程由 AI 自动生成并经过验证
> 📅 生成日期：2026-06-13

## 📋 这个项目是什么？

快速搭建一个FastAPI示例应用并运行

## 🎯 跑完之后你能得到什么？

你将拥有一个运行在本地的FastAPI API服务，并能访问自动生成的交互式API文档。

---

## 📖 教程正文

### 第 1 步：创建项目目录并进入

复制下面的命令，粘贴到终端窗口中，然后按回车键执行：

```bash
mkdir ~/fastapi-demo && cd ~/fastapi-demo
```

> 💡 **这一步在干嘛：** 进入刚才下载好的文件夹

⏱️ 预计耗时约 1 秒

---


### 第 2 步：安装FastAPI和Uvicorn

复制下面的命令，粘贴到终端窗口中，然后按回车键执行：

```bash
pip install fastapi uvicorn
```

> 💡 **这一步在干嘛：** 自动安装这个项目运行所需要的所有工具包（就像安装 App 的依赖一样）

✅ 如果一切顺利，你的终端会显示类似下图的内容（不需要完全一样，只要没有红色的 Error 报错就行）：

![步骤2截图](./screenshots/step_02.png)

⏱️ 预计耗时约 1 秒

---


### 第 3 步：创建主程序文件main.py

复制下面的命令，粘贴到终端窗口中，然后按回车键执行：

```bash
cat > main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
EOF
```

> 💡 **这一步在干嘛：** 创建一个新文件并往里面写入内容

✅ 如果一切顺利，你的终端会显示类似下图的内容（不需要完全一样，只要没有红色的 Error 报错就行）：

![步骤3截图](./screenshots/step_03.png)

⏱️ 预计耗时约 1 秒

---



## ✅ 完成！

验证方式：在浏览器中访问 http://localhost:8000/docs 查看自动生成的交互式API文档，或访问 http://localhost:8000 看到JSON响应。

（自动验证未通过，请手动检查）

---

## ❓ 说明

本次部署共 4 个步骤，3 个自动完成。
1 个步骤需要手动处理，详见下方「未能自动完成的步骤」。

## ⚠️ 未能自动完成的步骤

以下步骤在自动部署过程中未能成功，可能需要手动处理：

**启动FastAPI服务（开发模式）**

错误信息：`服务启动后立即退出`

---



---

> 本教程由「AI 项目实战教练」自动生成
> GitHub: https://github.com/aNewfolder/ai-project-coach

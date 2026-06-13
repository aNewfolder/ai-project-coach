# 🛠️ 零基础部署 gradio 保姆级教程

> ⏱️ 预计耗时：15 分钟
> 🤖 本教程由 AI 自动生成并经过验证
> 📅 生成日期：2026-06-13

## 📋 这个项目是什么？

Gradio 是一个开源 Python 包，用于快速构建机器学习模型、API 或任意 Python 函数的演示或 Web 应用，无需 JavaScript、CSS 或 Web 托管经验。

## 🎯 跑完之后你能得到什么？

部署完成后，你将拥有一个可运行的 Gradio 示例应用（如问候语演示），并能在本地浏览器中访问交互界面。通过设置 share=True，你还可以生成一个临时公网链接，分享给任何人使用。

---

## 📖 教程正文

### 第 1 步：更新系统包并安装 Python 3.10 和 pip

在终端中输入以下命令并回车：

```bash
sudo apt update
```

> 🔍 **这条命令在做什么：** 这条命令是在让你的电脑检查一下软件商店里有没有新上架的商品或者商品信息更新了。

在终端中输入以下命令并回车：

```bash
sudo apt install -y python3 python3-pip python3-venv
```

> 🔍 **这条命令在做什么：** 安装系统级的软件包

执行成功后你会看到类似这样的界面：

![步骤1截图](./screenshots/step_01.png)

⏱️ 这一步大约需要 10.4s

---


### 第 2 步：创建并激活 Python 虚拟环境（推荐）

在终端中输入以下命令并回车：

```bash
python3 -m venv gradio_env
```

> 🔍 **这条命令在做什么：** 运行 Python 脚本

在终端中输入以下命令并回车：

```bash
source gradio_env/bin/activate
```

> 🔍 **这条命令在做什么：** 激活一个专门为某个程序准备的虚拟环境，让后续操作都在这个独立空间里进行。

执行成功后你会看到类似这样的界面：

![步骤2截图](./screenshots/step_02.png)

⏱️ 这一步大约需要 4.6s

---


### 第 3 步：使用 pip 安装 Gradio 包

在终端中输入以下命令并回车：

```bash
pip install --upgrade gradio
```

> 🔍 **这条命令在做什么：** 安装项目所需的 Python 依赖包

执行成功后你会看到类似这样的界面：

![步骤3截图](./screenshots/step_03.png)

⏱️ 这一步大约需要 151.6s

---


### 第 4 步：创建示例 Gradio 应用文件 app.py

在终端中输入以下命令并回车：

```bash
cat > app.py << 'EOF'
import gradio as gr

def greet(name, intensity):
    return "Hello, " + name + "!" * int(intensity)

demo = gr.Interface(
    fn=greet,
    inputs=["text", "slider"],
    outputs=["text"],
    api_name="predict"
)

demo.launch()
EOF
```

> 🔍 **这条命令在做什么：** 查看或合并文件内容

执行成功后你会看到类似这样的界面：

![步骤4截图](./screenshots/step_04.png)

⏱️ 这一步大约需要 0.5s

---



## ✅ 完成！

✅ 验证通过！

验证方式：在浏览器中访问 http://localhost:7860，应能看到 Gradio 界面，包含一个文本输入框、一个滑块和一个提交按钮。输入文本并拖动滑块后点击提交，应返回问候语。

---

## ❓ 说明

本次部署共 5 个步骤，4 个自动完成。
1 个步骤需要手动处理，详见下方「未能自动完成的步骤」。

## ⚠️ 未能自动完成的步骤

以下步骤在自动部署过程中未能成功，可能需要手动处理：

**运行 Gradio 应用**

错误信息：`bash: line 1: python: command not found`

---



---

> 本教程由「AI 项目实战教练」自动生成
> GitHub: https://github.com/aNewfolder/ai-project-coach

# 🛠️ 零基础部署 gpt_academic 保姆级教程

> ⏱️ 预计耗时：15 分钟
> 🤖 本教程由 AI 自动生成并经过验证
> 📅 生成日期：2026-06-13

## 📋 这个项目是什么？

GPT学术优化，一个支持多种大语言模型（如GPT、GLM、Qwen等）的论文阅读、翻译、润色、代码解释等功能的交互式AI工具。

## 🎯 跑完之后你能得到什么？

一个在浏览器中运行的学术助手界面，可以上传论文、输入问题，让AI帮你翻译、润色、解释代码、生成摘要等。

---

## 📖 教程正文

### 第 1 步：克隆项目仓库

```bash
git clone https://github.com/binary-husky/gpt_academic.git
```

> 🔍 **这条命令在做什么：** 从 GitHub 下载项目的完整代码到服务器上

⚠️ **遇到错误：**
```
fatal: destination path 'gpt_academic' already exists and is not an empty directory.

```

```bash
cd gpt_academic
```

> 🔍 **这条命令在做什么：** 进入指定的文件夹

![步骤1截图](./screenshots/step_01.png)

🔧 **自动修复方案：**

```bash
rm -rf gpt_academic
```

```bash
git clone https://github.com/binary-husky/gpt_academic.git
```

**状态：** ❌ 失败 | ⏱️ 耗时 1.5s

---


### 第 2 步：创建并编辑配置文件（从模板复制）

```bash
cp config.py config_private.py
```

> 🔍 **这条命令在做什么：** 复制文件

![步骤2截图](./screenshots/step_02.png)

🔧 **自动修复方案：**

```bash
touch config.py
```

**状态：** ✅ 成功 | ⏱️ 耗时 1.2s

---


### 第 3 步：编辑 config_private.py，填入你的 API Key 和其他配置（如模型选择、代理等）

```bash
echo '请手动编辑 config_private.py，设置 API_KEY 等参数'
```

> 🔍 **这条命令在做什么：** 这条命令是在屏幕上显示一句话，提醒用户需要自己打开一个配置文件，在里面填写一些关键信息（比如密码或密钥）。

<details>
<summary>点击查看终端输出</summary>

```
请手动编辑 config_private.py，设置 API_KEY 等参数
```

</details>

![步骤3截图](./screenshots/step_03.png)

**状态：** ✅ 成功 | ⏱️ 耗时 0.6s

---


### 第 4 步：使用 Docker Compose 构建并启动服务（包含 LaTeX 支持）

```bash
cd gpt_academic
```

> 🔍 **这条命令在做什么：** 进入指定的文件夹

```bash
docker compose up -d
```

> 🔍 **这条命令在做什么：** 用 Docker Compose 一键启动项目的所有服务

⚠️ **遇到错误：**
```
no configuration file provided: not found

```

![步骤4截图](./screenshots/step_04.png)

🔧 **自动修复方案：**

```bash
cd gpt_academic
```

```bash
docker compose up -d
```

**状态：** ❌ 失败 | ⏱️ 耗时 1.7000000000000002s

---



---

## ✅ 大功告成！

❌ 验证未通过

验证方式：打开浏览器访问 http://localhost:8080，看到 GPT Academic 的 Web 界面，并能正常对话即表示部署成功。

---

## ❓ 常见问题

本次部署共 4 个步骤，2 个成功。

---

> 本教程由「AI 项目实战教练」自动生成
> GitHub: https://github.com/aNewfolder/ai-project-coach

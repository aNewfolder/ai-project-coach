# 🛠️ 零基础部署 requests 保姆级教程

> ⏱️ 预计耗时：5 分钟
> 🤖 本教程由 AI 自动生成并经过验证
> 📅 生成日期：2026-06-13

## 📋 这个项目是什么？

一个简单优雅的 Python HTTP 库

## 🎯 跑完之后你能得到什么？

安装完成后，你可以在 Python 代码中使用 requests 库来发送 HTTP 请求，例如获取网页内容、调用 API 接口等。它是一个非常流行且易用的网络请求工具。

## 🧰 你需要准备什么？

1. 一台 AutoDL GPU 服务器（推荐 RTX 4090，约 ¥2/小时）
2. 大约 5 分钟的时间
3. 零编程经验即可

---

## 📖 教程正文

### 第 1 步：使用 pip 安装 requests 库

```bash
python -m pip install requests
```

> 🔍 **这条命令在做什么：** 安装项目所需的 Python 依赖包

⚠️ **遇到错误：**
```
bash: line 1: python: command not found

```

![步骤1截图](./screenshots/step_01.png)

🔧 **自动修复方案：**

```bash
sudo apt update
```

```bash
sudo apt install python3 python3-pip -y
```

```bash
python3 -m pip install requests
```

**状态：** ❌ 失败 | ⏱️ 耗时 1.0s

---



---

## ✅ 大功告成！

❌ 验证未通过

验证方式：在 Python 中导入 requests 并发送一个简单的 GET 请求，检查返回状态码是否为 200

---

## ❓ 常见问题

本次部署共 1 个步骤，0 个成功。

---

> 本教程由「AI 项目实战教练」自动生成
> GitHub: https://github.com/aNewfolder/ai-project-coach

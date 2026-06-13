# 🛠️ 零基础部署 open-webui 保姆级教程

> ⏱️ 预计耗时：20 分钟
> 🤖 本教程由 AI 自动生成并经过验证
> 📅 生成日期：2026-06-13

## 📋 这个项目是什么？

一个功能丰富、可扩展的自托管AI平台，支持离线运行，集成Ollama和OpenAI兼容API，内置RAG推理引擎。

## 🎯 跑完之后你能得到什么？

部署完成后，你将获得一个可通过浏览器访问的AI聊天界面，支持本地大模型（如通过Ollama）或远程API（如OpenAI）进行对话、文档问答（RAG）、图像生成等功能，所有数据都存储在你的服务器上。

## 🧰 你需要准备什么？

1. 一台 AutoDL GPU 服务器（推荐 RTX 4090，约 ¥2/小时）
2. 大约 20 分钟的时间
3. 零编程经验即可

---

## 📖 教程正文

### 第 1 步：更新系统并安装 Docker 和 Docker Compose

```bash
sudo apt update && sudo apt upgrade -y
```

> 🔍 **这条命令在做什么：** 这条命令是在让电脑自动检查并安装所有软件的最新版本，就像手机系统提示“有更新”时你点“全部更新”一样。

⚠️ **遇到错误：**
```
bash: line 1: sudo: command not found

```

```bash
sudo apt install -y ca-certificates curl gnupg lsb-release
```

> 🔍 **这条命令在做什么：** 安装系统级的软件包

<details>
<summary>点击查看终端输出</summary>

```
Reading package lists...
Building dependency tree...
Reading state information...
ca-certificates is already the newest version (20240203~22.04.1).
curl is already the newest version (7.81.0-1ubuntu1.24).
gnupg is already the newest version (2.2.27-3ubuntu2.5).
gnupg set to manually installed.
The f
```

</details>

```bash
sudo mkdir -p /etc/apt/keyrings
```

> 🔍 **这条命令在做什么：** 创建一个新文件夹

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

> 🔍 **这条命令在做什么：** 从网上获取数据或下载文件

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

> 🔍 **这条命令在做什么：** 这条命令是在告诉电脑：“请把Docker软件包的下载地址写进系统的一个配置文件里，这样以后就能从这个地址安装Docker了。”

```bash
sudo apt update
```

> 🔍 **这条命令在做什么：** 让电脑检查一下可以安装或更新的软件列表，就像去超市看看货架上有什么新商品或补货。

<details>
<summary>点击查看终端输出</summary>

```
Hit:1 https://repo.huaweicloud.com/ubuntu jammy InRelease
Hit:2 https://repo.huaweicloud.com/ubuntu jammy-backports InRelease
Hit:3 https://repo.huaweicloud.com/ubuntu jammy-proposed InRelease
Hit:4 https://repo.huaweicloud.com/ubuntu jammy-security InRelease
Hit:5 https://repo.huaweicloud.com/ubunt
```

</details>

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

> 🔍 **这条命令在做什么：** 用 Docker Compose 一键启动项目的所有服务

<details>
<summary>点击查看终端输出</summary>

```
Reading package lists...
Building dependency tree...
Reading state information...
The following packages were automatically installed and are no longer required:
  bridge-utils dns-root-data dnsmasq-base iproute2 libatm1 libbpf0 netcat
  netcat-openbsd ubuntu-fan
Use 'sudo apt autoremove' to remove 
```

</details>

```bash
sudo systemctl enable docker && sudo systemctl start docker
```

> 🔍 **这条命令在做什么：** 让电脑每次开机时自动准备好“Docker”这个工具，并且现在就立刻启动它。

⚠️ **遇到错误：**
```
Synchronizing state of docker.service with SysV service script with /lib/systemd/systemd-sysv-install.
Executing: /lib/systemd/systemd-sysv-install enable docker
perl: warning: Setting locale failed.
perl: warning: Please check that your locale settings:
	LANGUAGE = (unset),
	LC_ALL = (unset),
	LANG
```

```bash
sudo usermod -aG docker $USER
```

> 🔍 **这条命令在做什么：** 把你的当前用户账号添加到“docker”这个特殊用户组里，这样你就能直接使用Docker命令，而不用每次都输入管理员密码了。

![步骤1截图](./screenshots/step_01.png)

🔧 **自动修复方案：**

```bash
sudo apt-get install -y locales
```

```bash
sudo locale-gen en_US.UTF-8
```

```bash
sudo update-locale LANG=en_US.UTF-8
```

```bash
sudo service docker start
```

**状态：** ❌ 失败 | ⏱️ 耗时 46.199999999999996s

---


### 第 2 步：拉取 Open WebUI Docker 镜像（支持 CUDA 的版本）

```bash
docker pull ghcr.io/open-webui/open-webui:cuda
```

> 🔍 **这条命令在做什么：** 下载项目需要的 Docker 镜像

⚠️ **遇到错误：**
```
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory

```

![步骤2截图](./screenshots/step_02.png)

🔧 **自动修复方案：**

```bash
sudo systemctl start docker
```

```bash
sudo systemctl enable docker
```

```bash
sudo usermod -aG docker $USER
```

```bash
newgrp docker
```

**状态：** ❌ 失败 | ⏱️ 耗时 2.3s

---


### 第 3 步：创建持久化数据目录并启动 Open WebUI 容器

```bash
mkdir -p ~/open-webui-data
```

> 🔍 **这条命令在做什么：** 创建一个新文件夹

```bash
docker run -d --name open-webui --gpus all -p 3000:8080 -v ~/open-webui-data:/app/backend/data --restart unless-stopped ghcr.io/open-webui/open-webui:cuda
```

> 🔍 **这条命令在做什么：** 启动一个 Docker 容器来运行项目

⚠️ **遇到错误：**
```
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory

```

![步骤3截图](./screenshots/step_03.png)

🔧 **自动修复方案：**

```bash
sudo systemctl start docker
```

```bash
sudo systemctl enable docker
```

```bash
sudo usermod -aG docker $USER
```

```bash
newgrp docker
```

**状态：** ❌ 失败 | ⏱️ 耗时 2.0s

---


### 第 4 步：（可选）同时部署 Ollama 容器以支持本地模型

```bash
docker run -d --name ollama --gpus all -p 11434:11434 -v ~/ollama-data:/root/.ollama --restart unless-stopped ollama/ollama:latest
```

> 🔍 **这条命令在做什么：** 启动一个 Docker 容器来运行项目

⚠️ **遇到错误：**
```
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory

```

🔧 **自动修复方案：**

```bash
sudo systemctl start docker
```

```bash
sudo systemctl enable docker
```

**状态：** ❌ 失败 | ⏱️ 耗时 1.0s

---


### 第 5 步：验证容器是否正常运行

```bash
docker ps | grep open-webui
```

> 🔍 **这条命令在做什么：** 这条命令是在电脑里运行的“容器”列表中，找出名字里包含“open-webui”的那个程序。

⚠️ **遇到错误：**
```
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory

```

```bash
docker logs open-webui --tail 20
```

> 🔍 **这条命令在做什么：** 显示一个叫“open-webui”的程序最近输出的20行运行记录。

⚠️ **遇到错误：**
```
failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory

```

![步骤5截图](./screenshots/step_05.png)

🔧 **自动修复方案：**

```bash
sudo systemctl start docker
```

```bash
sudo systemctl enable docker
```

```bash
sudo usermod -aG docker $USER
```

```bash
newgrp docker
```

**状态：** ❌ 失败 | ⏱️ 耗时 2.2s

---



---

## ✅ 大功告成！

❌ 验证未通过

验证方式：在浏览器中访问 http://<服务器IP>:3000，应能看到 Open WebUI 的登录/注册页面。首次访问会提示创建管理员账户。

---

## ❓ 常见问题

本次部署共 5 个步骤，0 个成功。

---

> 本教程由「AI 项目实战教练」自动生成
> GitHub: https://github.com/aNewfolder/ai-project-coach

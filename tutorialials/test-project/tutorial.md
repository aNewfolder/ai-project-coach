# 测试项目部署教程
## 第1步:更新系统
```bash
apt-get update
apt-get install -y python3 python3-pip
python3 --version
pip3 install requests
python3 -c "import requests; print('成功!版本:', requests.__version__)"

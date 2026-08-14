本文主要面向开发者，介绍如何搭建 talebook 本地开发环境并修改代码。

## 项目结构

```
talebook/
  app/          # 前端：Nuxt 4 + Vue 3 + Vuetify 3
  webserver/    # 后端：Tornado + Calibre（Python）
  tests/        # 后端单元测试
  conf/         # Nginx / Supervisor 配置模板
  docker/       # 容器启动脚本和预置书籍
```

---

## 本地开发（推荐方式）

### 架构说明

推荐的本地开发方式：

- **后端**：`make dev` —— 用 Docker 容器运行后端，同时将 `webserver/` 目录挂载进容器，修改 Python 代码后服务自动重启。
- **前端**：`cd app && npm run dev` —— 本地启动 Nuxt 开发服务器（默认 `http://localhost:3000`），`nuxt.config.ts` 中的 `routeRules` 已配置将 `/api/**`、`/get/**`、`/read/**` 反向代理到后端容器（默认 `http://127.0.0.1:8080`）。

这种组合：前端热重载、后端自动重启，无需手动配置 Nginx。

### macOS 完全脱离 Docker

安装 Calibre.app，并初始化仓库虚拟环境：

```bash
brew install --cask calibre
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-test.txt
```

复制本地配置模板并设置数据根目录：

```bash
cp .env.example .env
```

编辑 `.env`：

```dotenv
TALEBOOK_LOCAL_ROOT=/Users/你的用户名/talebook-local
```

该目录下会自动创建 `data/`、`imports/`、`library/` 和 `audiobooks/`，之后无需在启动命令前重复传入变量。

检查环境并准备仓库根目录下的 `data/`、`imports/`、`library/`、`audiobooks/`：

```bash
make dev-local-check
```

终端 1 启动真实后端。首次运行会幂等创建 Calibre 书库和 Talebook 数据库：

```bash
make dev-local
```

确认后端可用：

```bash
curl --fail http://127.0.0.1:8080/api/welcome
```

终端 2 启动 Nuxt 前端：

```bash
make dev-ui-local
```

访问 `http://127.0.0.1:3000/`。该入口设置 `TALEBOOK_PROFILE=local`，不会修改生产默认路径，也不会使用 `~/.config/calibre`；Calibre 配置保存在 `$TALEBOOK_LOCAL_ROOT/data/calibre/`。如果 Calibre 安装在非标准位置，可在 `.env` 中设置 `TALEBOOK_CALIBRE_BIN_DIR=/path/to/calibre/bin`。

### 启动步骤

**第一步：启动后端容器**

```bash
make dev
```

容器会监听 `8080` 端口，日志写到 `/tmp/demo/log/talebook.log`：

```bash
tail -f /tmp/demo/log/talebook.log
```

**第二步：启动前端开发服务器**

```bash
cd app
npm install   # 首次运行需安装依赖
npm run dev
```

访问 `http://localhost:3000` 即可，API 请求会自动代理到后端容器。

### 修改代码

- **修改 Python 后端**：直接编辑 `webserver/` 下的文件，容器内的 Tornado 会自动检测并重启，无需重新 `make dev`。
- **修改前端**：直接编辑 `app/` 下的文件，Nuxt 开发服务器会热更新。

### 后端测试与检查

```bash
make lint-py-fix  # black + isort 自动格式化（开发完后必须执行）
make lint-py      # flake8 检查（必须通过才能提交）
make pytest       # 运行后端单元测试
```

### 前端测试与检查

```bash
cd app
npm run lint            # eslint 检查
npm run lint:fix        # eslint 自动修复
npx vitest run test/components/   # 组件单元测试
npx playwright test               # E2E 测试（需先启动 mock server）
```

---

## 手动搭建（不使用 Docker）

如果希望完全脱离 Docker 运行，以下是完整的手动搭建步骤。**推荐在 Linux 环境下进行**，Mac / Windows 未经完整测试。

随着版本更新，部分命令可能不及时更新；遇到问题可参考 [独立基础镜像仓库](https://github.com/talebook/talebook-base) 和 [本仓库 Dockerfile](../Dockerfile)。

### 准备目录

```bash
mkdir -p /data/log/nginx/
mkdir -p /var/www/talebook/
mkdir -p /data/{settings,progress,themes,logo,ssl,calibre,work/upload,work/convert,work/extract}
mkdir -p /imports /library /audiobooks
export CALIBRE_CONFIG_DIRECTORY=/data/calibre
```

### 拉取代码

```bash
cd /var/www/
git clone https://github.com/talebook/talebook.git
cd talebook
```

### 安装 Calibre 基础环境

参考 [talebook-base 的 Dockerfile](https://github.com/talebook/talebook-base/blob/master/Dockerfile)：

```bash
apt-get install -y tzdata
apt-get install -y --no-install-recommends python3-pip unzip supervisor sqlite3 git nginx python-setuptools curl
apt-get install -y calibre
```

### 安装 Python 依赖

```bash
# 国内镜像（可选）
# pip3 config set global.index-url https://mirrors.tencent.com/pypi/simple/

pip3 install -r /var/www/talebook/requirements.txt
pip3 install flake8 pytest
```

### 安装 Node.js

建议安装 LTS 版本：

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get install -y nodejs
```

### 编译前端

```bash
# 国内镜像（可选）
# npm config set registry http://mirrors.tencent.com/npm/

cd /var/www/talebook/app/
npm install
npm run generate   # 输出静态文件到 dist/
```

### 初始化书库与数据库

```bash
# 使用预置书籍创建书库
calibredb add --library-path=/library/ -r /var/www/talebook/docker/book/

# 创建程序 DB
python /var/www/talebook/server.py --syncdb

touch /data/settings/auto.py
```

### 配置并启动服务

```bash
cp conf/nginx/talebook.conf /etc/nginx/conf.d/
cp conf/supervisor/talebook.conf /etc/supervisor/conf.d/

service nginx restart
service supervisor restart
```

访问 `http://127.0.0.1/` 验证是否正常。

---

## 问题排查

### supervisord 启动失败

调整配置后必须执行 `sudo supervisorctl reload all` 使配置生效。

若提示 `talebook:tornado-8000: ERROR(spawn error)`，说明环境未配置正确，查看日志：

```bash
tail -100 /data/log/talebook.log
```

重点关注 `Traceback (most recent call last)` 后的错误信息。

### 网站能打开，但提示 `500: internal server error`

常见原因：目录权限不正确、数据库未创建、代码 BUG。

```bash
tail -100 /data/log/talebook.log
```

查看最近的 Traceback，确认错误原因后提 issue 联系开发者。

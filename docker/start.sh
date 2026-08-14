#!/bin/sh

PUID=${PUID:-0}
PGID=${PGID:-0}

groupmod -o -g "${PGID}" talebook
usermod -o -u "${PUID}" talebook

if [ "${PUID}" = "0" ]; then
  echo "WARNING: PUID=0 runs Talebook application processes as root; this is supported for compatibility but is not required for SSL upload."
fi

# 先识别破坏性升级前的旧布局。发现旧数据时只准备诊断页所需的最小目录，
# 不初始化新数据库或新书库；bootstrap 会以 legacy_storage_layout 明确失败。
legacy_layout=0
if [ -s /data/books/calibre-webserver.db ] || [ -e /data/books/settings/auto.py ] || [ -e /data/books/library/metadata.db ]; then
  legacy_layout=1
else
  for legacy_dir in imports library audiobooks progress themes logo ssl upload convert extract; do
    if [ -d "/data/books/$legacy_dir" ] && [ -n "$(find "/data/books/$legacy_dir" -mindepth 1 -print -quit 2>/dev/null)" ]; then
      legacy_layout=1
      break
    fi
  done
fi

mkdir -p \
  /data/settings /data/progress /data/themes /data/logo /data/ssl /data/calibre /data/log/nginx \
  /data/work/upload /data/work/convert /data/work/extract \
  /imports /library /audiobooks \
  /root/.npm /run/talebook /var/www/talebook/status

if [ "$legacy_layout" = "0" ]; then
  if [ ! -s /data/calibre-webserver.db ]; then
    cp /prebuilt/data/calibre-webserver.db /data/
  fi

  # 复制应用预置状态，但绝不覆盖管理员已有文件。
  cd /prebuilt/data || exit 1
  find . -type f -print | while read -r source; do
    target="/data/$source"
    if [ ! -e "$target" ]; then
      mkdir -p "$(dirname "$target")"
      cp "$source" "$target"
    fi
  done

  if [ ! -s /library/metadata.db ]; then
    cp -a /prebuilt/library/. /library/
  fi
fi

# Nginx 必须在 bootstrap 失败时仍能展示诊断页，因此默认证书独立兜底。
if [ ! -e /data/ssl/ssl.crt ]; then
  cp /prebuilt/data/ssl/ssl.crt /data/ssl/
fi
if [ ! -e /data/ssl/ssl.key ]; then
  cp /prebuilt/data/ssl/ssl.key /data/ssl/
fi

# 系统运行目录必须在 supervisord 前可用；持久化目录的递归属主修复与原子写入
# 校验由 webserver/self_check.py 负责，以便失败时进入可见状态页。
chown talebook:talebook /var/www/talebook/app
chown -R talebook:talebook \
  /run/talebook \
  /data/ssl \
  /data/log/ \
  /data/calibre \
  /var/lib/nginx \
  /var/log/nginx \
  /root/.npm \
  /var/www/talebook/app/.env \
  /var/www/talebook/app/dist \
  /var/www/talebook/webserver \
  /var/www/talebook/server.py \
  /var/www/talebook/status \
  /usr/lib/calibre \
  /usr/share/calibre

if [ -f /data/ssl/ssl.crt ]; then
  chmod 0644 /data/ssl/ssl.crt
fi
if [ -f /data/ssl/ssl.key ]; then
  chmod 0600 /data/ssl/ssl.key
fi

export PYTHONDONTWRITEBYTECODE=1

echo
echo "====== Start Server ===="
exec /usr/bin/supervisord --nodaemon -u root -c /etc/supervisor/supervisord.conf

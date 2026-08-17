#!/bin/sh

PUID=${PUID:-0}
PGID=${PGID:-0}

groupmod -o -g "${PGID}" talebook
usermod -o -u "${PUID}" talebook

if [ "${PUID}" = "0" ]; then
  echo "WARNING: PUID=0 runs Talebook application processes as root; this is supported for compatibility but is not required for SSL upload."
fi

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
if [ "$legacy_layout" = "1" ]; then
  echo "检测到旧版 /data/books 存储布局；请按升级文档迁移到 /data、/imports 和 /library，有声书资产请单独备份。"
  exit 1
fi

mkdir -p \
  /data/settings /data/progress /data/themes /data/logo /data/ssl /data/calibre /data/log/nginx \
  /data/work/upload /data/work/convert /data/work/extract \
  /imports /library \
  /root/.npm /run/talebook

if [ ! -s /data/calibre-webserver.db ]; then
  cp /prebuilt/data/calibre-webserver.db /data/
fi

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

permission_file=/data/.permission
touch "$permission_file"
permission=$(cat "$permission_file")
if [ "x$permission" != "x$PUID:$PGID" ]; then
  echo "updating persistent storage permission to $PUID:$PGID"
  chown -R talebook:talebook /data /library
  echo "$PUID:$PGID" > "$permission_file"
else
  chown -R talebook:talebook /data/settings || exit 1
fi

chown talebook:talebook /var/www/talebook/app
chown -R talebook:talebook \
  /run/talebook /data/ssl /data/log/ /data/calibre \
  /var/lib/nginx /var/log/nginx /root/.npm \
  /var/www/talebook/webserver /var/www/talebook/server.py \
  /usr/lib/calibre /usr/share/calibre

chmod 0644 /data/ssl/ssl.crt
chmod 0600 /data/ssl/ssl.key

APP_DIR=/var/www/talebook/app
if [ -f "${APP_DIR}/package.json" ] && [ ! -d "${APP_DIR}/node_modules" ]; then
  echo "====== Installing npm dependencies ======"
  cd "${APP_DIR}" && gosu talebook:talebook npm install
fi

check_atomic_write() {
  directory=$1
  gosu talebook:talebook sh -c '
    set -eu
    tmp=$(mktemp "$1/.talebook-write-test.XXXXXX")
    moved="${tmp}.replace"
    trap '\''rm -f "$tmp" "$moved"'\'' 0
    mv "$tmp" "$moved"
  ' talebook-write-check "$directory"
}

for directory in /data /library; do
  if ! check_atomic_write "$directory"; then
    echo "目录权限异常，无法以 PUID/PGID 原子写入 $directory"
    exit 1
  fi
done

export PYTHONDONTWRITEBYTECODE=1
echo
echo "====== Check config ===="
gosu talebook:talebook nginx -t || exit 1
echo
echo "====== Sync DB Scheme ===="
gosu talebook:talebook /var/www/talebook/server.py --syncdb
echo
echo "====== Migrate Database Schema ===="
gosu talebook:talebook python3 /var/www/talebook/webserver/migrate_db.py
echo
echo "====== Update Server Config ===="
gosu talebook:talebook /var/www/talebook/server.py --update-config
echo
echo "====== Start Server ===="
exec /usr/bin/supervisord --nodaemon -u root -c /etc/supervisor/supervisord.conf

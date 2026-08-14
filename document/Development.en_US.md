
This article is intended for developers, introducing how to set up the talebook local development environment and modify code.

## Project Structure

```
talebook/
  app/          # Frontend: Nuxt 4 + Vue 3 + Vuetify 3
  webserver/    # Backend: Tornado + Calibre (Python)
  tests/        # Backend unit tests
  conf/         # Nginx / Supervisor configuration templates
  docker/       # Container startup scripts and preset books
```

---

## Local Development (Recommended Way)

### Architecture

The recommended local development approach:

- **Backend**: `make dev` —— Run the backend in a Docker container, while mounting the `webserver/` directory into the container. The Python code will auto-restart the service after modifications.
- **Frontend**: `cd app && npm run dev` —— Start the Nuxt development server locally (default `http://localhost:3000`). The `routeRules` in `nuxt.config.ts` has configured reverse proxy for `/api/**`, `/get/**`, `/read/**` to the backend container (default `http://127.0.0.1:8080`).

This combination: frontend hot reload, backend auto-restart, no manual Nginx configuration needed.

### Fully local macOS development without Docker

Install Calibre.app and initialize the repository virtual environment:

```bash
brew install --cask calibre
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-test.txt
```

Copy the local configuration template and set the data root:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
TALEBOOK_LOCAL_ROOT=/Users/your-name/talebook-local
```

The launcher creates `data/`, `imports/`, `library/`, and `audiobooks/` below this directory. You no longer need to prefix startup commands with the variable.

Check the environment and prepare `data/`, `imports/`, `library/`, and `audiobooks/` below the repository root:

```bash
make dev-local-check
```

Start the real backend in terminal 1. The first run idempotently initializes the Calibre library and Talebook database:

```bash
make dev-local
```

Verify the backend:

```bash
curl --fail http://127.0.0.1:8080/api/welcome
```

Start Nuxt in terminal 2:

```bash
make dev-ui-local
```

Open `http://127.0.0.1:3000/`. This entry point enables `TALEBOOK_PROFILE=local`, leaves production defaults unchanged, and stores Calibre configuration in `$TALEBOOK_LOCAL_ROOT/data/calibre/` instead of `~/.config/calibre`. Set `TALEBOOK_CALIBRE_BIN_DIR=/path/to/calibre/bin` in `.env` when Calibre is installed outside its standard location.

### Startup Steps

**Step 1: Start the backend container**

```bash
make dev
```

The container listens on port `8080`, and logs are written to `/tmp/demo/log/talebook.log`:

```bash
tail -f /tmp/demo/log/talebook.log
```

**Step 2: Start the frontend development server**

```bash
cd app
npm install   # Install dependencies on first run
npm run dev
```

Visit `http://localhost:3000`, and API requests will automatically proxy to the backend container.

### Code Modifications

- **Modify Python backend**: Directly edit files under `webserver/`, and the Tornado in the container will automatically detect and restart. No need to re-run `make dev`.
- **Modify frontend**: Directly edit files under `app/`, and the Nuxt development server will hot reload.

### Backend Testing and Checking

```bash
make lint-py-fix  # black + isort auto formatting (must execute after development)
make lint-py      # flake8 checking (must pass before commit)
make pytest       # Run backend unit tests
```

### Frontend Testing and Checking

```bash
cd app
npm run lint            # eslint checking
npm run lint:fix        # eslint auto fix
npx vitest run test/components/   # Component unit tests
npx playwright test               # E2E tests (need to start mock server first)
```

---

## Manual Setup (Without Docker)

If you want to completely run without Docker, here are the complete manual setup steps. **It is recommended to perform this in a Linux environment**. Mac / Windows have not been fully tested.

As the version updates, some commands may not be updated in time; when encountering issues, you can refer to [calibre-docker/Dockerfile](https://github.com/talebook/calibre-docker/blob/master/Dockerfile) and [this repository's Dockerfile](../Dockerfile).

### Prepare Directories

```bash
mkdir -p /data/log/nginx/
mkdir -p /var/www/talebook/
mkdir -p /data/{settings,progress,themes,logo,ssl,calibre,work/upload,work/convert,work/extract}
mkdir -p /imports /library /audiobooks
export CALIBRE_CONFIG_DIRECTORY=/data/calibre
```

### Pull Code

```bash
cd /var/www/
git clone https://github.com/talebook/talebook.git
cd talebook
```

### Install Calibre Base Environment

Refer to [calibre-docker/Dockerfile](https://github.com/talebook/calibre-docker/blob/master/Dockerfile):

```bash
apt-get install -y tzdata
apt-get install -y --no-install-recommends python3-pip unzip supervisor sqlite3 git nginx python-setuptools curl
apt-get install -y calibre
```

### Install Python Dependencies

```bash
# Chinese mirror (optional)
# pip3 config set global.index-url https://mirrors.tencent.com/pypi/simple/

pip3 install -r /var/www/talebook/requirements.txt
pip3 install flake8 pytest
```

### Install Node.js

It is recommended to install the LTS version:

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get install -y nodejs
```

### Build Frontend

```bash
# Chinese mirror (optional)
# npm config set registry http://mirrors.tencent.com/npm/

cd /var/www/talebook/app/
npm install
npm run generate   # Output static files to dist/
```

### Initialize Library and Database

```bash
# Create library with preset books
calibredb add --library-path=/library/ -r /var/www/talebook/docker/book/

# Create program DB
python /var/www/talebook/server.py --syncdb

touch /data/settings/auto.py
```

### Configure and Start Services

```bash
cp conf/nginx/talebook.conf /etc/nginx/conf.d/
cp conf/supervisor/talebook.conf /etc/supervisor/conf.d/

service nginx restart
service supervisor restart
```

Visit `http://127.0.0.1/` to verify if it works normally.

---

## Troubleshooting

### supervisord Startup Failed

After adjusting the configuration, you must execute `sudo supervisorctl reload all` to make the configuration take effect.

If it prompts `talebook:tornado-8000: ERROR(spawn error)`, it means the environment is not configured correctly. Check the logs:

```bash
tail -100 /data/log/talebook.log
```

Focus on the error message after `Traceback (most recent call last)`.

### Website Can Open, but Prompts `500: internal server error`

Common reasons: incorrect directory permissions, database not created, code bug.

```bash
tail -100 /data/log/talebook.log
```

Check the latest Traceback, confirm the error reason, and submit an issue to contact the developer.

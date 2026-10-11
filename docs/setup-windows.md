# Setting up your machine (Stage 0)

For Mozart's laptop: Windows, 16 GB RAM, NVIDIA RTX 3050 (6 GB). Do the steps in order. Everything here is free.

## 1. Free disk space: target 40 GB free, ideally 60 GB

The full setup needs about 15 to 22 GB, and builds need headroom.

- Settings → System → Storage → Temporary files: remove Windows Update cleanup, Delivery Optimization files, temporary files.
- Settings → Apps: uninstall what you do not use.
- After the new repo is set up (step 8), delete the old virtual environments in the V3 folder: `oms_infodemie_v3\.venv` and `oms_infodemie_v3\OMS_Demo\.venv`. They can be recreated and usually take hundreds of MB to a few GB each.
- If you have a second drive, Ollama models can live there (set the `OLLAMA_MODELS` environment variable to a folder on that drive before pulling models).

## 2. WSL2 with Ubuntu

In PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart, open Ubuntu, create your Linux user. Then create `C:\Users\fatna\.wslconfig` with:

```ini
[wsl2]
memory=8GB
networkingMode=mirrored
```

Run `wsl --shutdown` in PowerShell and reopen Ubuntu. Mirrored networking lets Linux reach Ollama on Windows at `http://localhost:11434`.

Work inside the Linux file system (`~/pnsi`), not in OneDrive or `/mnt/c`. It is much faster and avoids sync conflicts.

## 3. Docker Engine inside Ubuntu

Lighter than Docker Desktop. In Ubuntu:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# close and reopen the Ubuntu terminal, then:
docker run --rm hello-world
```

## 4. NVIDIA driver and Ollama (on Windows)

1. Update the NVIDIA driver from nvidia.com or the NVIDIA app.
2. Install Ollama for Windows from ollama.com.
3. In PowerShell:

```powershell
ollama pull bge-m3
ollama pull qwen3:4b
```

4. In Ubuntu, check: `curl http://localhost:11434/api/tags` should list both models.

## 5. Developer tools (in Ubuntu)

```bash
sudo apt update && sudo apt install -y git build-essential curl unzip gh
# Python tooling
curl -LsSf https://astral.sh/uv/install.sh | sh
# Node 22 and pnpm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
corepack enable
# GitHub login
gh auth login
git config --global user.name "Mohamed Fatnassi"
git config --global user.email "<your GitHub email>"
```

## 6. Claude Code (in Ubuntu)

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

Then run `claude` once and log in with your Claude account.

Plugins: inside a Claude Code session, run `/plugin` and open the Discover tab. Search for and install (project or user scope):

- `frontend-design` (interface quality)
- `feature-dev`, `code-review`, `security-guidance`, `commit-commands`
- the code intelligence (language server) plugins for Python and TypeScript
- a Playwright plugin if one is listed, for browser tests of the UI and RTL

Plugins you enabled on claude.ai sync into terminal sessions and appear as `<name>@synced` in `/plugin` (Installed tab). Check that your design plugins are there.

Taste skills (design quality, MIT licence), from your repo folder:

```bash
cd ~/pnsi
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
npx skills add https://github.com/Leonxlnx/taste-skill --skill "minimalist-ui"
```

Check that they land in `.claude/skills/` (or wherever the tool reports) and appear when you type `/` in Claude Code. If the CLI asks which agent to install for, choose Claude Code.

The project's own skills are already in the repo under `.claude/skills/` and load automatically.

## 7. Free accounts and keys

Put every value in `~/pnsi/.env` (copied from `.env.example`). Never commit `.env`.

| Service | Where | What to copy into .env |
| --- | --- | --- |
| Gemini API | aistudio.google.com → Get API key | `GEMINI_API_KEY` |
| Groq | console.groq.com → API Keys | `GROQ_API_KEY` |
| Google Cloud | console.cloud.google.com → new project "pnsi" → enable "YouTube Data API v3" and "Fact Check Tools API" → Credentials → API key, restricted to those two APIs | `GOOGLE_API_KEY` |
| Telegram API | my.telegram.org → API development tools (a dedicated phone number is better) | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE` |
| Telegram bot | In Telegram, talk to @BotFather → /newbot (for the tipline) | `TELEGRAM_BOT_TOKEN` |
| Apify | apify.com → sign up → Settings → API & Integrations | `APIFY_TOKEN` |
| NCBI (optional) | ncbi.nlm.nih.gov account → API key | `NCBI_API_KEY`, `NCBI_EMAIL` |

Applications to start now, because approval takes time:

- **Reddit:** create an app at reddit.com/prefs/apps and request Data API access under the Responsible Builder Policy. Describe the public health monitoring use honestly.
- **Meta:** create a developer account and an app at developers.facebook.com. App Review for Page Public Content Access and Instagram hashtag search comes later and needs business verification.

Facebook monitoring accounts (decision D4): use real, identifiable accounts (yours or teammates'), not invented personas. Use a separate Chrome profile for each monitoring account and install the PNSI Capture extension there once it exists (stage 3).

## 8. Create the repository

In Ubuntu:

```bash
mkdir -p ~/pnsi
cp -r "/mnt/c/Users/fatna/OneDrive/Desktop/oms_infodemie_v3/pnsi-starter/pnsi/." ~/pnsi/
cd ~/pnsi
cp .env.example .env      # then fill in the keys
git init -b main
git add .
git commit -m "Starter pack: docs, decisions, plan, skills, legacy V3 reference"
gh repo create cybermo-bot/pnsi --private --source=. --push
```

Check on github.com that `.env` is not in the repository.

## 9. First Claude Code session

```bash
cd ~/pnsi
claude
```

First message:

> Read CLAUDE.md, docs/decisions.md and docs/build-plan.md. We are starting Stage 1. Use plan mode: propose the plan for Stage 1 with the repository structure, the database schema and the test strategy, and wait for my approval before writing code.

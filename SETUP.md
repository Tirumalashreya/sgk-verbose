# Setup on a New Laptop

## Step 1 — Clone the repo

```bash
git clone https://github.com/Tirumalashreya/sgk-verbose.git
cd sgk-verbose
```

## Step 2 — Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Then run `claude` and log in with your Anthropic accoun
 the browser.

## Step 3 — Restore Claude memory

This makes Claude remember the full project context without re-explaining anything.

Find your username on the new laptop:
```bash
whoami
```

Then run (replace `YOUR_USERNAME` with the result):
```bash
mkdir -p /Users/YOUR_USERNAME/.claude/projects/-Users-YOUR_USERNAME-Desktop-sgk-verba/memory/

cp /Users/YOUR_USERNAME/Desktop/sgk-verba/claude-memory/* \
   /Users/YOUR_USERNAME/.claude/projects/-Users-YOUR_USERNAME-Desktop-sgk-verba/memory/
```

**Example** — if `whoami` prints `shreya`:
```bash
mkdir -p /Users/shreya/.claude/projects/-Users-shreya-Desktop-sgk-verba/memory/

cp /Users/shreya/Desktop/sgk-verba/claude-memory/* \
   /Users/shreya/.claude/projects/-Users-shreya-Desktop-sgk-verba/memory/
```

> The memory folder name is your project path with `/` replaced by `-`.
> Project is at `/Users/shreya/Desktop/sgk-verba` → folder is `-Users-shreya-Desktop-sgk-verba`

## Step 4 — Python backend setup

```bash
cd verba-pravachana-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_actual_key_here
```



Get a key from: https://ai.google.dev/

## Step 5 — React Native frontend setup

```bash
cd ../sgks
-app
npm install
```

## Step 6 — Open Claude in the project

```bash
cd /Users/YOUR_USERNAME/Desktop/sgk-verba
claude
```

Claude will load all memory automatically. No need to re-explain the project.

## To run the project

**Backend:**
```bash
cd verba-pravachana-ai
source venv/bin/activate
python main.py
```

**Frontend:**
```bash
cd sgks-app
npx expo start
```


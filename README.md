# 🐛 Github Bug Detection System

AI-powered system to detect and predict bugs in GitHub repositories using commit history, code analysis, and machine learning.

## ✨ Features

- **🔗 GitHub URL Analysis** - Paste any GitHub repo URL and analyze it instantly
- **📁 File Upload** - Upload JSON data with repository commits
- **📝 Manual Input** - Paste JSON data directly
- **🤖 ML-Powered** - Train custom models on your data
- **🎓 Self-Learning** - Model improves from user feedback automatically
- **📊 Risk Scoring** - Get 0-100% risk scores for each file
- **🔍 Code Analysis** - Detects 15+ types of security issues and code smells
- **🎨 Beautiful UI** - Modern React interface with color-coded results

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cd src
python api.py
```

API runs on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

UI runs on `http://localhost:3000`

### 3. Analyze a Repository

**Option 1: GitHub URL** (Easiest)
- Open http://localhost:3000
- Click "🔗 GitHub URL" tab
- Enter: `facebook/react` or `https://github.com/facebook/react`
- Click "Analyze Repository"

**Option 2: Upload File**
- Click "📁 Upload File" tab
- Upload a JSON file with commit data

**Option 3: Paste JSON**
- Click "📝 JSON Data" tab
- Click "Load Sample" to see format
- Paste your data and analyze

## 📖 How It Works

1. **Fetch Data**: Pulls commits, diffs, and issues from GitHub
2. **Extract Features**: Analyzes bug keywords, change frequency, complexity
3. **Calculate Risk**: Assigns 0-1 risk scores to each file
4. **Rank Results**: Shows highest-risk files first with explanations

## 🔑 GitHub Token (Optional)

For private repos and higher rate limits:

1. Get token: https://github.com/settings/tokens
2. Paste in "Optional: GitHub Token" field
3. Enjoy 5000 requests/hour (vs 60 without token)

See [GITHUB_SETUP.md](backend/GITHUB_SETUP.md) for details.

## 🎓 Train Custom Model

```bash
cd backend/src
python trainer.py
```

Add your own repository data to `backend/data/sample_repos.json` for better accuracy.

## 📡 API Endpoints

- `POST /analyze-github-url` - Analyze by GitHub URL
- `POST /analyze-github-file` - Upload JSON file
- `POST /predict` - Predict from JSON data
- `GET /` - Health check

## 🎯 Risk Factors

- Bug-related keywords (fix, bug, error, hotfix, patch)
- Commit frequency per file
- Code change complexity
- Historical bug patterns
- Issue tracking data

## 📊 Example Output

```json
{
  "repository_name": "owner/repo",
  "overall_repository_risk": 0.73,
  "modules": [
    {
      "file": "authController.js",
      "risk_score": 0.82,
      "reason": "Frequent bug-related commits and large authentication logic changes."
    }
  ]
}
```

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, scikit-learn, PyGithub
- **Frontend**: React, Vite
- **ML**: RandomForest Classifier

## 📝 License

MIT

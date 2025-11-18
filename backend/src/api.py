from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
import asyncio
from .predictor import BugPredictor
from .github_analyzer import GitHubAnalyzer
from .incremental_learner import IncrementalLearner
from .feedback_api import router as feedback_router
from .progress_tracker import ProgressTracker
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Github Bug Detection API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize shared instances
predictor = BugPredictor()
learner = IncrementalLearner()
progress_tracker = ProgressTracker()

# Set learner for feedback API
from . import feedback_api
feedback_api.set_learner(learner)

# Include feedback/learning endpoints
app.include_router(feedback_router, prefix="/api/learning", tags=["learning"])

# Initialize enhanced features flag (will be set later)
ENHANCED_FEATURES_ENABLED = False
oauth_handler = None
user_manager = None
gemini_analyzer = None

# Import new modules (optional - graceful degradation)
try:
    from .oauth_handler import OAuthHandler
    from .user_manager import UserManager
    from .gemini_analyzer import GeminiAnalyzer
    
    oauth_handler = OAuthHandler()
    user_manager = UserManager()
    gemini_analyzer = GeminiAnalyzer()
    ENHANCED_FEATURES_ENABLED = True
    print("✓ Enhanced features enabled (OAuth, Gemini AI, User Management)")
except ImportError as e:
    print(f"⚠ Enhanced features disabled: {e}")
    print("  Run: pip install google-generativeai authlib python-jose[cryptography] httpx")

class Commit(BaseModel):
    message: str
    diff: str
    files_changed: List[str]
    hash: Optional[str] = ""

class Issue(BaseModel):
    commit_hash: str
    type: str

class RepositoryData(BaseModel):
    repository_name: str
    commits: List[Commit]
    issues: List[Issue]

class GitHubURLRequest(BaseModel):
    repo_url: str
    max_commits: Optional[int] = 100
    access_token: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class GitHubAuthRequest(BaseModel):
    access_token: str

@app.get("/")
def root():
    return {
        "message": "Github Bug Detection API",
        "status": "running",
        "features": {
            "self_learning": True,
            "feedback_api": True,
            "code_analysis": True,
            "enhanced_features": ENHANCED_FEATURES_ENABLED,
            "gemini_ai": ENHANCED_FEATURES_ENABLED,
            "oauth": ENHANCED_FEATURES_ENABLED,
            "user_management": ENHANCED_FEATURES_ENABLED
        },
        "note": "Install enhanced features: pip install google-generativeai authlib python-jose[cryptography] httpx" if not ENHANCED_FEATURES_ENABLED else "All features enabled"
    }

@app.post("/predict")
def predict_bugs(data: RepositoryData):
    """Predict bug risk for repository modules"""
    try:
        repo_dict = data.model_dump()
        result = predictor.predict_repository_risk(repo_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """Stream progress updates for an analysis session"""
    progress_tracker.create_session(session_id)
    
    return StreamingResponse(
        progress_tracker.get_updates(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/analyze-github-url")
async def analyze_github_url(request: GitHubURLRequest):
    """Analyze a GitHub repository by URL with progress tracking"""
    session_id = request.session_id or "default"
    
    try:
        await progress_tracker.update(session_id, "starting", "Initializing analysis...", 0)
        print(f"\n=== Analyzing GitHub URL: {request.repo_url} ===")
        
        # Validate input
        if not request.repo_url or not request.repo_url.strip():
            await progress_tracker.update(session_id, "error", "Repository URL is required")
            raise HTTPException(status_code=400, detail="Repository URL is required")
        
        await progress_tracker.update(session_id, "fetching", "Connecting to GitHub...", 10)
        
        analyzer = GitHubAnalyzer(
            access_token=request.access_token,
            progress_tracker=progress_tracker,
            session_id=session_id
        )
        
        # Analyze repository
        await progress_tracker.update(session_id, "analyzing", "Fetching repository data...", 20)
        repo_data = analyzer.analyze_repository(
            request.repo_url, 
            max_commits=request.max_commits
        )
        
        # Predict bug risk
        await progress_tracker.update(session_id, "predicting", "Calculating risk scores...", 70)
        result = predictor.predict_repository_risk(repo_data)
        result["metadata"] = repo_data.get("metadata", {})
        
        # Add Gemini AI analysis if available
        if ENHANCED_FEATURES_ENABLED and gemini_analyzer:
            try:
                await progress_tracker.update(session_id, "gemini", "Running Gemini AI analysis...", 80)
                ml_analysis_summary = {
                    "repository": result['repository_name'],
                    "overall_risk": result['overall_repository_risk'],
                    "total_files": len(result.get('modules', [])),
                    "high_risk_files": [m for m in result.get('modules', []) if m['risk_score'] >= 0.7],
                    "medium_risk_files": [m for m in result.get('modules', []) if 0.4 <= m['risk_score'] < 0.7],
                    "modules": result.get('modules', [])[:10]
                }
                gemini_result = gemini_analyzer.analyze_ml_results(ml_analysis_summary)
                result["gemini_analysis"] = gemini_result
                print(f"✅ Gemini AI analysis completed")
                print(f"   - Has recommendations: {bool(gemini_result.get('recommendations'))}")
                print(f"   - Recommendations count: {len(gemini_result.get('recommendations', []))}")
            except Exception as e:
                print(f"❌ Gemini AI analysis failed: {e}")
                # Don't fail the entire request, just add error info
                result["gemini_analysis"] = {
                    "error": str(e),
                    "overall_risk": int(result['overall_repository_risk'] * 100),
                    "files_analyzed": 0,
                    "files": [],
                    "recommendations": [],
                    "critical_concerns": [],
                    "summary": f"Gemini AI analysis failed: {str(e)[:200]}"
                }
                await progress_tracker.update(session_id, "warning", f"Gemini AI unavailable, using ML only")
        
        # Record analysis for learning
        await progress_tracker.update(session_id, "recording", "Saving analysis...", 90)
        record_id = learner.record_analysis(repo_data, result)
        result["record_id"] = record_id
        
        # Save analysis data if user_id is provided
        if request.user_id:
            print(f"💾 Saving analysis for user: {request.user_id}")
            if ENHANCED_FEATURES_ENABLED:
                # Try MongoDB first
                if user_manager.mongodb.is_connected():
                    user_manager.mongodb.save_analysis(request.user_id, result)
                    print(f"✅ Analysis saved to MongoDB for user {request.user_id}")
                else:
                    # Fallback to local file
                    user_manager.save_analysis_local(request.user_id, result)
                    print(f"✅ Analysis saved locally for user {request.user_id}")
            else:
                print(f"⚠️ Enhanced features not enabled, cannot save analysis")
        else:
            print(f"⚠️ No user_id provided, analysis not saved to user profile")
        
        await progress_tracker.update(session_id, "complete", "Analysis complete!", 100)
        print(f"✓ Analysis complete for {result['repository_name']}")
        
        return result
    except HTTPException:
        await progress_tracker.update(session_id, "error", "Analysis failed")
        raise
    except Exception as e:
        error_msg = str(e)
        await progress_tracker.update(session_id, "error", f"Error: {error_msg}")
        print(f"✗ Error: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    finally:
        # Cleanup after a delay
        await asyncio.sleep(2)
        progress_tracker.cleanup_session(session_id)

@app.post("/analyze-github-file")
async def analyze_github_file(file: UploadFile = File(...)):
    """Analyze repository from uploaded JSON file"""
    try:
        contents = await file.read()
        repo_data = json.loads(contents)
        
        # Validate structure
        if "commits" not in repo_data:
            raise ValueError("Invalid file format. Must contain 'commits' field.")
        
        result = predictor.predict_repository_risk(repo_data)
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/github/repos")
def get_user_repos(request: GitHubAuthRequest):
    """Get list of user's repositories"""
    try:
        analyzer = GitHubAnalyzer(access_token=request.access_token)
        repos = analyzer.get_user_repos()
        return {"repositories": repos}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/github/rate-limit")
def check_rate_limit():
    """Check GitHub API rate limit"""
    try:
        analyzer = GitHubAnalyzer()
        analyzer.check_rate_limit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/demo")
def get_demo_analysis():
    """Get demo analysis with code issues for testing"""
    demo_data = {
        "repository_name": "demo/vulnerable-app",
        "commits": [
            {
                "hash": "abc123",
                "message": "Fixed SQL injection bug",
                "diff": "+ const query = \"SELECT * FROM users WHERE id = '\" + userId + \"'\";\n+ db.execute(query);",
                "files_changed": ["database.js"],
                "code_issues": [
                    {
                        "file": "database.js",
                        "issues": 1,
                        "severity_counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
                        "detailed_issues": [
                            {
                                "type": "sql_injection",
                                "severity": "critical",
                                "message": "Potential SQL injection vulnerability",
                                "line": 42,
                                "code_snippet": "const query = \"SELECT * FROM users WHERE id = '\" + userId + \"'\";",
                                "fix": "Use parameterized queries or prepared statements",
                                "impact": "Attackers can execute arbitrary SQL, steal or delete data"
                            }
                        ]
                    }
                ]
            },
            {
                "hash": "def456",
                "message": "Added error handling",
                "diff": "+ try {\n+   riskyOperation();\n+ } catch (error) {\n+ }",
                "files_changed": ["app.js"],
                "code_issues": [
                    {
                        "file": "app.js",
                        "issues": 2,
                        "severity_counts": {"critical": 0, "high": 2, "medium": 0, "low": 0},
                        "detailed_issues": [
                            {
                                "type": "empty_catch",
                                "severity": "high",
                                "message": "Empty catch block - errors silently ignored",
                                "line": 15,
                                "code_snippet": "} catch (error) { }",
                                "fix": "Add error logging or proper error handling",
                                "impact": "Errors are swallowed, making debugging impossible"
                            }
                        ]
                    }
                ]
            },
            {
                "hash": "ghi789",
                "message": "Added authentication",
                "diff": "+ const password = \"admin123\";\n+ if (userPassword == password) {",
                "files_changed": ["auth.js"],
                "code_issues": [
                    {
                        "file": "auth.js",
                        "issues": 2,
                        "severity_counts": {"critical": 1, "high": 0, "medium": 1, "low": 0},
                        "detailed_issues": [
                            {
                                "type": "hardcoded_password",
                                "severity": "critical",
                                "message": "Hardcoded password detected",
                                "line": 8,
                                "code_snippet": "const password = \"admin123\";",
                                "fix": "Use environment variables or secure credential storage",
                                "impact": "Credentials exposed in source code, major security risk"
                            },
                            {
                                "type": "double_equals",
                                "severity": "medium",
                                "message": "Use === instead of ==",
                                "line": 9,
                                "code_snippet": "if (userPassword == password) {",
                                "fix": "Replace == with === for strict equality comparison",
                                "impact": "Loose equality can cause unexpected type coercion"
                            }
                        ]
                    }
                ]
            }
        ],
        "issues": [],
        "metadata": {
            "stars": 42,
            "forks": 15,
            "language": "JavaScript",
            "description": "Demo app with intentional vulnerabilities"
        }
    }
    
    result = predictor.predict_repository_risk(demo_data)
    result["metadata"] = demo_data.get("metadata", {})
    
    # Record demo analysis for learning
    record_id = learner.record_analysis(demo_data, result)
    result["record_id"] = record_id
    
    return result

# OAuth & Authentication Endpoints
@app.get("/auth/github")
def github_auth():
    """Get GitHub OAuth authorization URL"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced features not available. Install dependencies: pip install google-generativeai authlib python-jose[cryptography] httpx")
    return {"authorization_url": oauth_handler.get_authorization_url()}

@app.post("/auth/callback")
async def github_callback(code: str):
    """Handle GitHub OAuth callback"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced features not available")
    try:
        # Exchange code for token
        token_data = await oauth_handler.exchange_code_for_token(code)
        access_token = token_data.get('access_token')
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Get user info
        user_info = await oauth_handler.get_user_info(access_token)
        
        # Create or update user
        user_profile = user_manager.create_or_update_user(user_info)
        
        # Create JWT token
        jwt_token = oauth_handler.create_jwt_token(user_info)
        
        return {
            "token": jwt_token,
            "user": user_profile,
            "github_token": access_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/auth/verify")
def verify_token(token: str):
    """Verify JWT token"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced features not available")
    payload = oauth_handler.verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"valid": True, "user": payload}

# User Management Endpoints
@app.get("/user/{user_id}")
def get_user_profile(user_id: str):
    """Get user profile"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced features not available")
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/user/{user_id}/stats")
def get_user_stats(user_id: str):
    """Get user statistics"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced features not available")
    
    print(f"📊 Getting stats for user: {user_id}")
    stats = user_manager.get_user_stats(user_id)
    
    if not stats or (stats.get('total_analyses') == 0 and stats.get('repositories_analyzed') == 0):
        print(f"⚠ No stats found for user {user_id}, returning defaults")
        # Return default stats instead of 404
        return {
            'total_analyses': 0,
            'repositories_analyzed': 0,
            'average_risk': 0,
            'last_analysis': None,
            'member_since': None
        }
    
    print(f"✓ Stats found: {stats}")
    return stats

@app.get("/user/{user_id}/repositories")
async def get_user_repositories(user_id: str, github_token: str):
    """Get user's GitHub repositories"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced features not available")
    try:
        repos = await oauth_handler.get_user_repos(github_token)
        return {"repositories": repos}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Gemini AI Analysis Endpoints
class GeminiAnalysisRequest(BaseModel):
    code: str
    filename: Optional[str] = "unknown"

@app.post("/analyze/gemini")
def analyze_with_gemini(request: GeminiAnalysisRequest):
    """Deep code analysis using Gemini AI"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Gemini AI not available. Install: pip install google-generativeai")
    try:
        result = gemini_analyzer.analyze_code(request.code, request.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/gemini/repository")
def analyze_repository_with_gemini(files_data: List[dict]):
    """Analyze multiple files with Gemini AI"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Gemini AI not available")
    try:
        result = gemini_analyzer.analyze_repository(files_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Analysis with Gemini
@app.post("/analyze-enhanced")
async def analyze_enhanced(request: GitHubURLRequest):
    """Enhanced analysis combining traditional ML + Gemini AI"""
    if not ENHANCED_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="Enhanced analysis not available. Use /analyze-github-url instead")
    
    session_id = request.session_id or "default"
    user_id = request.user_id  # Get user_id from request
    
    try:
        await progress_tracker.update(session_id, "starting", "Starting enhanced analysis...", 0)
        
        # Traditional analysis
        await progress_tracker.update(session_id, "analyzing", "Running ML analysis...", 20)
        analyzer = GitHubAnalyzer(
            access_token=request.access_token,
            progress_tracker=progress_tracker,
            session_id=session_id
        )
        repo_data = analyzer.analyze_repository(request.repo_url, max_commits=request.max_commits)
        ml_result = predictor.predict_repository_risk(repo_data)
        
        # Gemini AI analysis - analyze ML results with AI
        await progress_tracker.update(session_id, "gemini", "Running Gemini AI analysis...", 60)
        
        try:
            # Prepare ML analysis data for Gemini
            ml_analysis_summary = {
                "repository": ml_result['repository_name'],
                "overall_risk": ml_result['overall_repository_risk'],
                "total_files": len(ml_result.get('modules', [])),
                "high_risk_files": [m for m in ml_result.get('modules', []) if m['risk_score'] >= 0.7],
                "medium_risk_files": [m for m in ml_result.get('modules', []) if 0.4 <= m['risk_score'] < 0.7],
                "modules": ml_result.get('modules', [])[:10]  # Top 10 risky files
            }
            
            # Get Gemini's interpretation of the ML results
            gemini_result = gemini_analyzer.analyze_ml_results(ml_analysis_summary)
            
        except Exception as e:
            print(f"Error in Gemini analysis: {e}")
            gemini_result = {
                "overall_risk": int(ml_result['overall_repository_risk'] * 100),
                "files_analyzed": len(ml_result.get('modules', [])),
                "files": [],
                "summary": f"ML Analysis shows {len(ml_result.get('modules', []))} files with potential issues.",
                "error": str(e)
            }
        
        # Combine results
        await progress_tracker.update(session_id, "combining", "Combining results...", 90)
        combined_result = {
            **ml_result,
            "gemini_analysis": gemini_result,
            "enhanced": True,
            "metadata": repo_data.get("metadata", {})
        }
        
        # Save analysis to MongoDB and update user stats
        if user_id:
            print(f"💾 Saving enhanced analysis for user: {user_id}")
            if user_manager.mongodb.is_connected():
                user_manager.mongodb.save_analysis(user_id, combined_result)
                print(f"✅ Enhanced analysis saved to MongoDB for user {user_id}")
            else:
                # Fallback to local storage
                user_manager.save_analysis_local(user_id, combined_result)
                print(f"✅ Enhanced analysis saved locally for user {user_id}")
        else:
            print(f"⚠️ No user_id provided for enhanced analysis")
        
        await progress_tracker.update(session_id, "complete", "Enhanced analysis complete!", 100)
        return combined_result
        
    except Exception as e:
        await progress_tracker.update(session_id, "error", f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await asyncio.sleep(2)
        progress_tracker.cleanup_session(session_id)

# Analytics Endpoints
@app.get("/analytics/overview")
def get_analytics_overview():
    """Get overall analytics"""
    # Get all user files
    users_dir = "data/users"
    if not os.path.exists(users_dir):
        return {"total_users": 0, "total_analyses": 0, "average_risk": 0}
    
    total_users = 0
    total_analyses = 0
    total_risk = 0
    risk_count = 0
    
    for filename in os.listdir(users_dir):
        if filename.endswith('.json'):
            total_users += 1
            with open(os.path.join(users_dir, filename), 'r') as f:
                user_data = json.load(f)
                total_analyses += user_data.get('analysis_count', 0)
                for repo in user_data.get('repositories', []):
                    total_risk += repo.get('risk_score', 0)
                    risk_count += 1
    
    return {
        "total_users": total_users,
        "total_analyses": total_analyses,
        "average_risk": round(total_risk / risk_count, 2) if risk_count > 0 else 0,
        "repositories_analyzed": risk_count
    }

@app.get("/analytics/trends")
def get_analytics_trends(user_id: Optional[str] = None):
    """Get trend data for charts"""
    if user_id:
        # Try MongoDB first
        if user_manager.mongodb.is_connected():
            return user_manager.mongodb.get_analytics_trends(user_id)
        
        # Fallback to local storage
        user = user_manager.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        repos = user.get('repositories', [])
        return {
            "labels": [r.get('analyzed_at', '')[:10] for r in repos[-10:]],
            "risk_scores": [r.get('risk_score', 0) for r in repos[-10:]],
            "repository_names": [r.get('name', '') for r in repos[-10:]]
        }
    
    return {"labels": [], "risk_scores": [], "repository_names": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

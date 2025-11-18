"""
Gemini AI Integration for Deep Code Analysis
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiAnalyzer:
    def __init__(self):
        # Load multiple API keys for fallback
        self.api_keys = []
        for i in range(1, 10):  # Support up to 9 backup keys
            key_name = 'GEMINI_API_KEY' if i == 1 else f'GEMINI_API_KEY_{i}'
            api_key = os.getenv(key_name)
            if api_key:
                self.api_keys.append(api_key)
        
        if not self.api_keys:
            raise ValueError("No GEMINI_API_KEY found in environment")
        
        print(f"✓ Loaded {len(self.api_keys)} Gemini API key(s) for fallback")
        
        # Try to initialize with the first working key
        self.current_key_index = 0
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model with current API key"""
        try:
            api_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            print(f"✓ Using Gemini API key #{self.current_key_index + 1} (stable)")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize with key #{self.current_key_index + 1}: {e}")
            return False
    
    def _switch_to_next_key(self):
        """Switch to the next available API key"""
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            print("❌ All API keys exhausted")
            return False
        
        print(f"🔄 Switching to backup API key #{self.current_key_index + 1}")
        return self._initialize_model()
    
    def _make_request_with_fallback(self, prompt: str, max_retries: int = None):
        """Make a request with automatic fallback to backup keys"""
        if max_retries is None:
            max_retries = len(self.api_keys)
        
        attempts = 0
        last_error = None
        
        while attempts < max_retries:
            try:
                if not self.model:
                    if not self._initialize_model():
                        raise Exception("Failed to initialize model")
                
                response = self.model.generate_content(prompt)
                print(f"✅ Request successful with API key #{self.current_key_index + 1}")
                return response
            
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check if it's a quota/rate limit error
                if 'quota' in error_msg or 'rate limit' in error_msg or '429' in error_msg or 'resource_exhausted' in error_msg:
                    print(f"⚠️ API key #{self.current_key_index + 1} quota exceeded: {e}")
                    
                    # Try next key
                    if not self._switch_to_next_key():
                        raise Exception(f"All {len(self.api_keys)} API keys exhausted. Last error: {e}")
                    
                    attempts += 1
                    continue
                else:
                    # Non-quota error, don't retry
                    print(f"❌ Non-quota error with key #{self.current_key_index + 1}: {e}")
                    raise e
        
        raise Exception(f"Failed after {attempts} attempts with {len(self.api_keys)} API keys. Last error: {last_error}")
    
    def analyze_code(self, code: str, filename: str = "unknown") -> dict:
        """Deep code analysis using Gemini AI"""
        prompt = f"""You are an expert code reviewer. Analyze this code file '{filename}' in detail.

Code:
```
{code[:5000]}
```

Provide a comprehensive analysis in JSON format with:
1. risk_score: 0-100 (0=safe, 100=critical issues)
2. vulnerabilities: array of security vulnerabilities with descriptions
3. bugs: array of potential bugs with explanations
4. code_smells: array of code quality issues
5. suggestions: array of specific improvement recommendations
6. explanation: A detailed 2-3 sentence summary of the code's purpose and main concerns

Be specific and actionable. Format as valid JSON."""

        try:
            response = self._make_request_with_fallback(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            return {
                "risk_score": 50,
                "error": str(e),
                "vulnerabilities": [],
                "bugs": [],
                "code_smells": [],
                "suggestions": ["Unable to analyze with Gemini AI"],
                "explanation": f"Analysis failed: {str(e)}"
            }
    
    def _parse_response(self, text: str) -> dict:
        """Parse Gemini response"""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback parsing
        return {
            "risk_score": 60,
            "vulnerabilities": self._extract_list(text, "vulnerabilit"),
            "bugs": self._extract_list(text, "bug"),
            "code_smells": self._extract_list(text, "smell"),
            "suggestions": self._extract_list(text, "suggest"),
            "explanation": text[:200]
        }
    
    def _extract_list(self, text: str, keyword: str) -> list:
        """Extract items from text"""
        lines = text.lower().split('\n')
        items = []
        for line in lines:
            if keyword in line and ('-' in line or '*' in line):
                items.append(line.strip('- *').strip())
        return items[:5]  # Limit to 5 items
    
    def analyze_repository(self, files_data: list) -> dict:
        """Analyze multiple files in a repository"""
        results = []
        total_risk = 0
        
        for file_info in files_data[:10]:  # Limit to 10 files
            filename = file_info.get('filename', 'unknown')
            code = file_info.get('code', '')
            
            if code:
                analysis = self.analyze_code(code, filename)
                results.append({
                    "filename": filename,
                    **analysis
                })
                total_risk += analysis.get('risk_score', 50)
        
        avg_risk = total_risk / len(results) if results else 0
        
        return {
            "overall_risk": round(avg_risk, 2),
            "files_analyzed": len(results),
            "files": results
        }

    
    def analyze_ml_results(self, ml_data: dict) -> dict:
        """Analyze ML prediction results and provide AI-powered insights"""
        prompt = f"""You are an expert software security analyst and code quality expert. Analyze these ML-based bug prediction results and provide an extremely detailed, comprehensive analysis.

Repository: {ml_data['repository']}
Overall Risk Score: {ml_data['overall_risk'] * 100:.1f}%
Total Files Analyzed: {ml_data['total_files']}
High Risk Files: {len(ml_data['high_risk_files'])}
Medium Risk Files: {len(ml_data['medium_risk_files'])}

Top Risky Files:
{self._format_modules(ml_data['modules'])}

Provide a comprehensive JSON analysis with:

1. overall_risk: 0-100 (based on the ML results)

2. files_analyzed: number of files

3. summary: Write a DETAILED 400+ word comprehensive analysis covering:
   - Overall security posture and code quality assessment
   - Detailed explanation of the risk score and what it means
   - Analysis of the codebase structure and patterns observed
   - Specific security vulnerabilities and their potential impact
   - Code quality issues and technical debt indicators
   - Comparison to industry best practices
   - Long-term maintenance and scalability concerns
   - Specific areas that need immediate attention
   - Positive aspects of the codebase (if any)
   - Overall recommendations for improvement strategy
   Make this summary comprehensive, detailed, and actionable. Use professional security analysis language.

4. critical_concerns: array of 5-10 most critical issues found with detailed descriptions

5. recommendations: array of 8-12 specific, actionable, step-by-step recommendations with implementation details

6. files: array of detailed analysis for each high-risk file with:
   - filename
   - risk_score: 0-100
   - vulnerabilities: specific security issues with CVE references if applicable
   - bugs: potential bugs with detailed explanations
   - code_smells: code quality issues with refactoring suggestions
   - suggestions: detailed step-by-step fix instructions
   - explanation: comprehensive description of risks and issues

Be extremely detailed, specific, and actionable. Focus on security, quality, and maintainability. Provide professional-grade analysis."""

        try:
            response = self._make_request_with_fallback(prompt)
            result = self._parse_response(response.text)
            
            # Ensure we have the right structure
            if 'files' not in result or not result['files']:
                result['files'] = self._generate_file_analysis(ml_data['modules'])
            
            # Ensure recommendations field exists (frontend expects this)
            if 'recommendations' not in result or not result['recommendations']:
                result['recommendations'] = result.get('suggestions', [])
            
            # Ensure critical_concerns exists
            if 'critical_concerns' not in result:
                result['critical_concerns'] = []
            
            # Ensure summary exists
            if 'summary' not in result:
                result['summary'] = f"Analysis of {ml_data['repository']} completed. Overall risk: {result.get('overall_risk', 0)}%"
            
            print("✅ Gemini AI analysis completed successfully")
            print(f"   - Recommendations: {len(result.get('recommendations', []))}")
            print(f"   - Critical Concerns: {len(result.get('critical_concerns', []))}")
            print(f"   - Files Analyzed: {result.get('files_analyzed', 0)}")
            return result
        except Exception as e:
            print(f"❌ Gemini AI analysis failed: {e}")
            raise Exception(f"Gemini AI analysis failed: {str(e)}. Only real Gemini analysis is supported.")
    
    def _format_modules(self, modules: list) -> str:
        """Format module data for the prompt"""
        formatted = []
        for i, module in enumerate(modules[:10], 1):
            issues_summary = ""
            if module.get('code_issues'):
                issue = module['code_issues'][0]
                issues_summary = f" - {issue['issues']} code issues found"
            
            formatted.append(
                f"{i}. {module['file']} (Risk: {module['risk_score']*100:.0f}%)\n"
                f"   Reason: {module['reason']}{issues_summary}"
            )
        return "\n".join(formatted)
    
    def _generate_file_analysis(self, modules: list) -> list:
        """Generate detailed file analysis from ML results"""
        files = []
        for module in modules[:5]:
            analysis = {
                "filename": module['file'],
                "risk_score": int(module['risk_score'] * 100),
                "vulnerabilities": [],
                "bugs": [],
                "code_smells": [],
                "suggestions": [],
                "explanation": module['reason']
            }
            
            # Extract issues from code_issues if available
            if module.get('code_issues'):
                for issue_group in module['code_issues']:
                    for issue in issue_group.get('detailed_issues', []):
                        if issue['severity'] in ['critical', 'high']:
                            analysis['vulnerabilities'].append(
                                f"{issue['type']}: {issue['message']}"
                            )
                        else:
                            analysis['code_smells'].append(
                                f"{issue['type']}: {issue['message']}"
                            )
                        analysis['suggestions'].append(issue['fix'])
            
            files.append(analysis)
        
        return files
    


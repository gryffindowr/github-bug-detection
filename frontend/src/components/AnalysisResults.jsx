import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FiAlertCircle, FiCheckCircle, FiCode, FiZap } from 'react-icons/fi';
import './AnalysisResults.css';

const AnalysisResults = ({ result, onClose }) => {
    const [activeTab, setActiveTab] = useState('output');

    const getRiskColor = (score) => {
        if (score >= 0.7) return '#da3633';
        if (score >= 0.4) return '#d29922';
        return '#238636';
    };

    const getRiskLevel = (score) => {
        if (score >= 0.7) return 'High';
        if (score >= 0.4) return 'Medium';
        return 'Low';
    };

    return (
        <motion.div
            className="analysis-results-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
        >
            <motion.div
                className="analysis-results-modal"
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="modal-header">
                    <h2>{result.repository_name}</h2>
                    <button onClick={onClose} className="close-btn">×</button>
                </div>

                <div className="tabs">
                    <button
                        className={activeTab === 'output' ? 'tab active' : 'tab'}
                        onClick={() => setActiveTab('output')}
                    >
                        <FiCode /> Output
                    </button>
                    {result.gemini_analysis && (
                        <button
                            className={activeTab === 'gemini' ? 'tab active' : 'tab'}
                            onClick={() => setActiveTab('gemini')}
                        >
                            <FiZap /> Gemini Analysis
                        </button>
                    )}
                </div>

                <div className="tab-content">
                    {activeTab === 'output' && (
                        <div className="output-tab">
                            <div className="overall-risk">
                                <h3>Overall Repository Risk</h3>
                                <div
                                    className="risk-score"
                                    style={{ color: getRiskColor(result.overall_repository_risk) }}
                                >
                                    {(result.overall_repository_risk * 100).toFixed(0)}%
                                    <span className="risk-level">
                                        {getRiskLevel(result.overall_repository_risk)}
                                    </span>
                                </div>
                            </div>

                            {result.metadata && (
                                <div className="metadata">
                                    <span>⭐ {result.metadata.stars || 0}</span>
                                    <span>🔱 {result.metadata.forks || 0}</span>
                                    <span>🔤 {result.metadata.language || 'N/A'}</span>
                                </div>
                            )}

                            <div className="modules-list">
                                <h3>Risky Files ({result.modules?.length || 0})</h3>
                                {result.modules?.map((module, index) => (
                                    <div key={index} className="module-card">
                                        <div className="module-header">
                                            <span className="file-name">{module.file}</span>
                                            <span
                                                className="module-risk"
                                                style={{ color: getRiskColor(module.risk_score) }}
                                            >
                                                {(module.risk_score * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <p className="module-reason">{module.reason}</p>

                                        {module.code_issues && module.code_issues.length > 0 && (
                                            <div className="code-issues">
                                                <h4>
                                                    <FiAlertCircle /> Code Issues ({module.code_issues[0].issues})
                                                </h4>
                                                {module.code_issues[0].detailed_issues?.map((issue, idx) => (
                                                    <div key={idx} className={`issue-item severity-${issue.severity}`}>
                                                        <div className="issue-header">
                                                            <span className="issue-type">{issue.type}</span>
                                                            <span className="issue-severity">{issue.severity}</span>
                                                        </div>
                                                        <p className="issue-message">{issue.message}</p>
                                                        {issue.code_snippet && (
                                                            <code className="code-snippet">{issue.code_snippet}</code>
                                                        )}
                                                        <p className="issue-fix">
                                                            <FiCheckCircle /> {issue.fix}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeTab === 'gemini' && result.gemini_analysis && (
                        <div className="gemini-tab">
                            <div className="gemini-overview">
                                <h3>🤖 AI Analysis Overview</h3>
                                <div className="gemini-risk">
                                    Overall Risk: {result.gemini_analysis.overall_risk || 0}%
                                </div>
                                <p>Files Analyzed: {result.gemini_analysis.files_analyzed || 0}</p>

                                {result.gemini_analysis.summary && (
                                    <div className="gemini-summary">
                                        <h4>Summary</h4>
                                        <p>{result.gemini_analysis.summary}</p>
                                    </div>
                                )}

                                {result.gemini_analysis.critical_concerns && result.gemini_analysis.critical_concerns.length > 0 && (
                                    <div className="gemini-section">
                                        <h5>⚠️ Critical Concerns</h5>
                                        <ul>
                                            {result.gemini_analysis.critical_concerns.map((concern, i) => (
                                                <li key={i}>
                                                    {typeof concern === 'string' ? concern : (
                                                        <>
                                                            {concern.issue && <strong>{concern.issue}: </strong>}
                                                            {concern.description || concern.title || JSON.stringify(concern)}
                                                        </>
                                                    )}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {result.gemini_analysis.recommendations && result.gemini_analysis.recommendations.length > 0 && (
                                    <div className="gemini-section">
                                        <h5>💡 Recommendations</h5>
                                        <ul>
                                            {result.gemini_analysis.recommendations.map((rec, i) => (
                                                <li key={i}>
                                                    {typeof rec === 'string' ? rec : (
                                                        <>
                                                            {rec.title && <strong>{rec.title}: </strong>}
                                                            {rec.description || rec.details || JSON.stringify(rec)}
                                                        </>
                                                    )}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {result.gemini_analysis.files && result.gemini_analysis.files.length > 0 ? (
                                result.gemini_analysis.files.map((file, index) => (
                                    <div key={index} className="gemini-file">
                                        <h4>{file.filename}</h4>
                                        <div className="gemini-score">
                                            Risk Score: {file.risk_score}%
                                        </div>

                                        {file.vulnerabilities?.length > 0 && (
                                            <div className="gemini-section">
                                                <h5>🔒 Vulnerabilities</h5>
                                                <ul>
                                                    {file.vulnerabilities.map((v, i) => (
                                                        <li key={i}>
                                                            {typeof v === 'string' ? v : (
                                                                <>
                                                                    {v.type && <strong>{v.type}: </strong>}
                                                                    {v.description || v.name || JSON.stringify(v)}
                                                                </>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {file.bugs?.length > 0 && (
                                            <div className="gemini-section">
                                                <h5>🐛 Potential Bugs</h5>
                                                <ul>
                                                    {file.bugs.map((b, i) => (
                                                        <li key={i}>
                                                            {typeof b === 'string' ? b : (
                                                                <>
                                                                    {b.description || b.explanation || JSON.stringify(b)}
                                                                </>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {file.code_smells?.length > 0 && (
                                            <div className="gemini-section">
                                                <h5>👃 Code Smells</h5>
                                                <ul>
                                                    {file.code_smells.map((s, i) => (
                                                        <li key={i}>
                                                            {typeof s === 'string' ? s : (
                                                                <>
                                                                    {s.name && <strong>{s.name}: </strong>}
                                                                    {s.description || s.explanation || JSON.stringify(s)}
                                                                </>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {file.suggestions?.length > 0 && (
                                            <div className="gemini-section">
                                                <h5>💡 Suggestions</h5>
                                                <ul>
                                                    {file.suggestions.map((s, i) => (
                                                        <li key={i}>
                                                            {typeof s === 'string' ? s : (
                                                                <>
                                                                    {s.title && <strong>{s.title}: </strong>}
                                                                    {s.description || s.details || JSON.stringify(s)}
                                                                </>
                                                            )}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {file.explanation && (
                                            <div className="gemini-explanation">
                                                <p>{file.explanation}</p>
                                            </div>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div className="gemini-overview">
                                    <p style={{ color: '#8b949e', textAlign: 'center', padding: '2rem' }}>
                                        Gemini AI analysis is not available. The enhanced analysis may have failed or no code was found to analyze.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </motion.div>
        </motion.div>
    );
};

export default AnalysisResults;

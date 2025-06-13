import React, { useState, useEffect } from 'react';
import './DiffViewer.css';

const DiffViewer = ({ 
    preview, 
    onApply, 
    onReject, 
    onClose,
    showActions = true 
}) => {
    const [activeTab, setActiveTab] = useState('diff');
    const [isApplying, setIsApplying] = useState(false);

    if (!preview) {
        return (
            <div className="diff-viewer">
                <div className="diff-viewer-header">
                    <h3>No Preview Available</h3>
                    <button onClick={onClose} className="close-btn">×</button>
                </div>
                <div className="diff-viewer-content">
                    <p>Select a file and prompt to generate a preview.</p>
                </div>
            </div>
        );
    }

    const handleApply = async () => {
        setIsApplying(true);
        try {
            await onApply(preview);
        } catch (error) {
            console.error('Failed to apply injection:', error);
        } finally {
            setIsApplying(false);
        }
    };

    const handleReject = () => {
        onReject(preview);
    };

    const renderDiff = () => {
        if (!preview.diff) {
            return <p>No changes detected.</p>;
        }

        const lines = preview.diff.split('\n');
        return (
            <div className="diff-content">
                {lines.map((line, index) => {
                    let className = 'diff-line';
                    if (line.startsWith('+') && !line.startsWith('+++')) {
                        className += ' addition';
                    } else if (line.startsWith('-') && !line.startsWith('---')) {
                        className += ' deletion';
                    } else if (line.startsWith('@@')) {
                        className += ' hunk';
                    } else if (line.startsWith('+++') || line.startsWith('---')) {
                        className += ' file-header';
                    }
                    
                    return (
                        <div key={index} className={className}>
                            <span className="line-number">{index + 1}</span>
                            <span className="line-content">{line}</span>
                        </div>
                    );
                })}
            </div>
        );
    };

    const renderSideBySide = () => {
        if (!preview.before || !preview.after) {
            return <p>Content not available for side-by-side view.</p>;
        }

        const beforeLines = preview.before.split('\n');
        const afterLines = preview.after.split('\n');

        return (
            <div className="side-by-side">
                <div className="side-panel">
                    <h4>Before</h4>
                    <div className="code-panel">
                        {beforeLines.map((line, index) => (
                            <div key={index} className="code-line">
                                <span className="line-number">{index + 1}</span>
                                <span className="line-content">{line}</span>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="side-panel">
                    <h4>After</h4>
                    <div className="code-panel">
                        {afterLines.map((line, index) => (
                            <div key={index} className="code-line">
                                <span className="line-number">{index + 1}</span>
                                <span className="line-content">{line}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    };

    const renderStats = () => {
        if (!preview.diff_stats) {
            return <p>No statistics available.</p>;
        }

        const { additions, deletions, total_changes } = preview.diff_stats;
        
        return (
            <div className="stats-panel">
                <div className="stat-item">
                    <span className="stat-label">Additions:</span>
                    <span className="stat-value addition">{additions}</span>
                </div>
                <div className="stat-item">
                    <span className="stat-label">Deletions:</span>
                    <span className="stat-value deletion">{deletions}</span>
                </div>
                <div className="stat-item">
                    <span className="stat-label">Total Changes:</span>
                    <span className="stat-value">{total_changes}</span>
                </div>
                <div className="stat-item">
                    <span className="stat-label">Has Changes:</span>
                    <span className="stat-value">{preview.has_changes ? 'Yes' : 'No'}</span>
                </div>
                {preview.with_context && (
                    <div className="stat-item">
                        <span className="stat-label">Context-Aware:</span>
                        <span className="stat-value">Yes</span>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="diff-viewer">
            <div className="diff-viewer-header">
                <div className="header-info">
                    <h3>{preview.filename}</h3>
                    <span className="filepath">{preview.filepath}</span>
                </div>
                <div className="header-actions">
                    {showActions && (
                        <>
                            <button 
                                onClick={handleApply}
                                disabled={isApplying || !preview.has_changes}
                                className="apply-btn"
                            >
                                {isApplying ? 'Applying...' : '✅ Apply'}
                            </button>
                            <button 
                                onClick={handleReject}
                                className="reject-btn"
                            >
                                ❌ Reject
                            </button>
                        </>
                    )}
                    <button onClick={onClose} className="close-btn">×</button>
                </div>
            </div>

            <div className="diff-viewer-tabs">
                <button 
                    className={activeTab === 'diff' ? 'active' : ''}
                    onClick={() => setActiveTab('diff')}
                >
                    Diff View
                </button>
                <button 
                    className={activeTab === 'side-by-side' ? 'active' : ''}
                    onClick={() => setActiveTab('side-by-side')}
                >
                    Side by Side
                </button>
                <button 
                    className={activeTab === 'stats' ? 'active' : ''}
                    onClick={() => setActiveTab('stats')}
                >
                    Statistics
                </button>
            </div>

            <div className="diff-viewer-content">
                {activeTab === 'diff' && renderDiff()}
                {activeTab === 'side-by-side' && renderSideBySide()}
                {activeTab === 'stats' && renderStats()}
            </div>

            {preview.error && (
                <div className="error-panel">
                    <h4>Error</h4>
                    <p>{preview.error}</p>
                </div>
            )}
        </div>
    );
};

export default DiffViewer; 
import React, { useState, useEffect } from 'react';
import './FileSelectDropdown.css';

const FileSelectDropdown = ({ 
    onFileSelect, 
    onPromptSelect,
    projectRoot = '.',
    fileExtensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css'],
    placeholder = "Select a file to preview..."
}) => {
    const [files, setFiles] = useState([]);
    const [prompts, setPrompts] = useState([]);
    const [selectedFile, setSelectedFile] = useState('');
    const [selectedPrompt, setSelectedPrompt] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showDropdown, setShowDropdown] = useState(false);

    useEffect(() => {
        loadFiles();
        loadPrompts();
    }, [projectRoot]);

    const loadFiles = async () => {
        try {
            setIsLoading(true);
            setError(null);
            
            // In a real implementation, this would call an API endpoint
            // For now, we'll simulate file discovery
            const response = await fetch('/api/files/discover', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    root: projectRoot,
                    extensions: fileExtensions
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to load files');
            }
            
            const data = await response.json();
            setFiles(data.files || []);
            
        } catch (err) {
            console.error('Failed to load files:', err);
            setError('Failed to load files. Please check the project root.');
            // Fallback to empty array
            setFiles([]);
        } finally {
            setIsLoading(false);
        }
    };

    const loadPrompts = async () => {
        try {
            // In a real implementation, this would call an API endpoint
            const response = await fetch('/api/prompts/list');
            
            if (response.ok) {
                const data = await response.json();
                setPrompts(data.prompts || []);
            } else {
                // Fallback to common prompt locations
                setPrompts([
                    'prompts/landing_page.txt',
                    'prompts/api_enhancement.txt',
                    'prompts/error_handling.txt',
                    'prompts/documentation.txt'
                ]);
            }
        } catch (err) {
            console.error('Failed to load prompts:', err);
            // Fallback prompts
            setPrompts([
                'prompts/landing_page.txt',
                'prompts/api_enhancement.txt',
                'prompts/error_handling.txt',
                'prompts/documentation.txt'
            ]);
        }
    };

    const handleFileSelect = (filePath) => {
        setSelectedFile(filePath);
        setShowDropdown(false);
        onFileSelect(filePath);
    };

    const handlePromptSelect = (promptPath) => {
        setSelectedPrompt(promptPath);
        onPromptSelect(promptPath);
    };

    const handleInputChange = (e) => {
        const value = e.target.value;
        setSelectedFile(value);
        setShowDropdown(true);
        
        // Filter files based on input
        if (value) {
            const filtered = files.filter(file => 
                file.toLowerCase().includes(value.toLowerCase())
            );
            // Update filtered files (in a real implementation, this would be state)
        }
    };

    const handleInputFocus = () => {
        setShowDropdown(true);
    };

    const handleInputBlur = () => {
        // Delay hiding dropdown to allow for clicks
        setTimeout(() => setShowDropdown(false), 200);
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const getFileIcon = (filename) => {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'py': '🐍',
            'js': '📜',
            'ts': '📘',
            'jsx': '⚛️',
            'tsx': '⚛️',
            'html': '🌐',
            'css': '🎨',
            'json': '📋',
            'md': '📝',
            'txt': '📄'
        };
        return icons[ext] || '📄';
    };

    return (
        <div className="file-select-container">
            <div className="select-group">
                <label className="select-label">File to Preview:</label>
                <div className="dropdown-container">
                    <input
                        type="text"
                        value={selectedFile}
                        onChange={handleInputChange}
                        onFocus={handleInputFocus}
                        onBlur={handleInputBlur}
                        placeholder={placeholder}
                        className="file-input"
                        disabled={isLoading}
                    />
                    {isLoading && <div className="loading-spinner">⏳</div>}
                    
                    {showDropdown && files.length > 0 && (
                        <div className="dropdown-menu">
                            {files.map((file, index) => (
                                <div
                                    key={index}
                                    className="dropdown-item"
                                    onClick={() => handleFileSelect(file)}
                                >
                                    <span className="file-icon">{getFileIcon(file)}</span>
                                    <span className="file-name">{file}</span>
                                    <span className="file-size">
                                        {formatFileSize(Math.random() * 10000)} {/* Mock size */}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="select-group">
                <label className="select-label">Prompt Template:</label>
                <select
                    value={selectedPrompt}
                    onChange={(e) => handlePromptSelect(e.target.value)}
                    className="prompt-select"
                >
                    <option value="">Select a prompt template...</option>
                    {prompts.map((prompt, index) => (
                        <option key={index} value={prompt}>
                            {prompt}
                        </option>
                    ))}
                </select>
            </div>

            {error && (
                <div className="error-message">
                    <span className="error-icon">⚠️</span>
                    {error}
                </div>
            )}

            {files.length === 0 && !isLoading && !error && (
                <div className="no-files-message">
                    <span className="no-files-icon">📁</span>
                    No files found in the project directory.
                </div>
            )}
        </div>
    );
};

export default FileSelectDropdown; 
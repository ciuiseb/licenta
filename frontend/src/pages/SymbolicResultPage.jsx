import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';

const SymbolicResultPage = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const formula = location.state?.formula;
    const result = location.state?.result;

    const handleBack = () => {
        navigate('/');
    };

    const exportSolution = () => {
        if (!result) return;
        const solutions = result.solutions || [];
        const lines = solutions.map((sol, i) =>
            `Solution ${i + 1}: ${sol.formula_str || '—'}`
        );
        const content = [
            `Equation: ${formula || '—'}`,
            `Order: ${result.order ?? '—'}`,
            `Variable: ${result.variable || '—'}`,
            `Constants: ${(result.constants || []).join(', ') || '—'}`,
            '',
            ...lines
        ].join('\n');

        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'symbolic_solution.txt';
        a.click();
        window.URL.revokeObjectURL(url);
    };

    if (!result) {
        return (
            <div className="visualization-page">
                <div className="visualization-page-header">
                    <button onClick={handleBack} className="btn btn-secondary btn-back">
                        ← Back to Configuration
                    </button>
                    <h2>Symbolic Solution</h2>
                    <div className="visualization-page-formula">—</div>
                </div>
                <div className="visualization-page-content">
                    <div className="visualization-container">
                        <div className="card visualization-card">
                            <div className="visualization-content" style={{ padding: '30px' }}>
                                <p style={{ color: 'var(--text-on-surface-secondary)' }}>No symbolic solution data found.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const solutions = result.solutions || [];
    const constants = result.constants || [];
    const hasMetadata = result.order !== undefined || result.variable || constants.length > 0;

    return (
        <div className="visualization-page">
            <div className="visualization-page-header">
                <button onClick={handleBack} className="btn btn-secondary btn-back">
                    ← Back to Configuration
                </button>
                <h2>Symbolic Solution</h2>
                <div className="visualization-page-formula">
                    {formula || "—"}
                </div>
            </div>

            <div className="visualization-page-content">
                <div className="visualization-container">
                    <div className="card visualization-card">
                        <div className="card-header">
                            <div className="training-status">
                                <div className="connection-status" style={{ color: 'var(--status-converged)' }}>
                                    <span className="status-dot" style={{ backgroundColor: 'var(--status-converged)' }}></span>
                                    Solved
                                </div>
                            </div>
                        </div>

                        <div className="visualization-content">
                            {/* Solutions section – styled like chart-container */}
                            <div className="chart-container">
                                <div className="chart-header">
                                    <h3>
                                        {solutions.length > 1
                                            ? `General Solutions (${solutions.length} branches)`
                                            : 'General Solution'}
                                    </h3>
                                    <div className="chart-actions">
                                        <button onClick={exportSolution} className="btn btn-small btn-secondary">
                                            Export Solution
                                        </button>
                                    </div>
                                </div>
                                <div style={{ padding: '24px 20px', background: 'var(--chart-wrapper-bg)' }}>
                                    {solutions.length === 0 && (
                                        <div className="formula-content" style={{ textAlign: 'center' }}>
                                            <span style={{ color: 'var(--text-on-surface-secondary)' }}>No solutions returned.</span>
                                        </div>
                                    )}
                                    {solutions.map((sol, idx) => (
                                        <div
                                            key={idx}
                                            style={{
                                                textAlign: 'center',
                                                padding: '16px',
                                                marginBottom: idx < solutions.length - 1 ? '12px' : 0,
                                                background: 'var(--surface-2)',
                                                borderRadius: '8px',
                                                border: '1px solid var(--border-dark)',
                                            }}
                                        >
                                            {solutions.length > 1 && (
                                                <span style={{
                                                    color: 'var(--text-on-surface-secondary)',
                                                    fontSize: '0.8rem',
                                                    display: 'block',
                                                    marginBottom: '8px',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '1px',
                                                    fontWeight: 600,
                                                }}>
                                                    Branch {idx + 1}
                                                </span>
                                            )}
                                            <span style={{ fontSize: '1.2rem', color: 'var(--text-on-surface-bright)' }}>
                                                {sol.latex ? (
                                                    (() => {
                                                        try {
                                                            return <InlineMath math={sol.latex} errorColor="#ef4444" />;
                                                        } catch {
                                                            return <span>{sol.formula_str}</span>;
                                                        }
                                                    })()
                                                ) : (
                                                    <span>{sol.formula_str || '—'}</span>
                                                )}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Metadata section – styled like metric cards */}
                            {hasMetadata && (
                                <div className="loss-metrics">
                                    {result.order !== undefined && (
                                        <div className="metric-card">
                                            <span className="metric-label">Order</span>
                                            <span className="metric-value">{result.order}</span>
                                        </div>
                                    )}
                                    {result.variable && (
                                        <div className="metric-card">
                                            <span className="metric-label">Variable</span>
                                            <span className="metric-value">{result.variable}</span>
                                        </div>
                                    )}
                                    {constants.length > 0 && (
                                        <div className="metric-card">
                                            <span className="metric-label">Integration Constants</span>
                                            <span className="metric-value">{constants.join(', ')}</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SymbolicResultPage;

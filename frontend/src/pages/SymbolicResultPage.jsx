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
                                <p style={{ color: '#9ca3af' }}>No symbolic solution data found.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const solutions = result.solutions || [];
    const constants = result.constants || [];

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
                                <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span className="status-dot" style={{ backgroundColor: '#10b981' }}></span>
                                    Solved
                                </span>
                            </div>
                        </div>

                        <div className="visualization-content">
                            <div className="formula-display">
                                <h3>
                                    {solutions.length > 1
                                        ? `General Solutions (${solutions.length} branches)`
                                        : 'General Solution'}
                                </h3>
                                {solutions.length === 0 && (
                                    <div className="formula-content">
                                        <span style={{ color: '#9ca3af' }}>No solutions returned.</span>
                                    </div>
                                )}
                                {solutions.map((sol, idx) => (
                                    <div key={idx} className="formula-content" style={solutions.length > 1 ? { marginBottom: '12px' } : {}}>
                                        {solutions.length > 1 && (
                                            <span style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>
                                                Branch {idx + 1}
                                            </span>
                                        )}
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
                                    </div>
                                ))}
                            </div>

                            <div className="formula-display" style={{ display: 'flex', gap: '40px', flexWrap: 'wrap', justifyContent: 'center' }}>
                                {result.order !== undefined && (
                                    <div>
                                        <h3>Order</h3>
                                        <div className="formula-content">
                                            <span>{result.order}</span>
                                        </div>
                                    </div>
                                )}
                                {result.variable && (
                                    <div>
                                        <h3>Variable</h3>
                                        <div className="formula-content">
                                            <span>{result.variable}</span>
                                        </div>
                                    </div>
                                )}
                                {constants.length > 0 && (
                                    <div>
                                        <h3>Integration Constants</h3>
                                        <div className="formula-content">
                                            <span>{constants.join(', ')}</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SymbolicResultPage;

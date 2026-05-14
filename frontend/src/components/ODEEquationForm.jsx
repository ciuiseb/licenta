import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import pinnAPI from '../services/pinnAPI';

const ODEEquationForm = () => {
    const navigate = useNavigate();
    const [formula, setFormula] = useState("y'' + y = 0");
    const [isSolving, setIsSolving] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    const handleSolve = async () => {
        if (!formula.trim()) {
            setError('Please enter a differential equation.');
            return;
        }
        setError(null);
        setResult(null);
        setIsSolving(true);
        try {
            const response = await pinnAPI.solveSymbolic(formula);
            if (response && response.success) {
                navigate('/symbolic', { state: { formula, result: response } });
            } else {
                setError(response?.error || 'Could not solve the equation symbolically.');
            }
        } catch (err) {
            setError(err?.message || 'Request failed.');
        } finally {
            setIsSolving(false);
        }
    };

    const handleReset = () => {
        setResult(null);
        setError(null);
    };

    return (
        <div className="solver-container">
            <div className="card form-card">
                <div className="card-header">
                    <h2>General Symbolic Solution</h2>
                </div>

                <form className="solver-form" onSubmit={(e) => { e.preventDefault(); handleSolve(); }}>
                    <div className="form-group">
                        <label>Ecuația Diferențială</label>
                        <input
                            type="text"
                            className="math-input"
                            value={formula}
                            onChange={(e) => { setFormula(e.target.value); setError(null); }}
                            placeholder="ex: y'' + y = 0"
                            disabled={isSolving}
                        />
                    </div>

                    <div className="form-actions">
                        <button
                            type="submit"
                            disabled={isSolving || !formula.trim()}
                            className={`btn btn-primary btn-block ${isSolving ? 'btn-loading' : ''}`}
                        >
                            <span className="btn-text">
                                {isSolving ? 'Solving...' : 'Solve Symbolically'}
                            </span>
                        </button>
                        {result && (
                            <button
                                type="button"
                                onClick={handleReset}
                                className="btn btn-secondary"
                                style={{ marginTop: '8px' }}
                            >
                                Clear
                            </button>
                        )}
                    </div>
                </form>

                {error && (
                    <div className="alert alert-error">
                        <div>{error}</div>
                    </div>
                )}

                {result && result.success && (
                    <div style={{ marginTop: '20px' }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '10px'
                        }}>
                            <h3 style={{ margin: 0 }}>
                                General Solution{result.solutions.length > 1 ? 's' : ''}
                            </h3>
                            <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                                Order {result.order}
                                {result.constants && result.constants.length > 0 && (
                                    <> &middot; Constants: {result.constants.join(', ')}</>
                                )}
                            </span>
                        </div>

                        {result.solutions.map((sol, idx) => (
                            <div
                                key={idx}
                                style={{
                                    padding: '12px 16px',
                                    backgroundColor: '#f9fafb',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '8px',
                                    marginBottom: '10px',
                                    overflowX: 'auto'
                                }}
                            >
                                {result.solutions.length > 1 && (
                                    <div style={{
                                        fontSize: '0.8rem',
                                        color: '#6b7280',
                                        marginBottom: '6px'
                                    }}>
                                        Branch {idx + 1}
                                    </div>
                                )}
                                <BlockMath math={sol.latex} />
                                <div style={{
                                    fontSize: '0.8rem',
                                    color: '#6b7280',
                                    marginTop: '8px',
                                    fontFamily: 'monospace',
                                    wordBreak: 'break-all'
                                }}>
                                    {sol.formula_str}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ODEEquationForm;

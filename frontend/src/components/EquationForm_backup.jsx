// src/components/EquationForm.jsx
import React, { useState } from 'react';
import 'katex/dist/katex.min.css';
import { BlockMath } from 'react-katex';
import RealTimeVisualization from './RealTimeVisualization';
import useRealTimeTraining from '../hooks/useRealTimeTraining';

const EquationForm = () => {
    const [formula, setFormula] = useState("y'' + y = 0");
    const [conditions, setConditions] = useState([{ t: 0, val: 1 }]);
    const [tMax, setTMax] = useState(10); // Acum e folosit
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    const handleConditionChange = (index, value) => {
        const newConditions = [...conditions];
        newConditions[index].val = parseFloat(value) || 0;
        setConditions(newConditions);
    };

    const addCondition = () => {
        setConditions([...conditions, { t: 0, val: 0 }]);
    };

    const removeCondition = () => {
        if (conditions.length > 1) {
            setConditions(conditions.slice(0, -1));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const payload = {
                formula: formula,
                conditions: conditions,
                tMax: parseFloat(tMax)
            };

            // Asigură-te că URL-ul e corect (fără /api/math/api/math...)
            const response = await fetch('http://127.0.0.1:5000/api/math/solve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                setResult(data);
            } else {
                setError(data.error || "Unknown error occurred");
            }

        } catch (err) {
            console.error("Eroare backend:", err); // Rezolvă eroarea de lint
            setError("Eroare de rețea. Este backend-ul pornit?");
        } finally {
            setLoading(false);
        }
    };

    const getLabel = (index) => {
        if (index === 0) return "y(0)";
        if (index === 1) return "y'(0)";
        return `y^(${index})(0)`;
    };

    return (
        <div className="solver-container">
            <div className="card form-card">
                <div className="card-header">
                    <h2>🧮 Configurare Ecuație</h2>
                </div>

                <form onSubmit={handleSubmit} className="solver-form">
                    {/* Input Ecuație */}
                    <div className="form-group">
                        <label>Ecuația Diferențială</label>
                        <input
                            type="text"
                            className="math-input"
                            value={formula}
                            onChange={(e) => setFormula(e.target.value)}
                            placeholder="ex: y'' + y = 0"
                        />
                    </div>

                    {/* Condiții Inițiale */}
                    <div className="form-group">
                        <label>Condiții Inițiale (Cauchy)</label>
                        <div className="conditions-grid">
                            {conditions.map((cond, index) => (
                                <div key={index} className="condition-row">
                                    <span className="latex-label">{getLabel(index)} = </span>
                                    <input
                                        type="number"
                                        className="number-input"
                                        value={cond.val}
                                        onChange={(e) => handleConditionChange(index, e.target.value)}
                                    />
                                </div>
                            ))}
                        </div>

                        <div className="action-buttons">
                            <button type="button" onClick={addCondition} className="btn btn-secondary">
                                + Adaugă Derivată
                            </button>
                            {conditions.length > 1 && (
                                <button type="button" onClick={removeCondition} className="btn btn-danger">
                                    Șterge
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Interval Timp (ASTA LIPSEA ÎNAINTE) */}
                    <div className="form-group">
                        <label>Interval de timp (tMax)</label>
                        <div className="time-input-wrapper">
                            <span>t ∈ [0, </span>
                            <input
                                type="number"
                                className="number-input"
                                value={tMax}
                                onChange={(e) => setTMax(e.target.value)}
                            />
                            <span>]</span>
                        </div>
                    </div>

                    <button type="submit" disabled={loading} className="btn btn-primary btn-block">
                        {loading ? <span className="spinner">⚙️ Se antrenează AI...</span> : "🚀 Rezolvă Ecuația"}
                    </button>
                </form>
            </div>

            {/* Rezultate */}
            {error && <div className="alert alert-error">{error}</div>}

            {result && (
                <div className="card result-card">
                    <div className="card-header success">
                        <h3>✅ Rezultat Calculat</h3>
                    </div>
                    <div className="result-content">
                        <div className="math-block">
                            <small>Ecuația interpretată:</small>
                            <BlockMath math={result.meta.latex} />
                        </div>

                        <div className="math-block">
                            <small>Soluția Exactă (Simbolică):</small>
                            {result.symbolic.latex ?
                                <BlockMath math={result.symbolic.latex} /> :
                                <p className="mono-text">{result.symbolic.formula_str}</p>
                            }
                        </div>

                        <div className="stats-grid">
                            <div className="stat-item">
                                <span className="stat-label">Ordin</span>
                                <span className="stat-value">{result.meta.order}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Puncte Numerice</span>
                                <span className="stat-value">{result.numerical?.data?.x?.length || 0}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Status AI</span>
                                <span className={`stat-value ${result.pinn?.success ? 'text-green' : 'text-red'}`}>
                                    {result.pinn?.success ? "Convergent" : "Eșuat"}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EquationForm;
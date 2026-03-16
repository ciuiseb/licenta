// src/components/EquationForm.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import 'katex/dist/katex.min.css';
import { BlockMath } from 'react-katex';

const getEquationOrder = (formula) => {
    const matches = formula.match(/y'+/g);
    if (!matches) return 0;
    return Math.max(...matches.map(m => m.length - 1));
};

const EquationForm = ({ trainingHook, parameters, setParameters, useFallback, setUseFallback, onParameterChange }) => {
    const navigate = useNavigate();
    const [formula, setFormula] = useState("y' + y = 0");
    const [conditions, setConditions] = useState([{ t: 0, val: '1' }]);
    const [tMax, setTMax] = useState(10);
    const [validationError, setValidationError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const {
        isTraining,
        error: trainingError,
        startTraining,
    } = trainingHook;

    const handleConditionChange = (index, value) => {
        const newConditions = [...conditions];
        newConditions[index].val = value;
        setConditions(newConditions);
    };

    const validateForm = () => {
        if (!formula.trim()) {
            return 'Please enter a differential equation.';
        }

        const order = getEquationOrder(formula);
        if (order === 0) {
            return 'Could not detect the order of the equation. Make sure it contains y\' or y\'\'.';
        }

        if (conditions.length < order) {
            return `This is a ${order}-order equation — it requires ${order} initial condition${order > 1 ? 's' : ''} (${Array.from({length: order}, (_, i) => i === 0 ? 'y(0)' : i === 1 ? "y'(0)" : `y${'\'' .repeat(i)}(0)`).join(', ')}), but only ${conditions.length} provided.`;
        }

        if (conditions.length > order) {
            return `This is a ${order}-order equation — it requires exactly ${order} initial condition${order > 1 ? 's' : ''}, but ${conditions.length} were provided. Remove ${conditions.length - order}.`;
        }

        const numberRegex = /^-?\d*\.?\d+$/;
        for (let i = 0; i < conditions.length; i++) {
            const val = conditions[i].val.trim();
            if (val === '' || !numberRegex.test(val)) {
                const label = i === 0 ? 'y(0)' : i === 1 ? "y'(0)" : `y${'\'' .repeat(i)}(0)`;
                return `Initial condition ${label} must be a valid number${val ? ` (got '${val}')` : ''}.`;
            }
        }

        const parsedTMax = parseFloat(tMax);
        if (isNaN(parsedTMax) || parsedTMax <= 0) {
            return 'tMax must be a positive number.';
        }

        return null;
    };

    const handleStartTraining = () => {
        const error = validateForm();
        if (error) {
            setValidationError(error);
            return;
        }
        setValidationError(null);

        const payload = {
            formula: formula,
            conditions: conditions.map(c => ({ t: c.t, val: parseFloat(c.val) || 0 })),
            tMax: parseFloat(tMax),
            parameters: {
                learning_rate: parameters.learningRate,
                hidden_layers: parameters.hiddenLayers,
                neurons_per_layer: parameters.neuronsPerLayer
            }
        };

        setParameters(prev => ({
            ...prev,
            formula,
            conditions: conditions.map(c => ({ t: c.t, val: parseFloat(c.val) || 0 })),
            tMax: parseFloat(tMax)
        }));

        setIsSubmitting(true);
        startTraining(payload);
    };

    // Safe Navigation Hook
    useEffect(() => {
        if (!isSubmitting) return;

        // If a backend error pops up, cancel the navigation
        if (trainingError) {
            setIsSubmitting(false);
            return;
        }

        // Give the backend a brief moment to return a Validation 400.
        // If the connection holds and no error appears, transition safely.
        let timer;
        if (isTraining) {
            timer = setTimeout(() => {
                navigate('/visualization');
                setIsSubmitting(false);
            }, 400);
        }

        return () => clearTimeout(timer);
    }, [isSubmitting, isTraining, trainingError, navigate]);

    const addCondition = () => {
        setValidationError(null);
        setConditions([...conditions, { t: 0, val: '' }]);
    };

    const removeCondition = () => {
        if (conditions.length > 1) {
            setConditions(conditions.slice(0, -1));
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
                    <h2>Configurare Ecuație</h2>
                </div>

                <form className="solver-form">
                    {/* Input Ecuație */}
                    <div className="form-group">
                        <label>Ecuația Diferențială</label>
                        <input
                            type="text"
                            className="math-input"
                            value={formula}
                            onChange={(e) => { setFormula(e.target.value); setValidationError(null); }}
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
                                        type="text"
                                        inputMode="decimal"
                                        className="number-input"
                                        value={cond.val}
                                        onChange={(e) => handleConditionChange(index, e.target.value)}
                                        placeholder="0"
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

                    {/* Interval Timp */}
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

                    <div className="form-actions">
                        <div className="fallback-toggle">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={useFallback}
                                    onChange={(e) => setUseFallback(e.target.checked)}
                                    disabled={isTraining}
                                />
                                Use Fallback Mode (Simulation)
                            </label>
                        </div>

                        <button
                            type="button"
                            onClick={handleStartTraining}
                            disabled={isTraining || !formula}
                            className={`btn btn-primary btn-block ${isTraining ? 'btn-loading' : ''}`}
                        >
                            <span className="btn-text">
                                {isTraining ? "Training AI..." : "Start Real-Time Training"}
                            </span>
                        </button>
                    </div>
                </form>
            </div>

            {/* Validation Error */}
            {validationError && (
                <div className="alert alert-error">
                    <div>{validationError}</div>
                </div>
            )}

            {/* Training Error */}
            {trainingError && (
                <div className="alert alert-error">
                    <div>{trainingError}</div>
                    {trainingError.includes('SSE streaming not implemented') && (
                        <div style={{ marginTop: '10px', fontSize: '0.9rem' }}>
                            <strong>Solution:</strong> Enable "Use Fallback Mode" below to test the interface with simulation, or implement the SSE streaming method in your backend.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default EquationForm;
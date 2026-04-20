import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const getEquationInfo = (formula) => {
    const match = formula.match(/\b([a-zA-Z])'+/);
    const varName = match ? match[1] : 'y';

    const primeRegex = new RegExp(`\\b${varName}'+`, 'g');
    const primeMatches = formula.match(primeRegex);
    const order = primeMatches ? Math.max(...primeMatches.map(m => m.length - varName.length)) : 0;

    return { varName, order };
};

const getDerivativeLabel = (index, varName) => {
    if (index === 0) return varName;
    if (index === 1) return `${varName}'`;
    if (index === 2) return `${varName}''`;
    if (index === 3) return `${varName}'''`;
    return `${varName}^(${index})`;
};

const BVPEquationForm = ({ trainingHook, parameters, setParameters, useFallback, setUseFallback, onParameterChange }) => {
    const navigate = useNavigate();
    const [formula, setFormula] = useState("y'' + y = 0");
    const [conditions, setConditions] = useState([
        { t: '0', order: '0', val: '1' },
        { t: '10', order: '0', val: '0' }
    ]);
    const [tMax, setTMax] = useState(10);
    const [validationError, setValidationError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const {
        isTraining,
        error: trainingError,
        startTraining,
    } = trainingHook;

    const handleConditionChange = (index, field, value) => {
        const newConditions = [...conditions];
        newConditions[index][field] = value;
        setConditions(newConditions);
        setValidationError(null);
    };

    const validateForm = () => {
        if (!formula.trim()) {
            return 'Please enter a differential equation.';
        }

        const { varName, order } = getEquationInfo(formula);

        const standaloneLetters = formula.match(/\b[a-zA-Z]\b/g) || [];
        const invalidVars = standaloneLetters.filter(letter =>
            letter !== varName &&
            letter !== 't' &&
            letter !== 'e'
        );

        if (invalidVars.length > 0) {
            const uniqueInvalid = [...new Set(invalidVars)];
            return `Inconsistent variables detected: ${uniqueInvalid.join(', ')}. Please use only '${varName}' as the dependent variable and 't' as time.`;
        }

        if (order < 2) {
            return 'A Boundary Value Problem (BVP) typically requires an equation of order 2 or higher.';
        }

        if (conditions.length !== order) {
            return `This is a ${order}-order equation — it requires exactly ${order} boundary conditions, but ${conditions.length} were provided.`;
        }

        const numberRegex = /^-?\d*\.?\d+$/;
        for (let i = 0; i < conditions.length; i++) {
            const { t, val } = conditions[i];

            if (String(t).trim() === '' || !numberRegex.test(String(t))) {
                return `Condition ${i + 1}: Evaluation point 't' must be a valid number.`;
            }
            if (String(val).trim() === '' || !numberRegex.test(String(val))) {
                return `Condition ${i + 1}: The condition value must be a valid number.`;
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

        const formattedConditions = conditions.map(c => ({
            t: parseFloat(c.t),
            val: parseFloat(c.val),
            order: parseInt(c.order, 10)
        }));

        const payload = {
            formula: formula,
            conditions: formattedConditions,
            equation_type: "bvp",
            tMax: parseFloat(tMax),
            parameters: {
                learning_rate: parameters.learningRate,
                hidden_layers: parameters.hiddenLayers,
                neurons_per_layer: parameters.neuronsPerLayer,
                tolerance: Math.pow(10, -(parameters.toleranceExponent ?? 5))
            }
        };

        setParameters(prev => ({
            ...prev,
            formula,
            conditions: formattedConditions,
            equation_type: 'bvp',
            tMax: parseFloat(tMax)
        }));

        setIsSubmitting(true);
        startTraining(payload);
    };

    useEffect(() => {
        if (!isSubmitting) return;

        if (trainingError) {
            setTimeout(() => setIsSubmitting(false), 0);
            return;
        }

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

        setConditions([...conditions, { t: '10', order: '1', val: '0' }]);
    };

    const removeCondition = () => {
        if (conditions.length > 1) {
            setConditions(conditions.slice(0, -1));
        }
    };

    const { varName, order } = getEquationInfo(formula);
    const maxDerivativeOrder = Math.max(0, order - 1);
    return (
        <div className="card form-card">
            <div className="card-header">
                <h2>Configurare Ecuație (BVP)</h2>
            </div>

            <form className="solver-form">
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

                <div className="form-group">
                    <label>Condiții la Limită (Boundary Conditions)</label>

                    <div className="conditions-grid">
                        {conditions.map((cond, index) => (
                            <div key={index} className="condition-row" style={{ marginBottom: '10px' }}>
                                <select
                                    className="latex-label"
                                    value={cond.order}
                                    onChange={(e) => handleConditionChange(index, 'order', e.target.value)}
                                    style={{
                                        backgroundColor: '#ffffff',
                                        color: '#333333',
                                        border: '1px solid #d1d5db',
                                        borderRadius: '8px',
                                        padding: '3px 5px',
                                        cursor: 'pointer',
                                        textAlign: 'center',
                                    }}
                                >
                                    {Array.from({ length: maxDerivativeOrder + 1 }).map((_, i) => (
                                        <option key={i} value={i}>
                                            {getDerivativeLabel(i, varName)}
                                        </option>
                                    ))}
                                </select>

                                <span className="latex-label">(</span>

                                <input
                                    type="text"
                                    inputMode="decimal"
                                    className="number-input"
                                    value={cond.t}
                                    onChange={(e) => handleConditionChange(index, 't', e.target.value)}
                                    placeholder="t"
                                />

                                <span className="latex-label">) = </span>

                                <input
                                    type="text"
                                    inputMode="decimal"
                                    className="number-input"
                                    value={cond.val}
                                    onChange={(e) => handleConditionChange(index, 'val', e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                        ))}
                    </div>

                    <div className="action-buttons">
                        <button type="button" onClick={addCondition} className="btn btn-secondary">
                            + Adaugă Punct
                        </button>
                        {conditions.length > 1 && (
                            <button type="button" onClick={removeCondition} className="btn btn-danger">
                                Șterge
                            </button>
                        )}
                    </div>
                </div>

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

                <div className="form-group">
                    <label>
                        Target Precision: 1e-{parameters?.toleranceExponent ?? 5}
                        {' '}
                        <small style={{color: '#6b7280', fontWeight: 'normal'}}>
                            ({(parameters?.toleranceExponent ?? 5) <= 3 ? 'fast' :
                              (parameters?.toleranceExponent ?? 5) <= 5 ? 'balanced' : 'high precision'})
                        </small>
                    </label>
                    <input
                        type="range"
                        min="2"
                        max="8"
                        step="1"
                        value={parameters?.toleranceExponent ?? 5}
                        onChange={(e) => onParameterChange && onParameterChange('toleranceExponent', parseInt(e.target.value))}
                        disabled={isTraining}
                        style={{width: '100%'}}
                    />
                    <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6b7280', marginTop: '4px'}}>
                        <span>fast (1e-2)</span>
                        <span>high precision (1e-8)</span>
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
                            {isTraining ? "Training AI..." : "Start Training"}
                        </span>
                    </button>
                </div>
            </form>

            {validationError && (
                <div className="alert alert-error">
                    <div>{validationError}</div>
                </div>
            )}

            {trainingError && (
                <div className="alert alert-error">
                    <div>{trainingError}</div>
                </div>
            )}
        </div>
    );
};

export default BVPEquationForm;
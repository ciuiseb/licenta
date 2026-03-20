import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import 'katex/dist/katex.min.css';
import { BlockMath } from 'react-katex';

const getEquationInfo = (formula) => {
    const match = formula.match(/\b([a-zA-Z])'+/);
    const varName = match ? match[1] : 'y';

    const primeRegex = new RegExp(`\\b${varName}'+`, 'g');
    const primeMatches = formula.match(primeRegex);
    const order = primeMatches ? Math.max(...primeMatches.map(m => m.length - varName.length)) : 0;

    return { varName, order };
};

const IVPEquationForm = ({ trainingHook, parameters, setParameters, useFallback, setUseFallback }) => {
    const navigate = useNavigate();
    const [formula, setFormula] = useState("y' + y = 0");
    const [conditions, setConditions] = useState([{ val: '1' }]);
    const [initialTime, setInitialTime] = useState(0);
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
    };

    const handleInitialTimeChange = (value) => {
        setInitialTime(value);
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

        if (order === 0) {
            return 'Could not detect the order of the equation. Make sure it contains derivatives like f\' or x\'\'.';
        }

        if (conditions.length < order) {
            return `This is a ${order}-order equation — it requires ${order} initial condition${order > 1 ? 's' : ''} (${Array.from({length: order}, (_, i) => i === 0 ? `${varName}(0)` : i === 1 ? `${varName}'(0)` : `${varName}${'\'' .repeat(i)}(0)`).join(', ')}), but only ${conditions.length} provided.`;
        }

        if (conditions.length > order) {
            return `This is a ${order}-order equation — it requires exactly ${order} initial condition${order > 1 ? 's' : ''}, but ${conditions.length} were provided. Remove ${conditions.length - order}.`;
        }

        const numberRegex = /^-?\d*\.?\d+$/;
        for (let i = 0; i < conditions.length; i++) {
            const val = String(conditions[i].val).trim();
            if (val === '' || !numberRegex.test(val)) {
                const label = i === 0 ? `${varName}` : i === 1 ? `${varName}'` : `${varName}^(${i})`;
                return `Initial condition ${label} must be a valid number${val ? ` (got '${val}')` : ''}.`;
            }
        }

        const parsedInitialTime = parseFloat(initialTime);
        if (isNaN(parsedInitialTime)) {
            return 'Initial time must be a valid number.';
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
            conditions: conditions.map(c => ({ t: parseFloat(initialTime), val: parseFloat(c.val) || 0 })),
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
            conditions: conditions.map(c => ({ t: parseFloat(initialTime), val: parseFloat(c.val) || 0 })),
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
        setConditions([...conditions, { val: '' }]);
    };

    const removeCondition = () => {
        if (conditions.length > 1) {
            setConditions(conditions.slice(0, -1));
        }
    };

    const getLabel = (index, varName) => {
        if (index === 0) return `${varName}`;
        if (index === 1) return `${varName}'`;
        // if (index === 2) return `${varName}''`;
        // if (index === 3) return `${varName}'''`;
        return `${varName}<sup>(${index})</sup>`;
    };

    const { varName } = getEquationInfo(formula);

    return (
        <div className="solver-container">
            <div className="card form-card">
                <div className="card-header">
                    <h2>Configurare Ecuație</h2>
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
                        <label>Condiții Inițiale</label>
                        
                        <div className="form-group" style={{ marginBottom: '15px' }}>
                            <label style={{ fontSize: '0.9rem', fontWeight: 'normal' }}>Initial point t = </label>
                            <input
                                type="text"
                                inputMode="decimal"
                                className="number-input"
                                value={initialTime}
                                onChange={(e) => handleInitialTimeChange(e.target.value)}
                                placeholder="0"
                                style={{ width: '80px', marginLeft: '10px' }}
                            />
                        </div>
                        
                        <div className="conditions-grid">
                            {conditions.map((cond, index) => (
                                <div key={index} className="condition-row">
                                    <span className="latex-label" dangerouslySetInnerHTML={{ __html: getLabel(index, varName) + '(' + initialTime + ')' }}></span>
                                    <span className="latex-label"> = </span>
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
                                + Adaugă Derivată
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
            </div>

            {validationError && (
                <div className="alert alert-error">
                    <div>{validationError}</div>
                </div>
            )}

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

export default IVPEquationForm;
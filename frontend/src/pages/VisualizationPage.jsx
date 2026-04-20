import React from 'react';
import { useNavigate } from 'react-router-dom';
import RealTimeVisualization from '../components/RealTimeVisualization';

const VisualizationPage = ({ trainingHook, parameters, onParameterChange }) => {
    const navigate = useNavigate();

    const {
        isTraining,
        trainingData,
        numericalData,
        symbolicData,
        modelId,
        lossData,
        progress,
        connectionStatus,
        trainingStats,
        startTraining,
        stopTraining,
        reset
    } = trainingHook;

    const handleReset = () => {
        reset();
        navigate('/');
    };

    const handleToggleTraining = () => {
        if (isTraining) {
            stopTraining();
        } else {
            startTraining({
                formula: parameters.formula,
                conditions: parameters.conditions || [{ t: 0, val: 1 }],
                equation_type: parameters.equation_type || 'ivp',
                tMax: parameters.tMax || 10,
                parameters: {
                    learning_rate: parameters.learningRate,
                    hidden_layers: parameters.hiddenLayers,
                    neurons_per_layer: parameters.neuronsPerLayer,
                    tolerance: Math.pow(10, -(parameters.toleranceExponent ?? 5))
                }
            });
        }
    };

    return (
        <div className="visualization-page">
            <div className="visualization-page-header">
                <button onClick={handleReset} className="btn btn-secondary btn-back">
                    ← Back to Configuration
                </button>
                <h2>Real-Time PINN Training</h2>
                <div className="visualization-page-formula">
                    {parameters.formula || "—"}
                    {parameters.conditions && parameters.conditions.length > 0 && (
                        <div className="visualization-page-conditions">
                            {parameters.conditions.map((cond, index) => {
                                const getLabel = (index, varName = 'y') => {
                                    if (index === 0) return `${varName}`;
                                    if (index === 1) return `${varName}'`;
                                    if (index === 2) return `${varName}''`;
                                    if (index === 3) return `${varName}'''`;
                                    return `${varName}<sup>(${index})</sup>`;
                                };
                                const varName = parameters.formula?.match(/\b([a-zA-Z])'+/)?.[1] || 'y';
                                return (
                                    <span key={index} className="condition-item">
                                        <span dangerouslySetInnerHTML={{ __html: getLabel(index, varName) + '(' }}></span>
                                        {cond.t}) = {cond.val}
                                    </span>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            <div className="visualization-page-content">
                <RealTimeVisualization
                    isTraining={isTraining}
                    trainingData={trainingData}
                    numericalData={numericalData}
                    symbolicData={symbolicData}
                    modelId={modelId}
                    lossData={lossData}
                    progress={progress}
                    connectionStatus={connectionStatus}
                    trainingStats={trainingStats}
                    onToggleTraining={handleToggleTraining}
                    onReset={handleReset}
                    onParameterChange={onParameterChange}
                    parameters={parameters}
                />
            </div>
        </div>
    );
};

export default VisualizationPage;

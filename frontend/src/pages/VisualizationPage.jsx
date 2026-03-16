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
            // If restarting, use saved parameters from original training
            startTraining({
                formula: parameters.formula,
                conditions: parameters.conditions || [{ t: 0, val: 1 }],
                tMax: parameters.tMax || 10,
                parameters: {
                    learning_rate: parameters.learningRate,
                    hidden_layers: parameters.hiddenLayers,
                    neurons_per_layer: parameters.neuronsPerLayer
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
                </div>
            </div>

            <div className="visualization-page-content">
                <RealTimeVisualization
                    isTraining={isTraining}
                    trainingData={trainingData}
                    numericalData={numericalData}
                    symbolicData={symbolicData}
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

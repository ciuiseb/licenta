import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import EquationForm from './components/EquationForm';
import VisualizationPage from './pages/VisualizationPage';
import useRealTimeTraining from './hooks/useRealTimeTraining';
import useFallbackTraining from './hooks/useFallbackTraining';
import './App.css';

function App() {
    const [useFallback, setUseFallback] = useState(false);
    const [parameters, setParameters] = useState({
        learningRate: 0.001,
        hiddenLayers: 3,
        neuronsPerLayer: 20,
        formula: "y'' + y = 0"
    });

    const fallbackTrainingHook = useFallbackTraining();
    const realTimeTrainingHook = useRealTimeTraining();
    const trainingHook = useFallback ? fallbackTrainingHook : realTimeTrainingHook;

    const handleParameterChange = (param, value) => {
        setParameters(prev => ({ ...prev, [param]: value }));
    };

    return (
        <div className="app-container">
            <main>
                <Routes>
                    <Route path="/" element={
                        <EquationForm
                            trainingHook={trainingHook}
                            parameters={parameters}
                            setParameters={setParameters}
                            useFallback={useFallback}
                            setUseFallback={setUseFallback}
                            onParameterChange={handleParameterChange}
                        />
                    } />
                    <Route path="/visualization" element={
                        <VisualizationPage
                            trainingHook={trainingHook}
                            parameters={parameters}
                            onParameterChange={handleParameterChange}
                        />
                    } />
                </Routes>
            </main>
        </div>
    );
}

export default App;
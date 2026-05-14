import React, {useState, useEffect} from 'react';
import {Route, Routes} from 'react-router-dom';
import VisualizationPage from './pages/VisualizationPage';
import SymbolicResultPage from './pages/SymbolicResultPage';
import useRealTimeTraining from './hooks/useRealTimeTraining';
import useFallbackTraining from './hooks/useFallbackTraining';
import PasscodeModal from './components/PasscodeModal';
import authService from './services/authService';
import './App.css';

import SetupPage from './components/SetupPage';

function App() {
    const [authenticated, setAuthenticated] = useState(false);
    const [checkingAuth, setCheckingAuth] = useState(true);
    const [useFallback, setUseFallback] = useState(false);
    const [parameters, setParameters] = useState({
        toleranceExponent: 5,
        formula: "y'' + y = 0"
    });

    useEffect(() => {
        const checkAuth = async () => {
            const isAuth = await authService.checkStatus();
            setAuthenticated(isAuth);
            setCheckingAuth(false);
        };
        checkAuth();
    }, []);

    const handleAuthenticate = async (passcode) => {
        const result = await authService.login(passcode);
        if (result.success) {
            setAuthenticated(true);
        }
        return result;
    };

    const handleLogout = async () => {
        await authService.logout();
        setAuthenticated(false);
    };

    const fallbackTrainingHook = useFallbackTraining();
    const realTimeTrainingHook = useRealTimeTraining();
    const trainingHook = useFallback ? fallbackTrainingHook : realTimeTrainingHook;

    const handleParameterChange = (param, value) => {
        setParameters(prev => ({...prev, [param]: value}));
    };

    if (checkingAuth) {
        return (
            <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
                <div>Checking authentication...</div>
            </div>
        );
    }

    return (
        <div className="app-container">
            {!authenticated && <PasscodeModal onAuthenticate={handleAuthenticate} />}
            {authenticated && (
                <button
                    onClick={handleLogout}
                    className="logout-button"
                    title="Logout"
                >
                    Logout
                </button>
            )}
            <main>
                <Routes>
                    <Route path="/" element={
                        <SetupPage
                            trainingHook={trainingHook}
                            parameters={parameters}
                            setParameters={setParameters}
                            useFallback={useFallback}
                            setUseFallback={setUseFallback}
                            onParameterChange={handleParameterChange}
                        />
                    }/>
                    <Route path="/visualization" element={
                        <VisualizationPage
                            trainingHook={trainingHook}
                            parameters={parameters}
                            onParameterChange={handleParameterChange}
                        />
                    }/>
                    <Route path="/symbolic" element={
                        <SymbolicResultPage />
                    }/>
                </Routes>
            </main>
        </div>
    );
}

export default App;
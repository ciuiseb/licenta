import React, {useState, useEffect} from 'react';
import {Route, Routes} from 'react-router-dom';
import VisualizationPage from './pages/VisualizationPage';
import SymbolicResultPage from './pages/SymbolicResultPage';
import useRealTimeTraining from './hooks/useRealTimeTraining';
import useFallbackTraining from './hooks/useFallbackTraining';
import PasscodeModal from './components/PasscodeModal';
import authService from './services/authService';
import {useTheme} from './context/ThemeContext';
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

    const {theme, toggleTheme} = useTheme();

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
            <button
                onClick={toggleTheme}
                className="theme-toggle"
                title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
                {theme === 'dark' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
                    </svg>
                ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
                    </svg>
                )}
            </button>
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
import React, { useState } from 'react';
import IVPEquationForm from './IVPEquationForm';
import BVPEquationForm from "./BVPEquationForm.jsx";
import ODEEquationForm from './ODEEquationForm';

const SetupPage = (props) => {
    const [activeTab, setActiveTab] = useState('ivp');

    return (
        <div className="setup-page-wrapper">
            <div style={{ display: 'flex', justifyContent: 'center', gap: '15px', marginBottom: '20px' }}>
                <button
                    className={`btn ${activeTab === 'ivp' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('ivp')}
                    style={{ minWidth: '150px' }}
                >
                    Initial Value Problem
                </button>
                <button
                    className={`btn ${activeTab === 'bvp' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('bvp')}
                    style={{ minWidth: '150px' }}
                >
                    Boundary Value Problem
                </button>
                <button
                    className={`btn ${activeTab === 'ode' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('ode')}
                    style={{ minWidth: '150px' }}
                >
                    Ordinary Differential Equation
                </button>
            </div>

            <div className="active-form-container">
                {activeTab === 'ivp' ? (
                    <IVPEquationForm {...props} />
                ) : activeTab === 'bvp' ? (
                    <BVPEquationForm {...props} />
                ) : (
                    <ODEEquationForm />
                )}
            </div>
        </div>
    );
};

export default SetupPage;
import React, { useState } from 'react';
import IVPEquationForm from './IVPEquationForm';

const BVPEquationFormPlaceholder = () => {
    return (
        <div className="card form-card" style={{ textAlign: 'center', padding: '40px 20px' }}>
            <h2>Configurare Ecuație (BVP)</h2>
            <p style={{ marginTop: '20px', color: '#666' }}>
                Boundary Value Problem shall come
            </p>
        </div>
    );
};

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
            </div>

            <div className="active-form-container">
                {activeTab === 'ivp' ? (
                    <IVPEquationForm {...props} />
                ) : (
                    <BVPEquationFormPlaceholder {...props} />
                )}
            </div>
        </div>
    );
};

export default SetupPage;
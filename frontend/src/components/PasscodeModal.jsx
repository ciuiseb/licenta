import React, { useState } from 'react';
import './PasscodeModal.css';

const PasscodeModal = ({ onAuthenticate }) => {
  const [passcode, setPasscode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!passcode.trim()) {
      setError('Please enter a passcode');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await onAuthenticate(passcode);
      
      if (!result.success) {
        setError(result.error || 'Invalid passcode');
        setPasscode('');
      }
    } catch (err) {
      setError('Authentication failed. Please try again.');
      setPasscode('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="passcode-modal-overlay">
      <div className="passcode-modal">
        <div className="passcode-modal-header">
          <h2>Authentication Required</h2>
          <p>Please enter the passcode to access the application</p>
        </div>
        
        <form onSubmit={handleSubmit} className="passcode-form">
          <div className="passcode-input-group">
            <input
              type="password"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
              placeholder="Enter passcode"
              className={`passcode-input ${error ? 'error' : ''}`}
              disabled={loading}
              autoFocus
            />
            {error && <div className="passcode-error">{error}</div>}
          </div>
          
          <button 
            type="submit" 
            className="passcode-submit"
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Enter'}
          </button>
        </form>
        
        <div className="passcode-footer">
          <small>Contact the administrator if you need access</small>
        </div>
      </div>
    </div>
  );
};

export default PasscodeModal;

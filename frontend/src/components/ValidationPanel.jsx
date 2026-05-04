import React from 'react';
import './ValidationPanel.css';

const ValidationPanel = ({ validation, toleranceExponent }) => {
    if (!validation) return null;

    const { symbolic, numerical, losses } = validation;

    const formatScientific = (num) => {
        if (num === undefined || num === null) return 'N/A';
        if (num < 1e-10) return '< 1e-10';
        return num.toExponential(2);
    };

    const getQualityBadge = (accuracy) => {
        if (accuracy >= 99.9) return { label: 'Excellent', color: '#10b981' };
        if (accuracy >= 99.0) return { label: 'Very Good', color: '#34d399' };
        if (accuracy >= 95.0) return { label: 'Good', color: '#fbbf24' };
        if (accuracy >= 85.0) return { label: 'Fair', color: '#f59e0b' };
        return { label: 'Poor', color: '#ef4444' };
    };

    const renderMetricRow = (label, metrics) => {
        if (!metrics) {
            return (
                <div className="metric-row unavailable">
                    <span className="metric-label">{label}:</span>
                    <span className="metric-value-na">Not available</span>
                </div>
            );
        }

        const badge = getQualityBadge(metrics.accuracy_percent);
        
        return (
            <div className="metric-row">
                <div className="metric-header">
                    <span className="metric-label">{label}:</span>
                    <div className="accuracy-display">
                        <span className="accuracy-percent">{metrics.accuracy_percent.toFixed(2)}%</span>
                        <span className="quality-badge" style={{ backgroundColor: badge.color }}>
                            {badge.label}
                        </span>
                    </div>
                </div>
                <div className="metric-details">
                    <span>Max deviation: {formatScientific(metrics.linf_error)}</span>
                    <span>L² error: {formatScientific(metrics.l2_error)}</span>
                </div>
            </div>
        );
    };

    return (
        <div className="validation-panel">
            <div className="validation-header">
                <h3>Validation Report</h3>
            </div>
            
            <div className="validation-content">
                {renderMetricRow('Accuracy vs. Symbolic', symbolic)}
                {renderMetricRow('Accuracy vs. Numerical', numerical)}

                {(!symbolic && !numerical) && (
                    <div className="no-reference-note">
                        <span className="info-icon">ℹ️</span>
                        <span>No reference solutions available for comparison</span>
                    </div>
                )}

                {losses && (
                    <div className="losses-section">
                        <div className="loss-item">
                            <span className="loss-label">Physics residual:</span>
                            <span className="loss-value">{formatScientific(losses.physics_residual)}</span>
                        </div>
                        <div className="loss-item">
                            <span className="loss-label">Boundary error:</span>
                            <span className="loss-value">{formatScientific(losses.boundary_error)}</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ValidationPanel;

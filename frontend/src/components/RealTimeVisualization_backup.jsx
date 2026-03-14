import React, { useState, useEffect, useRef } from 'react';
import Plot from 'react-plotly.js';

const RealTimeVisualization = ({ 
  isTraining, 
  trainingData, 
  lossData, 
  progress,
  onToggleTraining,
  onReset,
  onParameterChange,
  parameters
}) => {
  const [plotData, setPlotData] = useState({
    x: [],
    y: [],
    target: []
  });
  
  const plotRef = useRef(null);

  // Update plot data when training data changes
  useEffect(() => {
    if (trainingData && trainingData.function_data) {
      setPlotData({
        x: trainingData.function_data.x || [],
        y: trainingData.function_data.y || [],
        target: trainingData.target_data?.y || []
      });
    }
  }, [trainingData]);

  // Plotly configuration for dark theme
  const plotLayout = {
    autosize: true,
    height: 400,
    paper_bgcolor: '#1e1e2e',
    plot_bgcolor: '#2d2d44',
    font: {
      color: '#ffffff',
      family: 'Inter, sans-serif'
    },
    xaxis: {
      title: 'Time (t)',
      gridcolor: '#404040',
      zerolinecolor: '#606060',
      color: '#ffffff'
    },
    yaxis: {
      title: 'y(t)',
      gridcolor: '#404040',
      zerolinecolor: '#606060',
      color: '#ffffff'
    },
    margin: {
      l: 50,
      r: 30,
      t: 30,
      b: 50
    },
    showlegend: true,
    legend: {
      x: 0.02,
      y: 0.98,
      bgcolor: 'rgba(45, 45, 68, 0.8)',
      bordercolor: '#404040',
      borderwidth: 1
    }
  };

  const plotConfig = {
    responsive: true,
    displayModeBar: false,
    staticPlot: false
  };

  const plotTraces = [
    {
      x: plotData.x,
      y: plotData.y,
      type: 'scatter',
      mode: 'lines',
      name: 'PINN Approximation',
      line: {
        color: '#3b82f6',
        width: 3
      },
      opacity: isTraining ? 0.8 : 1.0
    }
  ];

  // Add target solution if available
  if (plotData.target.length > 0) {
    plotTraces.push({
      x: plotData.x,
      y: plotData.target,
      type: 'scatter',
      mode: 'lines',
      name: 'Target Solution',
      line: {
        color: '#ef4444',
        width: 2,
        dash: 'dash'
      },
      opacity: 0.7
    });
  }

  return (
    <div className="visualization-container">
      <div className="card visualization-card">
        <div className="card-header">
          <h2>📊 Real-Time PINN Training</h2>
          <div className="training-status">
            {isTraining ? (
              <span className="status-indicator status-training">
                <span className="status-dot"></span>
                Training...
              </span>
            ) : progress?.completed ? (
              <span className="status-indicator status-converged">
                <span className="status-dot"></span>
                AI Converged ✓
              </span>
            ) : (
              <span className="status-indicator status-idle">
                <span className="status-dot"></span>
                Ready
              </span>
            )}
          </div>
        </div>

        <div className="visualization-content">
          {/* Progress Bar */}
          {isTraining && (
            <div className="progress-section">
              <div className="progress-info">
                <span>Epoch: {progress?.current || 0} / {progress?.total || 1000}</span>
                <span>{Math.round((progress?.current || 0) / (progress?.total || 1000) * 100)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${(progress?.current || 0) / (progress?.total || 1000) * 100}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Main Plot */}
          <div className="plot-container" ref={plotRef}>
            <Plot
              data={plotTraces}
              layout={plotLayout}
              config={plotConfig}
              style={{ width: '100%', height: '100%' }}
            />
          </div>

          {/* Loss Metrics */}
          {lossData && (
            <div className="loss-metrics">
              <div className="metric-card">
                <div className="metric-label">Physics Loss</div>
                <div className="metric-value">{lossData.physics?.toExponential(2) || 'N/A'}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Boundary Loss</div>
                <div className="metric-value">{lossData.boundary?.toExponential(2) || 'N/A'}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Total Loss</div>
                <div className="metric-value">{lossData.total?.toExponential(2) || 'N/A'}</div>
              </div>
            </div>
          )}

          {/* Training Controls */}
          <div className="training-controls">
            <button
              onClick={onToggleTraining}
              className={`btn ${isTraining ? 'btn-danger' : 'btn-primary'}`}
              disabled={!parameters?.formula}
            >
              {isTraining ? '⏹️ Stop Training' : '🚀 Start Training'}
            </button>
            
            <button
              onClick={onReset}
              className="btn btn-secondary"
              disabled={isTraining}
            >
              🔄 Reset
            </button>
          </div>

          {/* Parameter Controls */}
          <div className="parameter-controls">
            <div className="param-group">
              <label>Learning Rate</label>
              <input
                type="range"
                min="0.0001"
                max="0.01"
                step="0.0001"
                value={parameters?.learningRate || 0.001}
                onChange={(e) => onParameterChange('learningRate', parseFloat(e.target.value))}
                disabled={isTraining}
              />
              <span>{parameters?.learningRate || 0.001}</span>
            </div>

            <div className="param-group">
              <label>Hidden Layers</label>
              <select
                value={parameters?.hiddenLayers || 3}
                onChange={(e) => onParameterChange('hiddenLayers', parseInt(e.target.value))}
                disabled={isTraining}
              >
                <option value={2}>2 Layers</option>
                <option value={3}>3 Layers</option>
                <option value={4}>4 Layers</option>
                <option value={5}>5 Layers</option>
              </select>
            </div>

            <div className="param-group">
              <label>Neurons per Layer</label>
              <select
                value={parameters?.neuronsPerLayer || 20}
                onChange={(e) => onParameterChange('neuronsPerLayer', parseInt(e.target.value))}
                disabled={isTraining}
              >
                <option value={10}>10 Neurons</option>
                <option value={20}>20 Neurons</option>
                <option value={30}>30 Neurons</option>
                <option value={50}>50 Neurons</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RealTimeVisualization;

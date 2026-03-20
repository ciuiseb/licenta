import React, {useEffect, useMemo, useRef, useState} from 'react';
import {
    CategoryScale,
    Chart as ChartJS,
    Filler,
    Legend,
    LinearScale,
    LineElement,
    PointElement,
    Title,
    Tooltip
} from 'chart.js';
import {Line} from 'react-chartjs-2';
import {InlineMath} from 'react-katex';
import 'katex/dist/katex.min.css';
import zoomPlugin from 'chartjs-plugin-zoom';
import pinnAPI from '../services/pinnAPI';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    zoomPlugin
);

const RealTimeVisualization = ({
                                   isTraining,
                                   trainingData,
                                   numericalData,
                                   symbolicData,
                                   progress,
                                   connectionStatus,
                                   onToggleTraining,
                                   onReset,
                                   onParameterChange,
                                   parameters
                               }) => {
    const chartRef = useRef(null);
    const [historicalData, setHistoricalData] = useState([]);
    const [currentEpoch, setCurrentEpoch] = useState(0);
    const updateTimeoutRef = useRef(null);

    const [yBounds, setYBounds] = useState({min: -1, max: 1});

    const [evalPoint, setEvalPoint] = useState('');
    const [evalResult, setEvalResult] = useState(null);
    const [evalError, setEvalError] = useState(null);
    const [isEvaluating, setIsEvaluating] = useState(false);

    const [chartData, setChartData] = useState({
        labels: [],
        datasets: []
    });

    useEffect(() => {
        const datasets = [];
        let allYValues = [];

        if (numericalData && numericalData.success && numericalData.data) {
            const {x, y} = numericalData.data;
            allYValues = allYValues.concat(y);
            datasets.push({
                label: 'Numerical Solution',
                data: y.map((val, idx) => ({x: x[idx], y: val})),
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1,
                fill: false,
                borderDash: [5, 5]
            });
        }

        if (symbolicData && symbolicData.success && symbolicData.data) {
            const {x, y} = symbolicData.data;
            allYValues = allYValues.concat(y);
            datasets.push({
                label: 'Symbolic Solution',
                data: y.map((val, idx) => ({x: x[idx], y: val})),
                borderColor: 'rgb(34, 197, 94)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1,
                fill: false
            });
        }

        if (trainingData && trainingData.function_data) {
            const {x, y} = trainingData.function_data;
            allYValues = allYValues.concat(y);

            if (progress.current !== currentEpoch) {
                setCurrentEpoch(progress.current);

                setHistoricalData(prev => {
                    const newHistory = [...prev, {epoch: progress.current, x, y}];
                    return newHistory.slice(-5);
                });
            }

            datasets.push({
                label: `PINN Solution${progress.current > 0 ? ` (Epoch ${progress.current})` : ''}`,
                data: y.map((val, idx) => ({x: x[idx], y: val})),
                borderColor: 'rgb(251, 146, 60)',
                backgroundColor: 'rgba(251, 146, 60, 0.1)',
                borderWidth: 3,
                pointRadius: 0,
                tension: 0.1,
                fill: false
            });
        }

        if (allYValues.length > 0) {
            const minY = Math.min(...allYValues);
            const maxY = Math.max(...allYValues);
            const padding = (maxY - minY) * 0.1 || 1;
            setYBounds({
                min: minY - padding,
                max: maxY + padding
            });
        }

        if (updateTimeoutRef.current) {
            clearTimeout(updateTimeoutRef.current);
        }

        const updateChart = () => {
            setChartData({
                labels: trainingData?.function_data?.x || numericalData?.data?.x || symbolicData?.data?.x || [],
                datasets: datasets
            });
        };

        if (isTraining && trainingData) {
            updateTimeoutRef.current = setTimeout(updateChart, 100);
        } else {
            updateChart();
        }

        return () => {
            if (updateTimeoutRef.current) {
                clearTimeout(updateTimeoutRef.current);
            }
        };
    }, [trainingData, numericalData, symbolicData, isTraining, progress.current, currentEpoch]);

    useEffect(() => {
        if (!isTraining && progress.current === 0) {
            setHistoricalData([]);
            setCurrentEpoch(0);
        }
    }, [isTraining, progress.current]);

    const chartOptions = useMemo(() => {
        const xMin = parameters?.t_min || 0;
        const xMax = parameters?.t_max || 10;

        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: isTraining ? false : {
                duration: 750,
                easing: 'easeInOutQuart'
            },
            transitions: {
                active: {
                    animation: {
                        duration: 0
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'nearest',
                axis: 'x'
            },
            scales: {
                x: {
                    type: 'linear',
                    min: xMin,
                    max: xMax,
                    title: {
                        display: true,
                        text: 'Time (t)',
                        color: '#e5e7eb'
                    },
                    grid: {
                        color: '#374151',
                        borderColor: '#4b5563'
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                y: {
                    min: yBounds.min,
                    max: yBounds.max,
                    title: {
                        display: true,
                        text: 'Solution y(t)',
                        color: '#e5e7eb'
                    },
                    grid: {
                        color: '#374151',
                        borderColor: '#4b5563'
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#e5e7eb',
                        font: {
                            size: 12
                        },
                        usePointStyle: true,
                        padding: 20
                    },
                    onClick: (e, legendItem, legend) => {
                        const index = legendItem.datasetIndex;
                        const chart = legend.chart;
                        const meta = chart.getDatasetMeta(index);
                        
                        meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                        chart.update();
                    }
                },
                tooltip: {
                    backgroundColor: '#1f2937',
                    titleColor: '#e5e7eb',
                    bodyColor: '#9ca3af',
                    borderColor: '#4b5563',
                    borderWidth: 1,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function (context) {
                            return `t = ${context[0].parsed.x.toFixed(3)}`;
                        },
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += `y = ${context.parsed.y.toFixed(6)}`;
                            return label;
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                            speed: 0.1
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'xy',
                    },
                    pan: {
                        enabled: true,
                        mode: 'xy',
                    },
                    limits: {
                        y: {min: yBounds.min, max: yBounds.max}
                    }
                }
            }
        };
    }, [isTraining, progress.current, progress.total, parameters, yBounds]);

    const getConnectionStatusColor = () => {
        switch (connectionStatus) {
            case 'connected':
                return '#10b981';
            case 'connecting':
                return '#f59e0b';
            case 'error':
                return '#ef4444';
            default:
                return '#6b7280';
        }
    };

    const getConnectionStatusText = () => {
        switch (connectionStatus) {
            case 'connected':
                return 'Connected';
            case 'connecting':
                return 'Connecting...';
            case 'error':
                return 'Connection Error';
            default:
                return 'Disconnected';
        }
    };

    const exportData = () => {
        if (!trainingData) return;

        const {x, y} = trainingData.function_data;
        const csvContent = "t,y(t)\n" + x.map((t, i) => `${t},${y[i]}`).join("\n");

        const blob = new Blob([csvContent], {type: 'text/csv'});
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'pinn_solution.csv';
        a.click();
        window.URL.revokeObjectURL(url);
    };

    const exportChart = () => {
        if (chartRef.current) {
            const url = chartRef.current.toBase64Image();
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pinn_graph.png';
            a.click();
        }
    };

    const resetZoom = () => {
        if (chartRef.current) {
            chartRef.current.resetZoom();
        }
    };

    return (
        <div className="visualization-container">
            <div className="card visualization-card">
                <div className="card-header">
                    <h2>Real-Time PINN Training</h2>
                    <div className="training-status">
                        <div className="connection-status" style={{color: getConnectionStatusColor()}}>
                            <span className="status-dot" style={{backgroundColor: getConnectionStatusColor()}}></span>
                            {getConnectionStatusText()}
                        </div>
                        {isTraining && (
                            <span className="status-indicator status-training">
                <span className="status-dot"></span>
                Training...
              </span>
                        )}
                        {progress.completed && (
                            <span className="status-indicator status-converged">
                <span className="status-dot"></span>
                AI Converged ✓
              </span>
                        )}
                    </div>
                </div>

                <div className="visualization-content">
                    <div className="progress-section">
                        <div className="progress-bar">
                            <div
                                className="progress-fill"
                                style={{width: `${(progress.current / progress.total) * 100}%`}}
                            ></div>
                        </div>
                        {isTraining && (
                            <div className="graph-building-indicator">
                                <span className="building-text">Graph building with epoch {progress.current}...</span>
                            </div>
                        )}
                    </div>


                    <div className="chart-container">
                        <div className="chart-header">
                            <h3>PINN Solution</h3>
                            {trainingData && (
                                <div className="chart-actions">
                                    <button onClick={resetZoom} className="btn btn-small btn-secondary">
                                        Reset Zoom
                                    </button>
                                    <button onClick={exportChart} className="btn btn-small btn-secondary">
                                        Export Graph
                                    </button>
                                    <button onClick={exportData} className="btn btn-small btn-secondary">
                                        Export Data
                                    </button>
                                </div>
                            )}
                        </div>
                        <div className="chart-wrapper" style={{height: '400px'}}>
                            <Line ref={chartRef} data={chartData} options={chartOptions}/>
                        </div>
                    </div>

                    {symbolicData && symbolicData.success && (() => {
                        try {
                            return (
                                <div className="formula-display">
                                    <h3>Symbolic Solution</h3>
                                    <div className="formula-content">
                                        {symbolicData.latex ? (
                                            <InlineMath math={symbolicData.latex} errorColor="#ef4444" />
                                        ) : (
                                            <span>{symbolicData.formula_str}</span>
                                        )}
                                    </div>
                                </div>
                            );
                        } catch (error) {
                            console.error('Formula display error:', error);
                            return (
                                <div className="formula-display">
                                    <h3>Symbolic Solution</h3>
                                    <div className="formula-content">
                                        <span>{symbolicData.formula_str}</span>
                                    </div>
                                </div>
                            );
                        }
                    })()}

                    
                    <div className="training-controls">
                        <button
                            onClick={onToggleTraining}
                            className={`btn ${isTraining ? 'btn-danger' : 'btn-primary'}`}
                            disabled={!parameters?.formula || connectionStatus === 'connecting'}
                        >
                            {isTraining ? 'Stop Training' : 'Start Training'}
                        </button>

                        <button
                            onClick={onReset}
                            className="btn btn-secondary"
                            disabled={isTraining}
                        >
                            Reset
                        </button>
                    </div>

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

                    {progress.completed && (
                        <div className="point-evaluation">
                            <h3>Evaluate at Point</h3>
                            <p style={{color: '#9ca3af', fontSize: '0.9rem', marginBottom: '15px'}}>
                                Enter a value of t to instantly evaluate y(t) using the trained model.
                            </p>
                            <div className="eval-input-group">
                                <input
                                    type="text"
                                    inputMode="decimal"
                                    className="eval-input"
                                    placeholder="Enter t value (e.g., 5.5)"
                                    value={evalPoint}
                                    onChange={(e) => setEvalPoint(e.target.value)}
                                    disabled={isEvaluating}
                                />
                                <button
                                    onClick={async () => {
                                        if (!evalPoint.trim()) return;

                                        const numberRegex = /^-?\d*\.?\d+$/;
                                        if (!numberRegex.test(evalPoint.trim())) {
                                            setEvalError('Please enter a valid number');
                                            setEvalResult(null);
                                            return;
                                        }

                                        setIsEvaluating(true);
                                        setEvalError(null);
                                        setEvalResult(null);

                                        try {
                                            const result = await pinnAPI.evaluatePoint(parseFloat(evalPoint));
                                            setEvalResult(result);
                                        } catch (error) {
                                            setEvalError(error.message || 'Failed to evaluate point');
                                        } finally {
                                            setIsEvaluating(false);
                                        }
                                    }}
                                    className="btn btn-primary"
                                    disabled={isEvaluating || !evalPoint.trim()}
                                >
                                    {isEvaluating ? 'Evaluating...' : 'Evaluate'}
                                </button>
                            </div>

                            {evalResult && (
                                <div className="eval-result">
                                    <strong>Result:</strong> y({evalResult.t}) = <span
                                    className="result-value">{evalResult.y.toFixed(6)}</span>
                                </div>
                            )}

                            {evalError && (
                                <div className="eval-error">
                                    {evalError}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RealTimeVisualization;

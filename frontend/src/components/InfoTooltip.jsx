import React, { useState } from 'react';

const InfoTooltip = ({ content, title }) => {
    const [visible, setVisible] = useState(false);

    return (
        <span
            style={{ position: 'relative', display: 'inline-block', marginLeft: '6px' }}
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
            onFocus={() => setVisible(true)}
            onBlur={() => setVisible(false)}
        >
            <span
                tabIndex={0}
                role="button"
                aria-label="More information"
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--border-color)',
                    color: 'var(--text-main)',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    cursor: 'help',
                    userSelect: 'none',
                    lineHeight: 1,
                }}
            >
                i
            </span>
            {visible && (
                <span
                    role="tooltip"
                    style={{
                        position: 'absolute',
                        bottom: 'calc(100% + 8px)',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        zIndex: 1000,
                        width: '280px',
                        maxWidth: '90vw',
                        backgroundColor: 'var(--tooltip-bg)',
                        color: 'var(--tooltip-text)',
                        padding: '10px 12px',
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
                        fontSize: '0.8rem',
                        fontWeight: 'normal',
                        lineHeight: 1.45,
                        textAlign: 'left',
                        whiteSpace: 'normal',
                        pointerEvents: 'none',
                    }}
                >
                    {title && (
                        <div style={{ fontWeight: 'bold', marginBottom: '4px', color: 'var(--tooltip-text)' }}>
                            {title}
                        </div>
                    )}
                    <div>{content}</div>
                    <span
                        style={{
                            position: 'absolute',
                            top: '100%',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            width: 0,
                            height: 0,
                            borderLeft: '6px solid transparent',
                            borderRight: '6px solid transparent',
                            borderTop: '6px solid var(--tooltip-bg)',
                        }}
                    />
                </span>
            )}
        </span>
    );
};

export default InfoTooltip;

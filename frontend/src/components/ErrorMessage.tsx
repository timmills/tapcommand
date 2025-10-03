import React from 'react';

interface ErrorMessageProps {
  message: string;
  onDismiss?: () => void;
  onRetry?: () => void;
  className?: string;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  onDismiss,
  onRetry,
  className = ''
}) => {
  return (
    <div className={`error-message ${className}`}>
      <div className="error-content">
        <span className="error-icon">⚠️</span>
        <span className="error-text">{message}</span>
        <div className="error-actions">
          {onRetry && (
            <button className="button secondary" onClick={onRetry}>
              Retry
            </button>
          )}
          {onDismiss && (
            <button className="error-dismiss" onClick={onDismiss}>
              ✕
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ErrorMessage;
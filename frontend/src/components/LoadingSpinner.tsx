import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  text?: string;
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  text = 'Loading...',
  className = ''
}) => {
  const sizeClasses = {
    small: 'loading-spinner-small',
    medium: 'loading-spinner-medium',
    large: 'loading-spinner-large',
  };

  return (
    <div className={`loading-spinner ${sizeClasses[size]} ${className}`}>
      <div className="spinner"></div>
      {text && <div className="loading-text">{text}</div>}
    </div>
  );
};

export default LoadingSpinner;
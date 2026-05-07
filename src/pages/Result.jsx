import React, { useEffect, useState } from 'react';
import ResultCard from '../components/kiosk/ResultCard';

const Result = ({ value, onReset, isDevMode }) => {
  const [countdown, setCountdown] = useState(10);
  const isPass = value < 50; // Threshold example: 50 mg%

  useEffect(() => {
    if (isDevMode) return;

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          onReset();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [onReset, isDevMode]);

  return (
    <ResultCard 
      isPass={isPass} 
      value={value} 
      countdown={countdown} 
      onReset={onReset}
      isDevMode={isDevMode} 
    />
  );
};

export default Result;

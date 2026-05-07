import React, { useEffect, useState } from 'react';
import ResultCard from '../components/kiosk/ResultCard';

const Result = ({ value, onReset }) => {
  const [countdown, setCountdown] = useState(10);
  const isPass = value < 50; // Threshold example: 50 mg%

  useEffect(() => {
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
  }, [onReset]);

  return (
    <ResultCard 
      isPass={isPass} 
      value={value} 
      countdown={countdown} 
      onReset={onReset} 
    />
  );
};

export default Result;

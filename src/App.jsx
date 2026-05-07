import React, { useState } from 'react';
import FullscreenLayout from './layouts/FullscreenLayout';
import Home from './pages/Home';
import EnterID from './pages/EnterID';
import AlcoholTest from './pages/AlcoholTest';
import Result from './pages/Result';

function App() {
  const [currentStep, setCurrentStep] = useState('home'); // home, id_entry, testing, result
  const [employeeId, setEmployeeId] = useState('');
  const [testResult, setTestResult] = useState(0);

  const handleStart = () => {
    setCurrentStep('id_entry');
  };

  const handleConfirmID = (id) => {
    setEmployeeId(id);
    setCurrentStep('testing');
  };

  const handleTestComplete = (value) => {
    setTestResult(value);
    setCurrentStep('result');
  };

  const handleReset = () => {
    setEmployeeId('');
    setTestResult(0);
    setCurrentStep('home');
  };

  return (
    <FullscreenLayout>
      {currentStep === 'home' && (
        <Home onStart={handleStart} />
      )}
      
      {currentStep === 'id_entry' && (
        <EnterID onConfirm={handleConfirmID} />
      )}
      
      {currentStep === 'testing' && (
        <AlcoholTest onComplete={handleTestComplete} />
      )}
      
      {currentStep === 'result' && (
        <Result value={testResult} onReset={handleReset} />
      )}
    </FullscreenLayout>
  );
}

export default App;

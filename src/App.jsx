import React, { useState } from 'react';
import FullscreenLayout from './layouts/FullscreenLayout';
import Home from './pages/Home';
import EnterID from './pages/EnterID';
import AlcoholTest from './pages/AlcoholTest';
import Result from './pages/Result';
import DevOverlay from './components/kiosk/DevOverlay';
import { WebSocketProvider } from './context/WebSocketContext';

const isDevMode = import.meta.env.VITE_APP_MODE === 'dev';

function App() {
  const [currentStep, setCurrentStep] = useState('home'); // home, id_entry, testing, result
  const [employeeId, setEmployeeId] = useState('');
  const [testResult, setTestResult] = useState(0);
  const [devControls, setDevControls] = useState(null);

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

  const handleDevNavigate = (step) => {
    if (isDevMode) {
      setCurrentStep(step);
      // Ensure we have some mockup data if skipping directly to test/result
      if (step === 'testing' && !employeeId) setEmployeeId('12345678');
      if (step === 'result' && testResult === 0) setTestResult(25); // Mock a pass result
    }
  };

  return (
    <WebSocketProvider isDevMode={isDevMode}>
      <FullscreenLayout>
        {isDevMode && (
          <DevOverlay currentStep={currentStep} onNavigate={handleDevNavigate} extraControls={devControls} />
        )}

        {currentStep === 'home' && (
          <Home onStart={handleStart} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}
        
        {currentStep === 'id_entry' && (
          <EnterID onConfirm={handleConfirmID} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}
        
        {currentStep === 'testing' && (
          <AlcoholTest onComplete={handleTestComplete} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}
        
        {currentStep === 'result' && (
          <Result value={testResult} onReset={handleReset} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}
      </FullscreenLayout>
    </WebSocketProvider>
  );
}

export default App;

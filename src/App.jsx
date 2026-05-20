import React, { useState } from 'react';
import FullscreenLayout from './layouts/FullscreenLayout';
import Home from './pages/Home';
import ScanFingerprint from './pages/ScanFingerprint';
import AlcoholTest from './pages/AlcoholTest';
import Result from './pages/Result';
import RegisterFingerprint from './pages/RegisterFingerprint';
import DevOverlay from './components/kiosk/DevOverlay';
import { WebSocketProvider } from './context/WebSocketContext';

const isDevMode = import.meta.env.VITE_APP_MODE === 'dev';

function App() {
  const [currentStep, setCurrentStep] = useState('home'); // home, fingerprint_scan, testing, result, register_input_id, register_fingerprint
  const [employee, setEmployee] = useState(null);
  const [testResult, setTestResult] = useState({ value: 0, image: null });
  const [devControls, setDevControls] = useState(null);

  const handleStart = () => {
    setCurrentStep('fingerprint_scan');
  };

  const handleConfirmEmployee = (empData) => {
    setEmployee(empData);
    setCurrentStep('testing');
  };

  const handleTestComplete = (value, image = null) => {
    setTestResult({ value, image });
    setCurrentStep('result');
  };

  const handleReset = () => {
    setEmployee(null);
    setTestResult({ value: 0, image: null });
    setCurrentStep('home');
  };

  const handleDevNavigate = (step) => {
    if (isDevMode) {
      setCurrentStep(step);
      // Ensure we have some mockup data if skipping directly to test/result
      if (step === 'testing' && !employee) {
        setEmployee({ id: 1, name: 'สมชาย รักดี', emp_id: 'IDDE00001' });
      }
      if (step === 'result' && testResult.value === 0) setTestResult({ value: 25, image: null }); // Mock a pass result
    }
  };

  return (
    <WebSocketProvider isDevMode={isDevMode}>
      <FullscreenLayout>
        {isDevMode && (
          <DevOverlay currentStep={currentStep} onNavigate={handleDevNavigate} extraControls={devControls} />
        )}

        {currentStep === 'home' && (
          <Home 
            onStart={handleStart} 
            onRegister={() => setCurrentStep('register_input_id')}
            isDevMode={isDevMode} 
            setDevControls={setDevControls} 
          />
        )}
        
        {currentStep === 'fingerprint_scan' && (
          <ScanFingerprint onConfirm={handleConfirmEmployee} onCancel={handleReset} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}
        
        {currentStep === 'testing' && (
          <AlcoholTest employee={employee} onComplete={handleTestComplete} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}
        
        {currentStep === 'result' && (
          <Result value={testResult.value} image={testResult.image} onReset={handleReset} isDevMode={isDevMode} setDevControls={setDevControls} />
        )}

        {(currentStep === 'register_input_id' || currentStep === 'register_fingerprint') && (
          <RegisterFingerprint 
            currentStep={currentStep}
            setCurrentStep={setCurrentStep}
            onCancel={handleReset}
            isDevMode={isDevMode}
            setDevControls={setDevControls}
          />
        )}
      </FullscreenLayout>
    </WebSocketProvider>
  );
}

export default App;

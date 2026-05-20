import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const steps = ['home', 'fingerprint_scan', 'testing', 'result'];

const DevOverlay = ({ currentStep, onNavigate, extraControls }) => {
  const currentIndex = steps.indexOf(currentStep);

  const handlePrev = () => {
    if (currentIndex > 0) {
      onNavigate(steps[currentIndex - 1]);
    }
  };

  const handleNext = () => {
    if (currentIndex < steps.length - 1) {
      onNavigate(steps[currentIndex + 1]);
    }
  };

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] bg-slate-900/90 text-white px-6 py-3 rounded-full flex items-center space-x-6 backdrop-blur-md shadow-2xl border border-slate-700">
      <div className="text-sm font-mono font-bold text-amber-400 uppercase tracking-wider flex-shrink-0">Dev Mode</div>
      
      {extraControls && (
        <>
          <div className="w-px h-6 bg-slate-700" />
          <div className="flex items-center space-x-2">
            {extraControls}
          </div>
        </>
      )}

      <div className="w-px h-6 bg-slate-700" />
      
      <div className="flex items-center space-x-4">
        <button 
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className="p-2 hover:bg-white/20 rounded-full disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
        >
          <ChevronLeft size={20} />
        </button>
        
        <div className="text-sm font-medium min-w-[80px] text-center capitalize">
          {currentStep.replace('_', ' ')}
        </div>
        
        <button 
          onClick={handleNext}
          disabled={currentIndex === steps.length - 1}
          className="p-2 hover:bg-white/20 rounded-full disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
        >
          <ChevronRight size={20} />
        </button>
      </div>
    </div>
  );
};

export default DevOverlay;

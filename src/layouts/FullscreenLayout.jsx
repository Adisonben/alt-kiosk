import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const FullscreenLayout = ({ children }) => {
  return (
    <div className="fixed inset-0 bg-slate-50 flex flex-col items-center justify-center overflow-hidden p-6">
      {/* Background Decor */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      
      <main className="relative w-full max-w-4xl h-full flex flex-col items-center justify-center">
        <AnimatePresence mode="wait">
          {children}
        </AnimatePresence>
      </main>
      
      {/* Footer / Status Bar (Optional) */}
      <div className="absolute bottom-6 left-0 right-0 flex justify-center items-center gap-4 text-slate-400 text-sm font-medium">
        <span>© 2024 ALT Alcohol Test System</span>
        <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
        <span>System Ready</span>
      </div>
    </div>
  );
};

export default FullscreenLayout;

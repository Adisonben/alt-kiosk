import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wind, RefreshCcw } from 'lucide-react';
import StatusCircle from '../components/kiosk/StatusCircle';
import ProgressIndicator from '../components/kiosk/ProgressIndicator';

const AlcoholTest = ({ onComplete }) => {
  const [status, setStatus] = useState('waiting'); // waiting, detecting, success, retry
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let interval;
    if (status === 'detecting') {
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setTimeout(() => setStatus('success'), 500);
            return 100;
          }
          return prev + 2;
        });
      }, 50);
    }
    return () => clearInterval(interval);
  }, [status]);

  useEffect(() => {
    if (status === 'success') {
      const timer = setTimeout(() => {
        onComplete(Math.random() * 50); // Simulate random alcohol value
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [status, onComplete]);

  const startTest = () => {
    setStatus('detecting');
    setProgress(0);
  };

  const getStatusText = () => {
    switch (status) {
      case 'waiting': return 'กรุณาเริ่มเป่า';
      case 'detecting': return 'กำลังตรวจสอบ...';
      case 'success': return 'ตรวจสอบสำเร็จ';
      case 'retry': return 'กรุณาเป่าใหม่';
      default: return '';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center space-y-12 w-full"
    >
      <div className="text-center space-y-4">
        <h2 className="text-5xl font-bold text-slate-800">กรุณาเป่าแอลกอฮอล์</h2>
        <p className="text-2xl text-slate-500">{getStatusText()}</p>
      </div>

      <StatusCircle status={status} progress={progress} icon={Wind} />

      <div className="w-full max-w-xl space-y-6">
        <ProgressIndicator progress={progress} />
        
        <div className="flex justify-center">
          {status === 'waiting' && (
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={startTest}
              className="kiosk-button h-20 px-12 bg-primary text-white text-2xl shadow-lg"
            >
              เริ่มเป่า
            </motion.button>
          )}
          
          {status === 'retry' && (
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={startTest}
              className="kiosk-button h-20 px-12 bg-destructive text-white text-2xl shadow-lg"
            >
              <RefreshCcw className="mr-3" />
              ลองใหม่
            </motion.button>
          )}
        </div>
      </div>

      <p className="text-xl text-slate-400 font-medium">
        กรุณาเป่าต่อเนื่องจนกว่าจะเสร็จสิ้น
      </p>
    </motion.div>
  );
};

export default AlcoholTest;

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wind, RefreshCcw, CheckCircle2, Circle, User } from 'lucide-react';
import StatusCircle from '../components/kiosk/StatusCircle';
import ProgressIndicator from '../components/kiosk/ProgressIndicator';
import { useWebSocket } from '../context/WebSocketContext';

const AlcoholTest = ({ employee, onComplete, isDevMode, setDevControls }) => {
  const [status, setStatus] = useState('preparing'); // preparing, ready, detected, error, sampling, analyzing
  const [progress, setProgress] = useState(0); // Progress is just for animation now
  
  const { sendCommand, subscribe } = useWebSocket();

  const instructions = [
    {
      title: "หยิบหลอดใหม่",
      description: "รับหลอดใหม่จากกล่องด้านข้าง",
    },
    {
      title: "เสียบหลอดที่ช่องเป่า",
      description: "ใส่หลอดลงในช่องเป่าให้แน่น",
    },
    {
      title: "เป่าลมค้างไว้ประมาณ 3 วินาที",
      description: "เริ่มเป่าเมื่อสัญญาณพร้อมและเป่าต่อเนื่อง",
    },
  ];

  // Send START command on mount
  useEffect(() => {
    if (!isDevMode && employee) {
      sendCommand('START_TEST', { employee_id: employee.id });
    }
  }, [isDevMode, sendCommand, employee]);

  // Handle incoming WebSocket messages via Pub/Sub
  useEffect(() => {
    if (!isDevMode) {
      const unsubState = subscribe('alcohol_state', (data) => {
        const stateMapping = {
          'warming_up': 'preparing',
          'ready': 'ready',
          'breath_detected': 'detected',
          'sampling': 'detected',
          'analyzing': 'detected',
          'error': 'error',
          'flow_error': 'error',
          'timeout': 'error'
        };
        const mappedState = stateMapping[data.state] || data.state;
        setStatus(mappedState);
      });

      const unsubResult = subscribe('alcohol_result', (data) => {
        if (data.success) {
          onComplete(data.value, data.image_base64);
        } else {
          setStatus('error');
        }
      });
      
      return () => {
        unsubState();
        unsubResult();
      };
    }
  }, [isDevMode, onComplete, subscribe]);

  // Dev Mode Mock Progress & State
  useEffect(() => {
    if (isDevMode && status === 'preparing') {
      const timer = setTimeout(() => setStatus('ready'), 2000);
      return () => clearTimeout(timer);
    }
  }, [status, isDevMode]);

  // Fake progress animation for visual feedback during 'detected' state
  useEffect(() => {
    let interval;
    if (status === 'detected') {
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) return prev; // Stop at 90% and wait for real result in prod
          return prev + 2;
        });
      }, 100);
    } else if (status === 'error' || status === 'preparing' || status === 'ready') {
      setProgress(0);
    }
    return () => clearInterval(interval);
  }, [status]);

  const startDevTest = () => {
    setStatus('detected');
    // Mock the backend completing the test
    setTimeout(() => {
      onComplete(Math.random() * 5); // Pass random small value
    }, 4000);
  };

  useEffect(() => {
    if (isDevMode && setDevControls) {
      if (status === 'ready') {
        setDevControls(
          <button
            onClick={startDevTest}
            className="flex items-center px-3 py-1.5 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded-md text-sm font-bold transition-colors"
          >
            <Wind size={16} className="mr-2" />
            Simulate Blow
          </button>
        );
      } else {
        setDevControls(null);
      }
    }
    return () => {
      if (setDevControls) setDevControls(null);
    };
  }, [isDevMode, status, setDevControls]);

  const getStatusDisplay = () => {
    switch (status) {
      case 'preparing': return { text: 'กำลังเตรียมอุปกรณ์...', color: 'text-amber-500' };
      case 'ready': return { text: 'อุปกรณ์พร้อมแล้ว', color: 'text-success' };
      case 'detected': return { text: 'กำลังตรวจวัด...', color: 'text-primary' };
      case 'error': return { text: 'เกิดข้อผิดพลาด', color: 'text-destructive' };
      default: return { text: '', color: '' };
    }
  };

  const statusDisplay = getStatusDisplay();

  const handleRetry = () => {
    setStatus('preparing');
    if (!isDevMode) {
      sendCommand('START_TEST', { employee_id: employee?.id });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-12 items-center"
    >
      {/* Left Column: Instructions & Employee Profile */}
      <div className="space-y-8">
        {/* Identified Employee Info Card */}
        <div className="w-full bg-white rounded-[2.5rem] p-6 flex items-center space-x-6 shadow-sm border border-slate-100 animate-fadeIn">
          <div className="w-20 h-20 bg-primary/5 rounded-2xl flex items-center justify-center text-primary border border-primary/10">
            <User size={48} />
          </div>
          <div className="flex-1 space-y-1">
            <span className="text-sm font-bold text-primary bg-primary/10 px-3 py-1 rounded-full">ผู้ตรวจวัด / Tester</span>
            <h3 className="text-3xl font-black text-slate-800">{employee?.name}</h3>
            <p className="text-lg text-slate-400 font-mono font-bold">รหัสพนักงาน: {employee?.emp_id}</p>
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-4xl font-black text-slate-800">คำแนะนำการใช้งาน</h2>
          <p className="text-xl text-slate-500 font-medium">กรุณาปฏิบัติตามขั้นตอนด้านล่าง</p>
        </div>

        <div className="space-y-6">
          {instructions.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.2 }}
              className="flex items-start space-x-6 p-6 bg-white rounded-3xl shadow-sm border border-slate-100"
            >
              <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center text-2xl font-black">
                {index + 1}
              </div>
              <div className="space-y-1">
                <h3 className="text-2xl font-bold text-slate-800">{step.title}</h3>
                <p className="text-lg text-slate-500 leading-relaxed font-medium">{step.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right Column: Blow Status */}
      <div className="kiosk-card p-12 flex flex-col items-center space-y-10 bg-slate-50/50 border-2 border-white">
        <div className="text-center space-y-2">
          <h2 className={`text-4xl font-black ${statusDisplay.color}`}>
            {statusDisplay.text}
          </h2>
          <p className="text-xl text-slate-400 font-medium uppercase tracking-widest">
            Blow Status
          </p>
        </div>

        <StatusCircle 
          status={status === 'detected' ? 'detecting' : status === 'ready' ? 'waiting' : status} 
          progress={progress} 
          icon={Wind} 
        />

        <div className="w-full space-y-8">
          <div className="space-y-3">
            <div className="flex justify-between items-end">
              <span className="text-lg font-bold text-slate-500">ความคืบหน้า</span>
              <span className="text-2xl font-black text-primary">{progress}%</span>
            </div>
            <ProgressIndicator progress={progress} />
          </div>
          
          <div className="flex justify-center h-24">
            {status === 'ready' && (
              <div className="flex items-center text-slate-400 text-2xl font-bold italic animate-pulse">
                กรุณาเป่าลมอย่างต่อเนื่อง...
              </div>
            )}
            
            {status === 'error' && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleRetry}
                className="kiosk-button w-full bg-destructive text-white text-3xl shadow-lg shadow-destructive/20"
              >
                <RefreshCcw className="mr-3" />
                ลองใหม่
              </motion.button>
            )}

            {status === 'preparing' && (
              <div className="flex items-center text-slate-400 text-2xl font-bold italic animate-pulse">
                โปรดรอสักครู่...
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default AlcoholTest;

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Fingerprint, Check, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { useWebSocket } from '../context/WebSocketContext';

const ScanFingerprint = ({ onConfirm, onCancel, isDevMode, setDevControls }) => {
  const [scanStatusMsg, setScanStatusMsg] = useState('กำลังรอรับข้อมูลลายนิ้วมือ...');
  const [scanState, setScanState] = useState('waiting'); // waiting, scanning, processing, success, error
  const [scanError, setScanError] = useState(null);
  const [scanRetries, setScanRetries] = useState(0);

  const { sendCommand, subscribe } = useWebSocket();

  // Send IDENTIFY command to Python backend to turn on sensor immediately on mount
  useEffect(() => {
    if (!isDevMode) {
      sendCommand('IDENTIFY', {});
    }
  }, [isDevMode, sendCommand]);

  const handleVerifySimulate = () => {
    setScanState('success');
    setScanStatusMsg('ตรวจสอบลายนิ้วมือสำเร็จ! (จำลอง)');
    
    const mockEmployee = {
      id: 'mock-uuid-001',
      name: 'สมชาย รักดี',
      emp_id: 'IDDE00001'
    };

    setTimeout(() => {
      onConfirm(mockEmployee);
    }, 1500);
  };

  const handleRetryScan = () => {
    setScanError(null);
    setScanState('waiting');
    setScanStatusMsg('กำลังรอรับข้อมูลลายนิ้วมือ...');
    if (!isDevMode) {
      sendCommand('IDENTIFY', {});
    }
  };

  // Handle WebSocket Event Subscriptions
  useEffect(() => {
    if (isDevMode) return;

    // 1. Subscribe to sensor state changes
    const unsubState = subscribe('fingerprint_state', (data) => {
      if (data.state) {
        setScanState(data.state);
      }
      if (data.message) {
        setScanStatusMsg(data.message.split(' / ')[0]); // Extract Thai part
      }
    });

    // 2. Subscribe to matching verification results
    const unsubVerify = subscribe('verify_result', (data) => {
      if (data.success && data.match) {
        setScanState('success');
        setScanStatusMsg('ตรวจสอบลายนิ้วมือสำเร็จ!');
        
        const verifiedEmployee = {
          id: data.employee?.id,
          name: data.employee?.name,
          emp_id: data.employee?.emp_id
        };

        setTimeout(() => {
          onConfirm(verifiedEmployee);
        }, 1500);
      } else {
        setScanState('error');
        const errorMsg = data.message || 'ไม่พบลายนิ้วมือที่ตรงกัน';
        
        setScanRetries(prev => {
          const next = prev + 1;
          if (next >= 3) {
            setScanError('ไม่สามารถตรวจสอบได้ ระบบกำลังกลับสู่หน้าหลัก...');
            setTimeout(() => {
              if (onCancel) onCancel();
            }, 3000);
          } else {
            setScanError(`${errorMsg} (ลองใหม่ได้อีก ${3 - next} ครั้ง)`);
          }
          return next;
        });
      }
    });

    return () => {
      unsubState();
      unsubVerify();
    };
  }, [isDevMode, onConfirm, onCancel, subscribe]);

  // Dev Controls Integration
  useEffect(() => {
    if (isDevMode && setDevControls) {
      setDevControls(
        <button
          onClick={handleVerifySimulate}
          className="flex items-center px-4 py-2 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded-md text-sm font-bold transition-colors cursor-pointer"
        >
          <Fingerprint size={16} className="mr-2" />
          Simulate Match
        </button>
      );
    }
    return () => {
      if (setDevControls) setDevControls(null);
    };
  }, [isDevMode, setDevControls]);

  // Helper styles based on scan status
  const getUIParams = () => {
    switch (scanState) {
      case 'success':
        return {
          glowColor: 'bg-success/20',
          borderColor: 'border-success',
          textColor: 'text-success',
          title: 'ยืนยันตัวตนสำเร็จ'
        };
      case 'error':
        return {
          glowColor: 'bg-destructive/20',
          borderColor: 'border-destructive',
          textColor: 'text-destructive',
          title: 'ตรวจสอบไม่ผ่าน'
        };
      case 'processing':
        return {
          glowColor: 'bg-amber-500/20',
          borderColor: 'border-amber-500',
          textColor: 'text-amber-500',
          title: 'กำลังตรวจสอบข้อมูล...'
        };
      case 'scanning':
        return {
          glowColor: 'bg-primary/30',
          borderColor: 'border-primary',
          textColor: 'text-primary',
          title: 'กำลังบันทึกข้อมูลลายนิ้วมือ'
        };
      default:
        return {
          glowColor: 'bg-primary/10',
          borderColor: 'border-slate-200',
          textColor: 'text-primary',
          title: 'กรุณาวางนิ้วบนเครื่องสแกน'
        };
    }
  };

  const ui = getUIParams();

  return (
    <div className="w-full flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-2xl kiosk-card p-12 flex flex-col items-center space-y-10"
      >
        {/* Header bar */}
        <div className="w-full flex justify-between items-center border-b border-slate-100 pb-6">
          <button
            onClick={onCancel}
            className="flex items-center text-slate-400 font-bold text-xl hover:text-primary transition-colors cursor-pointer"
          >
            <ArrowLeft size={32} className="mr-2" />
            ยกเลิก
          </button>
          <div>
            <span className="bg-primary/10 text-primary px-4 py-2 rounded-full text-lg font-bold">
              ขั้นที่ 1: ตรวจสอบตัวตน
            </span>
          </div>
        </div>

        {/* Biometrics Graphic Ring */}
        <div className="relative flex items-center justify-center py-4">
          <AnimatePresence>
            {scanState === 'scanning' && (
              <motion.div
                key="pulse-ring"
                animate={{ scale: [1, 1.3, 1], opacity: [0.4, 0, 0.4] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                className="absolute w-56 h-56 rounded-full border-2 border-primary/40 bg-primary/5"
              />
            )}
          </AnimatePresence>

          <motion.div
            animate={scanState === 'scanning' ? { scale: [1, 1.05, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
            className={`absolute -inset-8 rounded-full blur-xl transition-all duration-500 ${ui.glowColor}`}
          />

          <div className={`relative bg-white p-12 rounded-[3.5rem] shadow-xl border-4 transition-colors duration-500 ${ui.borderColor}`}>
            {scanState === 'success' ? (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              >
                <Check size={110} className="text-success" />
              </motion.div>
            ) : scanState === 'processing' ? (
              <Loader2 size={110} className="text-amber-500 animate-spin" />
            ) : scanState === 'error' ? (
              <motion.div
                animate={{ x: [-10, 10, -10, 10, 0] }}
                transition={{ duration: 0.4 }}
              >
                <AlertCircle size={110} className="text-destructive" />
              </motion.div>
            ) : (
              <Fingerprint size={110} className={scanState === 'scanning' ? 'text-primary' : 'text-slate-400'} />
            )}
          </div>
        </div>

        {/* Status Text Box */}
        <div className="text-center space-y-4 w-full">
          <h4 className={`text-4xl font-black tracking-tight ${ui.textColor}`}>
            {scanError ? 'ลายนิ้วมือไม่ถูกต้อง' : ui.title}
          </h4>
          
          <p className="text-2xl text-slate-500 font-semibold leading-relaxed max-w-lg mx-auto">
            {scanError ? scanError : scanStatusMsg}
          </p>

          {/* Dev Mode Simulation Hint */}
          {isDevMode && scanState === 'waiting' && (
            <p className="text-amber-500 text-lg font-bold bg-amber-50 px-4 py-2 rounded-full inline-block">
              [โหมดนักพัฒนา] กรุณากดปุ่ม Simulate Match ด้านบนเพื่อจำลองการยืนยันตัวตน
            </p>
          )}

          {/* Retry Button */}
          {scanState === 'error' && scanRetries < 3 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="pt-6"
            >
              <button
                onClick={handleRetryScan}
                className="kiosk-button px-10 py-4 bg-primary text-white text-2xl shadow-lg shadow-primary/20 hover:bg-primary/95 cursor-pointer"
              >
                ลองสแกนใหม่อีกครั้ง
              </button>
            </motion.div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default ScanFingerprint;

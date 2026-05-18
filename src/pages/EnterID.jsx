import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Fingerprint, Check, ArrowLeft, User, Loader2 } from 'lucide-react';
import NumericKeypad from '../components/kiosk/NumericKeypad';
import { useWebSocket } from '../context/WebSocketContext';

const EnterID = ({ onConfirm, onCancel, isDevMode, setDevControls }) => {
  const [phase, setPhase] = useState('identifying'); // identifying, loading, verifying
  const [employeeId, setEmployeeId] = useState('');
  const [userData, setUserData] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [scanStatusMsg, setScanStatusMsg] = useState('กำลังรอรับข้อมูลลายนิ้วมือ...');
  const [scanSuccess, setScanSuccess] = useState(false);
  const [scanRetries, setScanRetries] = useState(0);

  const { sendCommand, subscribe } = useWebSocket();

  const handleKeyPress = (num) => {
    if (employeeId.length < 8) {
      setEmployeeId(prev => prev + num);
      setScanError(null);
      setScanSuccess(false);
    }
  };

  const handleDelete = () => {
    setEmployeeId(prev => prev.slice(0, -1));
    setScanError(null);
    setScanSuccess(false);
  };

  const handleIdentify = async () => {
    setPhase('loading');
    setScanError(null);
    setScanSuccess(false);
    setScanRetries(0);

    if (isDevMode) {
      // Mock flow for Dev Mode
      setTimeout(() => {
        setUserData({
          name: 'สมชาย รักดี',
          id: employeeId
        });
        setPhase('verifying');
        setScanStatusMsg('กำลังรอรับข้อมูลลายนิ้วมือ...');
      }, 1000);
    } else {
      // NEW: Send IDENTIFY command to Python backend
      sendCommand('IDENTIFY', { employee_id: employeeId });
      // The rest is handled via WS subscriptions below
    }
  };

  const handleVerify = () => {
    // Dev overlay manual trigger
    setScanSuccess(true);
    setScanStatusMsg('ตรวจสอบลายนิ้วมือสำเร็จ! (จำลอง)');
    setTimeout(() => {
      onConfirm(employeeId);
    }, 1500);
  };

  const handleBack = () => {
    setPhase('identifying');
    setScanError(null);
    setScanSuccess(false);
    setScanRetries(0);
    setUserData(null);
  };

  const handleRetryScan = () => {
    setScanError(null);
    setScanStatusMsg('กำลังรอรับข้อมูลลายนิ้วมือ...');
    if (!isDevMode) {
      // Re-trigger the same IDENTIFY command
      sendCommand('IDENTIFY', { employee_id: employeeId });
    }
  };

  // Handle WS Messages via Pub/Sub
  useEffect(() => {
    if (isDevMode) return;

    // 1. Handle Employee Lookup Result
    const unsubIdentify = subscribe('identify_result', (data) => {
      if (data.success) {
        setUserData({
          id: data.employee.id,
          name: data.employee.name,
          emp_id: data.employee.emp_id
        });
        setPhase('verifying');
        setScanStatusMsg('กำลังรอรับข้อมูลลายนิ้วมือ...');
      } else {
        setScanError(data.message || 'ไม่พบข้อมูลพนักงาน');
        setPhase('identifying');
        setEmployeeId('');
      }
    });

    // 2. Handle Hardware Status Updates
    const unsubState = subscribe('fingerprint_state', (data) => {
      if (data.message) {
        setScanStatusMsg(data.message.split(' / ')[0]); // Use Thai part
      }
    });

    // 3. Handle Final Verification Result
    const unsubVerify = subscribe('verify_result', (data) => {
      if (data.success && data.match) {
        setScanSuccess(true);
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
        setScanRetries(prev => {
          const next = prev + 1;
          if (next >= 3) {
            setScanError('สแกนไม่สำเร็จ ระบบกำลังกลับสู่หน้าหลัก...');
            setTimeout(() => {
              if (onCancel) onCancel();
            }, 3000);
          } else {
            setScanError(`ลายนิ้วมือไม่ตรงกัน (${next}/3 ครั้ง)`);
          }
          return next;
        });
      }
    });

    return () => {
      unsubIdentify();
      unsubState();
      unsubVerify();
    };
  }, [isDevMode, onConfirm, onCancel, employeeId, subscribe]);

  // Dev Controls
  useEffect(() => {
    if (isDevMode && setDevControls) {
      if (phase === 'verifying') {
        setDevControls(
          <button
            onClick={handleVerify}
            className="flex items-center px-3 py-1.5 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded-md text-sm font-bold transition-colors"
          >
            <Fingerprint size={16} className="mr-2" />
            Simulate Scan
          </button>
        );
      } else {
        setDevControls(null);
      }
    }
    return () => {
      if (setDevControls) setDevControls(null);
    };
  }, [isDevMode, phase, setDevControls, employeeId]);

  return (
    <div className="w-full flex items-center justify-center p-4">
      <AnimatePresence mode="wait">
        {phase === 'identifying' || phase === 'loading' ? (
          <motion.div
            key="identifying"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="w-full max-w-2xl kiosk-card p-12 flex flex-col items-center space-y-12"
          >
            <div className="text-center space-y-2">
              <h2 className="text-4xl font-bold text-slate-800">ใส่รหัสพนักงาน</h2>
              <p className="text-xl text-slate-500 font-medium">กรุณาระบุรหัสพนักงานเพื่อตรวจสอบข้อมูล</p>
            </div>

            <div className="w-full h-28 bg-slate-100 rounded-[2rem] flex items-center justify-center border-2 border-slate-200">
              <span className="text-6xl font-mono tracking-[0.5em] text-primary font-bold">
                {employeeId || <span className="text-slate-300">--------</span>}
              </span>
            </div>

            {scanError && phase === 'identifying' && (
              <div className="w-full text-center text-destructive font-bold text-xl">
                {scanError}
              </div>
            )}

            <div className="w-full">
              {phase === 'loading' ? (
                <div className="h-[400px] flex flex-col items-center justify-center space-y-6">
                  <Loader2 size={80} className="animate-spin text-primary" />
                  <p className="text-2xl font-bold text-slate-400">กำลังตรวจสอบข้อมูล...</p>
                </div>
              ) : (
                <NumericKeypad
                  onKeyPress={handleKeyPress}
                  onDelete={handleDelete}
                  onConfirm={handleIdentify}
                  disabledConfirm={!employeeId}
                />
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="verifying"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full max-w-2xl kiosk-card p-12 flex flex-col items-center space-y-8"
          >
            <div className="w-full flex justify-between items-center border-b border-slate-100 pb-6">
              <button
                onClick={handleBack}
                className="flex items-center text-slate-400 font-bold text-xl hover:text-primary transition-colors"
              >
                <ArrowLeft size={32} className="mr-2" />
                ย้อนกลับ
              </button>
              <div className="text-right">
                <span className="bg-primary/10 text-primary px-4 py-2 rounded-full text-lg font-bold">ขั้นที่ 2: ยืนยันตัวตน</span>
              </div>
            </div>

            <div className="w-full bg-slate-50 rounded-[2.5rem] p-8 flex items-center space-x-8 border border-slate-100">
              <div className="w-24 h-24 bg-white rounded-3xl shadow-inner flex items-center justify-center text-primary border border-slate-200">
                <User size={64} />
              </div>
              <div className="flex-1 space-y-1">
                <h3 className="text-3xl font-black text-slate-800">{userData?.name}</h3>
                <p className="text-xl text-primary font-mono font-bold">รหัสพนักงาน: {userData?.emp_id}</p>
              </div>
            </div>

            <div className="flex flex-col items-center space-y-8 py-4">
              <div className="relative">
                <motion.div
                  animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className={`absolute -inset-8 rounded-full blur-xl ${scanError ? 'bg-destructive/20' : scanSuccess ? 'bg-success/20' : 'bg-primary/20'}`}
                />
                <div className="relative bg-white p-10 rounded-[3rem] shadow-xl border-4 border-slate-50">
                  {scanSuccess ? (
                    <Check size={120} className="text-success" />
                  ) : (
                    <Fingerprint size={120} className={scanError ? 'text-destructive' : 'text-primary'} />
                  )}
                </div>
              </div>

              <div className="text-center space-y-3">
                <h4 className={`text-3xl font-bold ${scanError ? 'text-destructive' : scanSuccess ? 'text-success' : 'text-slate-800'}`}>
                  {scanError ? scanError : scanSuccess ? 'ยืนยันตัวตนสำเร็จ' : 'กรุณาวางนิ้วบนเครื่องสแกน'}
                </h4>
                <p className={`text-xl ${scanError ? 'text-destructive/80' : scanSuccess ? 'text-success/80' : 'text-slate-400 animate-pulse'}`}>
                  {scanError ? (scanRetries >= 3 ? 'กรุณาติดต่อผู้ดูแลระบบ' : 'กดปุ่มเพื่อลองสแกนใหม่อีกครั้ง') : scanStatusMsg}
                </p>
                {scanError && scanRetries < 3 && (
                  <div className="pt-4">
                    <button
                      onClick={handleRetryScan}
                      className="px-8 py-3 bg-destructive/10 text-destructive hover:bg-destructive hover:text-white rounded-full font-bold text-xl transition-colors"
                    >
                      ลองสแกนใหม่
                    </button>
                  </div>
                )}
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default EnterID;

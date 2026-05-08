import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Fingerprint, Check, ArrowLeft, User, Loader2 } from 'lucide-react';
import NumericKeypad from '../components/kiosk/NumericKeypad';
import { fetchEmployeeData } from '../services/api';
import { useWebSocket } from '../context/WebSocketContext';

// Test Fingerprint Data
const finger1_template = "IzXhJ205qqb7m0Z0CstIsd9bWZ/Ns+5NLDejMa+IAKwCbn+AwCHbqT5Xk0RJdqsbCKN1QlbPpkkdh0vUS5JQd7gaXvxmI8ZB5q1xMY47LiisilMLswj3gtYo4SoN4SHM8Br7Vo2u3M1FPQAGNIy23HSPfrt6h341/0dP/9d5ok0bLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fA==";
const finger2_template = "f+o/bulopwVzRiIZtxlRt/whg1M4mWFl/Im4w4d4mM72pf36PsAxm4gkYXf3Quc0iOVG+6I6ifSKjmL3Acsd1unm6WPRIRSsHHCltcN0vkINNf272lILqUHScL2cOnV+IatvJeSSCBq4e3WyyAtbamrFrfeGX3XtpSR4+IuYNOwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fA==";

const EnterID = ({ onConfirm, isDevMode, setDevControls }) => {
  const [phase, setPhase] = useState('identifying'); // identifying, loading, verifying
  const [employeeId, setEmployeeId] = useState('');
  const [userData, setUserData] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [scanStatusMsg, setScanStatusMsg] = useState('กำลังรอรับข้อมูลลายนิ้วมือ...');
  const [scanSuccess, setScanSuccess] = useState(false);

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
    try {
      if (isDevMode) {
        // Mock API query for Dev Mode
        setTimeout(() => {
          setUserData({
            name: 'สมชาย รักดี',
            department: 'ฝ่ายผลิต (Production)',
            id: employeeId,
            finger_data: [finger1_template, finger2_template] // Mock array
          });
          setPhase('verifying');
          setScanStatusMsg('กำลังรอรับข้อมูลลายนิ้วมือ...');
        }, 1000);
      } else {
        // Actual REST API Call
        // const data = await fetchEmployeeData(employeeId);
        // setUserData({
        //   name: data.name || 'ไม่ทราบชื่อ',
        //   department: data.department || '-',
        //   id: employeeId,
        //   finger_data: data.fingerprint_template || []
        // });
        setUserData({
          name: 'สมชาย รักดี',
          department: 'ฝ่ายผลิต (Production)',
          id: employeeId,
          finger_data: [finger1_template, finger2_template] // Mock array
        });
        setPhase('verifying');
        setScanStatusMsg('กำลังรอรับข้อมูลลายนิ้วมือ...');
      }
    } catch (err) {
      setScanError('ไม่พบข้อมูลพนักงาน หรือเกิดข้อผิดพลาด');
      setPhase('identifying');
      setEmployeeId('');
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
  };

  // Phase 2: Send WS command when entering verifying phase
  useEffect(() => {
    if (phase === 'verifying' && userData && !isDevMode) {
      const templates = Array.isArray(userData.finger_data) ? userData.finger_data : [userData.finger_data].filter(Boolean);
      sendCommand('VERIFY_FINGERPRINT', { target_templates: templates });
    }
  }, [phase, userData, isDevMode, sendCommand]); // Only runs when phase changes to verifying

  // Handle WS Messages via Pub/Sub
  useEffect(() => {
    if (phase === 'verifying' && !isDevMode) {
      const unsubState = subscribe('fingerprint_state', (data) => {
        if (data.message) {
          setScanStatusMsg(data.message.split(' / ')[0]); // Use Thai part
        }
      });

      const unsubResult = subscribe('fingerprint_result', (data) => {
        if (data.success && data.match) {
          setScanSuccess(true);
          setScanStatusMsg('ตรวจสอบลายนิ้วมือสำเร็จ!');
          setTimeout(() => {
            onConfirm(employeeId);
          }, 1500);
        } else {
          setScanError('ลายนิ้วมือไม่ตรงกัน หรือสแกนไม่สำเร็จ');
        }
      });

      return () => {
        unsubState();
        unsubResult();
      };
    }
  }, [phase, isDevMode, onConfirm, employeeId, subscribe]);

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
                <p className="text-xl text-slate-500 font-medium">{userData?.department}</p>
                <p className="text-lg text-primary font-mono font-bold">ID: {userData?.id}</p>
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
                  {scanError ? 'ลายนิ้วมือไม่ตรงกัน หรือสแกนไม่สำเร็จ' : scanStatusMsg}
                </p>
              </div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default EnterID;

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Fingerprint, Check, ArrowLeft, Loader2, AlertCircle, User, ShieldAlert, BadgeCheck } from 'lucide-react';
import { useWebSocket } from '../context/WebSocketContext';
import NumericKeypad from '../components/kiosk/NumericKeypad';

const RegisterFingerprint = ({ currentStep, setCurrentStep, onCancel, isDevMode, setDevControls }) => {
  // Sub-states: input_id, verifying_employee, employee_details, scanning, enroll_success, enroll_error
  const [registerState, setRegisterState] = useState('input_id');
  const [employeeIdInput, setEmployeeIdInput] = useState('');
  const [employee, setEmployee] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [scanStatusMsg, setScanStatusMsg] = useState('กำลังรอลงทะเบียนลายนิ้วมือ...');
  const [scanState, setScanState] = useState('waiting'); // waiting, scanning, processing, success, error
  const [selectedFingerIndex, setSelectedFingerIndex] = useState(null);
  const [activeRegisteredFingers, setActiveRegisteredFingers] = useState([]);

  const { sendCommand, subscribe } = useWebSocket();

  // Keypad Handlers
  const handleKeyPress = (key) => {
    if (employeeIdInput.length < 5) {
      setEmployeeIdInput((prev) => prev + key);
    }
  };

  const handleDelete = () => {
    setEmployeeIdInput((prev) => prev.slice(0, -1));
  };

  const handleConfirmId = () => {
    if (!employeeIdInput) return;

    setRegisterState('verifying_employee');
    setErrorMessage('');
    setActiveRegisteredFingers([]);

    if (isDevMode) {
      // In dev mode, we wait a moment and show a mock employee or let developer choose via overlay
      setTimeout(() => {
        // Default to a mock employee for the keypad confirmation
        const mockEmployee = {
          id: 'mock-uuid-999',
          name: 'สมชาย รักดี',
          emp_id: `IDDE${employeeIdInput.padStart(5, '0')}`,
          has_fingerprints: true
        };
        setEmployee(mockEmployee);
        setActiveRegisteredFingers([0]); // Default to finger 1 registered
        setRegisterState('employee_details');
      }, 1000);
    } else {
      // Send IDENTIFY command with typed employee sequence ID (e.g. "00001")
      sendCommand('IDENTIFY', { employee_id: employeeIdInput });
    }
  };

  // Trigger Scanner for enrollment
  const handleStartScan = (fingerIndex) => {
    setSelectedFingerIndex(fingerIndex);
    setRegisterState('scanning');
    setScanState('waiting');
    setScanStatusMsg('กรุณาวางนิ้วบนเครื่องสแกน...');

    if (!isDevMode) {
      sendCommand('SCAN_FINGERPRINT', { employee_id: employee.id, finger_index: fingerIndex });
    }
  };

  // Simulate verification and enrollment in dev mode
  const handleSimulateFingers = (fingers) => {
    setEmployee({
      id: 'mock-uuid-new',
      name: 'วัชระ มีสุข',
      emp_id: `IDDE${employeeIdInput.padStart(5, '0') || '00002'}`,
      has_fingerprints: fingers.length > 0
    });
    setActiveRegisteredFingers(fingers);
    setRegisterState('employee_details');
  };

  const handleSimulateNotFound = () => {
    setErrorMessage('ไม่พบข้อมูลพนักงานในระบบ กรุณาตรวจสอบรหัสพนักงานอีกครั้ง');
    setRegisterState('enroll_error');
  };

  const handleSimulateScanSuccess = () => {
    setScanState('success');
    setScanStatusMsg(`สแกนลายนิ้วมือนิ้วที่ ${(selectedFingerIndex !== null ? selectedFingerIndex : 0) + 1} สำเร็จ! กำลังบันทึกข้อมูล...`);
    setTimeout(() => {
      setRegisterState('enroll_success');
      setTimeout(() => {
        onCancel(); // go back to home
      }, 3000);
    }, 1500);
  };

  const handleSimulateScanFail = () => {
    setScanState('error');
    setScanStatusMsg('สแกนลายนิ้วมือไม่สำเร็จ กรุณาลองใหม่อีกครั้ง');
  };

  // Handle WebSocket Event Subscriptions (Phase 2 connection)
  useEffect(() => {
    if (isDevMode) return;

    // 1. Subscribe to identify lookup results
    const unsubIdentify = subscribe('identify_result', (data) => {
      if (registerState !== 'verifying_employee') return;

      if (data.success) {
        setEmployee({
          id: data.employee?.id,
          name: data.employee?.name,
          emp_id: data.employee?.emp_id,
          has_fingerprints: data.has_fingerprints
        });
        setActiveRegisteredFingers(data.registered_fingers || []);
        setRegisterState('employee_details');
      } else {
        setErrorMessage(data.message || 'ไม่พบข้อมูลพนักงานในระบบ');
        setRegisterState('enroll_error');
      }
    });

    // 2. Subscribe to scanner state updates
    const unsubScanState = subscribe('fingerprint_state', (data) => {
      if (registerState !== 'scanning') return;
      if (data.state) {
        setScanState(data.state);
      }
      if (data.message) {
        setScanStatusMsg(data.message.split(' / ')[0]);
      }
    });

    // 3. Subscribe to final enrollment result
    const unsubEnrollResult = subscribe('enroll_result', (data) => {
      if (registerState !== 'scanning') return;

      if (data.success) {
        setScanState('success');
        setRegisterState('enroll_success');
        setTimeout(() => {
          onCancel(); // go back to home
        }, 3000);
      } else {
        setScanState('error');
        setErrorMessage(data.message || 'เกิดข้อผิดพลาดในการลงทะเบียนลายนิ้วมือ');
        setRegisterState('enroll_error');
      }
    });

    return () => {
      unsubIdentify();
      unsubScanState();
      unsubEnrollResult();
    };
  }, [isDevMode, registerState, subscribe, onCancel]);

  // Dev Controls Setup
  useEffect(() => {
    if (isDevMode && setDevControls) {
      setDevControls(
        <div className="flex flex-wrap gap-2">
          {registerState === 'verifying_employee' && (
            <>
              <button
                onClick={() => handleSimulateFingers([])}
                className="px-3 py-1.5 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: พบพนักงาน (ยังไม่มีลายนิ้วมือ)
              </button>
              <button
                onClick={() => handleSimulateFingers([0])}
                className="px-3 py-1.5 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: พบพนักงาน (นิ้ว 1 ลงทะเบียนแล้ว)
              </button>
              <button
                onClick={() => handleSimulateFingers([0, 1])}
                className="px-3 py-1.5 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: พบพนักงาน (นิ้ว 1, 2 ลงทะเบียนแล้ว)
              </button>
              <button
                onClick={() => handleSimulateFingers([0, 1, 2])}
                className="px-3 py-1.5 bg-primary/20 text-primary-200 hover:bg-primary/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: พบพนักงาน (ลงทะเบียนครบ 3 นิ้ว)
              </button>
              <button
                onClick={handleSimulateNotFound}
                className="px-3 py-1.5 bg-destructive/20 text-destructive-200 hover:bg-destructive/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: ไม่พบพนักงาน
              </button>
            </>
          )}

          {registerState === 'scanning' && (
            <>
              <button
                onClick={handleSimulateScanSuccess}
                className="px-3 py-1.5 bg-success/20 text-success-200 hover:bg-success/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: สแกนและลงทะเบียนสำเร็จ
              </button>
              <button
                onClick={handleSimulateScanFail}
                className="px-3 py-1.5 bg-destructive/20 text-destructive-200 hover:bg-destructive/40 hover:text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                จำลอง: สแกนล้มเหลว
              </button>
            </>
          )}
        </div>
      );
    }
    return () => {
      if (setDevControls) setDevControls(null);
    };
  }, [isDevMode, registerState, employeeIdInput, selectedFingerIndex, setDevControls]);

  // UI status color helper for scanner
  const getScannerUIParams = () => {
    switch (scanState) {
      case 'success':
        return {
          glowColor: 'bg-success/20',
          borderColor: 'border-success',
          textColor: 'text-success',
          title: 'บันทึกลายนิ้วมือสำเร็จ'
        };
      case 'error':
        return {
          glowColor: 'bg-destructive/20',
          borderColor: 'border-destructive',
          textColor: 'text-destructive',
          title: 'เกิดข้อผิดพลาดในการสแกน'
        };
      case 'processing':
        return {
          glowColor: 'bg-amber-500/20',
          borderColor: 'border-amber-500',
          textColor: 'text-amber-500',
          title: 'กำลังประมวลผลข้อมูล...'
        };
      case 'scanning':
        return {
          glowColor: 'bg-primary/30',
          borderColor: 'border-primary',
          textColor: 'text-primary',
          title: 'กำลังอ่านลายนิ้วมือ'
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

  const ui = getScannerUIParams();

  return (
    <div className="w-full flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-2xl kiosk-card p-12 flex flex-col items-center space-y-8"
      >
        {/* Header bar */}
        <div className="w-full flex justify-between items-center border-b border-slate-100 pb-6">
          <button
            onClick={() => {
              onCancel();
            }}
            className="flex items-center text-slate-400 font-bold text-xl hover:text-primary transition-colors cursor-pointer"
          >
            <ArrowLeft size={32} className="mr-2" />
            ย้อนกลับ
          </button>
          <div>
            <span className="bg-primary/10 text-primary px-4 py-2 rounded-full text-lg font-bold">
              ลงทะเบียนลายนิ้วมือ
            </span>
          </div>
        </div>

        {/* Dynamic States */}
        <AnimatePresence mode="wait">

          {/* STATE 1: Enter ID Keypad */}
          {registerState === 'input_id' && (
            <motion.div
              key="input_id"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="w-full flex flex-col items-center space-y-8"
            >
              <div className="text-center space-y-2">
                <h3 className="text-3xl font-black text-slate-800">กรอกรหัสพนักงาน</h3>
                <p className="text-xl text-slate-400 font-bold uppercase tracking-wider">Enter Employee ID</p>
              </div>

              {/* ID Input display */}
              <div className="w-full max-w-md h-24 bg-slate-50 border-4 border-slate-200 rounded-3xl flex items-center justify-center text-5xl font-black tracking-[0.5em] pl-[0.5em] text-primary shadow-inner">
                {employeeIdInput || <span className="text-slate-300 font-normal select-none">ID</span>}
              </div>

              <div className="w-full max-w-md pt-2">
                <NumericKeypad
                  onKeyPress={handleKeyPress}
                  onDelete={handleDelete}
                  onConfirm={handleConfirmId}
                  disabledConfirm={!employeeIdInput}
                />
              </div>
            </motion.div>
          )}

          {/* STATE 2: Verifying Employee */}
          {registerState === 'verifying_employee' && (
            <motion.div
              key="verifying_employee"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center justify-center space-y-6 py-12"
            >
              <Loader2 size={80} className="text-primary animate-spin" />
              <div className="text-center space-y-2">
                <h3 className="text-3xl font-black text-slate-800">กำลังตรวจสอบข้อมูลพนักงาน...</h3>
                <p className="text-xl text-slate-400 font-bold">Checking employee data, please wait.</p>
              </div>

              {isDevMode && (
                <div className="pt-6 text-amber-500 text-lg font-bold bg-amber-50 px-6 py-3 rounded-full text-center max-w-md">
                  [โหมดนักพัฒนา] กรุณาใช้ปุ่มจำลอง ด้านบนสุดเพื่อทดสอบกรณีต่างๆ
                </div>
              )}
            </motion.div>
          )}

          {/* STATE 3: Employee Details Evaluation */}
          {registerState === 'employee_details' && employee && (
            <motion.div
              key="employee_details"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="w-full flex flex-col items-center space-y-8 py-4"
            >
              {/* Employee profile card */}
              <div className="w-full max-w-md bg-slate-50 border border-slate-100 rounded-3xl p-4 flex flex-col items-center space-y-4 shadow-sm">
                <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                  <User size={40} />
                </div>
                <div className="text-center space-y-1">
                  <h4 className="text-3xl font-black text-slate-800">{employee.name}</h4>
                  <p className="text-xl text-slate-400 font-bold">รหัส: {employee.emp_id}</p>
                </div>
              </div>

              {/* 3-Box Fingerprint Selection Grid */}
              <div className="w-full max-w-2xl flex flex-col items-center space-y-6">
                <div className="text-center">
                  <h4 className="text-2xl font-black text-slate-700">เลือกนิ้วมือที่ต้องการลงทะเบียน</h4>
                  <p className="text-lg text-slate-400 font-bold">ลงทะเบียนลายนิ้วมือได้สูงสุด 3 ลายนิ้วมือ</p>
                </div>

                <div className="grid grid-cols-3 gap-4 w-full">
                  {[0, 1, 2].map((idx) => {
                    const isRegistered = activeRegisteredFingers.includes(idx);
                    return (
                      <motion.button
                        key={idx}
                        whileHover={!isRegistered ? { scale: 1.05, y: -4 } : {}}
                        whileTap={!isRegistered ? { scale: 0.95 } : {}}
                        onClick={() => {
                          if (!isRegistered) {
                            handleStartScan(idx);
                          }
                        }}
                        disabled={isRegistered}
                        className={`flex flex-col items-center justify-center p-2 rounded-3xl border-4 transition-all duration-300 min-h-[180px] ${isRegistered
                          ? 'bg-success/10 border-success text-success shadow-md shadow-success/10'
                          : 'bg-white border-dashed border-slate-300 text-slate-400 hover:border-primary hover:text-primary hover:shadow-lg hover:shadow-primary/5 cursor-pointer'
                          }`}
                      >
                        {isRegistered ? (
                          <>
                            <div className="w-16 h-16 bg-success/20 rounded-full flex items-center justify-center text-success mb-4 animate-pulse">
                              <Check size={36} />
                            </div>
                            <span className="text-2xl font-black">นิ้วที่ {idx + 1}</span>
                            <span className="text-lg font-bold text-success/80 mt-1">ลงทะเบียนแล้ว</span>
                          </>
                        ) : (
                          <>
                            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 mb-4 transition-colors">
                              <Fingerprint size={36} />
                            </div>
                            <span className="text-2xl font-black text-slate-700">นิ้วที่ {idx + 1}</span>
                            <span className="text-lg font-bold text-slate-400 mt-1">ว่าง (สแกน)</span>
                          </>
                        )}
                      </motion.button>
                    );
                  })}
                </div>

                {/* <button
                  onClick={onCancel}
                  className="kiosk-button w-full h-12 bg-slate-800 text-white text-2xl shadow-lg hover:bg-slate-900 cursor-pointer mt-4"
                >
                  กลับสู่หน้าหลัก
                </button> */}
              </div>
            </motion.div>
          )}

          {/* STATE 4: Scanning Fingerprint */}
          {registerState === 'scanning' && (
            <motion.div
              key="scanning"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full flex flex-col items-center space-y-8 py-4"
            >
              {/* Pulsing graphic */}
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

              {/* Status information */}
              <div className="text-center space-y-4 w-full">
                <h4 className={`text-4xl font-black tracking-tight transition-colors duration-500 ${ui.textColor}`}>
                  {ui.title}
                </h4>
                <p className="text-2xl text-slate-500 font-semibold leading-relaxed max-w-lg mx-auto">
                  {scanStatusMsg}
                </p>

                {isDevMode && scanState === 'waiting' && (
                  <div className="text-amber-500 text-lg font-bold bg-amber-50 px-6 py-2.5 rounded-full inline-block mt-4">
                    [โหมดนักพัฒนา] กรุณาใช้ปุ่มจำลอง ด้านบนสุดเพื่อสแกนลายนิ้วมือให้สำเร็จ
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* STATE 5: Enroll Success */}
          {registerState === 'enroll_success' && (
            <motion.div
              key="enroll_success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center justify-center space-y-6 py-8"
            >
              <div className="w-32 h-32 bg-success/10 rounded-full flex items-center justify-center text-success border-4 border-success animate-bounce">
                <Check size={72} />
              </div>
              <div className="text-center space-y-3">
                <h3 className="text-4xl font-black text-success">ลงทะเบียนลายนิ้วมือสำเร็จ!</h3>
                <p className="text-2xl text-slate-500 font-bold">ข้อมูลถูกบันทึกและส่งไปยังเซิร์ฟเวอร์แล้ว</p>
                <p className="text-xl text-slate-400 font-semibold pt-4">ระบบกำลังกลับสู่หน้าหลักอัตโนมัติ...</p>
              </div>
            </motion.div>
          )}

          {/* STATE 6: Enroll/Lookup Error */}
          {registerState === 'enroll_error' && (
            <motion.div
              key="enroll_error"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-full flex flex-col items-center justify-center space-y-6 py-8"
            >
              <div className="w-24 h-24 bg-destructive/10 rounded-full flex items-center justify-center text-destructive border-4 border-destructive">
                <AlertCircle size={56} />
              </div>
              <div className="text-center space-y-2 w-full px-4">
                <h3 className="text-3xl font-black text-destructive">การลงทะเบียนขัดข้อง</h3>
                <p className="text-2xl text-slate-600 font-bold max-w-lg mx-auto leading-relaxed">
                  {errorMessage || 'ระบบสแกนลายนิ้วมือขัดข้อง ไม่สามารถดำเนินการได้'}
                </p>
              </div>

              <div className="w-full max-w-md pt-6 flex flex-col space-y-4">
                <button
                  onClick={() => {
                    setRegisterState('input_id');
                    setEmployeeIdInput('');
                    setEmployee(null);
                    setErrorMessage('');
                  }}
                  className="kiosk-button w-full h-20 bg-primary text-white text-2xl shadow-lg shadow-primary/20 hover:bg-primary/95 cursor-pointer"
                >
                  ลองใหม่อีกครั้ง
                </button>
                <button
                  onClick={onCancel}
                  className="kiosk-button w-full h-20 bg-slate-800 text-white text-2xl shadow-lg hover:bg-slate-900 cursor-pointer"
                >
                  กลับสู่หน้าหลัก
                </button>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default RegisterFingerprint;

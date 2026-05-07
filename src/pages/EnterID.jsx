import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Fingerprint, Check } from 'lucide-react';
import NumericKeypad from '../components/kiosk/NumericKeypad';

const EnterID = ({ onConfirm }) => {
  const [employeeId, setEmployeeId] = useState('');

  const handleKeyPress = (num) => {
    if (employeeId.length < 10) {
      setEmployeeId(prev => prev + num);
    }
  };

  const handleDelete = () => {
    setEmployeeId(prev => prev.slice(0, -1));
  };

  const handleClear = () => {
    setEmployeeId('');
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      className="w-full max-w-2xl kiosk-card p-12 flex flex-col items-center space-y-10"
    >
      <div className="text-center space-y-2">
        <h2 className="text-4xl font-bold text-slate-800">ใส่รหัสพนักงาน</h2>
        <p className="text-xl text-slate-500">กรุณาระบุรหัสพนักงานของคุณ</p>
      </div>

      <div className="w-full h-24 bg-slate-100 rounded-2xl flex items-center justify-center border-2 border-slate-200">
        <span className="text-5xl font-mono tracking-[0.5em] text-primary font-bold">
          {employeeId || <span className="text-slate-300">--------</span>}
        </span>
      </div>

      <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <NumericKeypad 
          onKeyPress={handleKeyPress} 
          onDelete={handleDelete} 
          onClear={handleClear} 
        />
        
        <div className="flex flex-col space-y-4 h-full justify-between">
          <motion.button
            whileTap={{ scale: 0.95 }}
            className="flex-1 flex flex-col items-center justify-center space-y-4 bg-slate-50 border-2 border-slate-200 rounded-3xl text-slate-600 hover:border-primary/50 hover:bg-primary/5 transition-colors"
          >
            <Fingerprint size={64} className="text-primary/60" />
            <span className="text-xl font-bold">สแกนลายนิ้วมือ</span>
          </motion.button>

          <motion.button
            disabled={!employeeId}
            whileTap={{ scale: 0.95 }}
            onClick={() => onConfirm(employeeId)}
            className="h-24 bg-primary text-white rounded-3xl flex items-center justify-center text-3xl font-bold shadow-lg shadow-primary/20 disabled:grayscale disabled:opacity-30"
          >
            <Check size={40} className="mr-3" />
            ยืนยัน
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

export default EnterID;

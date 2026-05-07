import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';

const ResultCard = ({ isPass, value, countdown, onReset }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1 }}
      className={`w-full max-w-2xl kiosk-card p-16 flex flex-col items-center space-y-10 border-t-[16px] ${
        isPass ? 'border-t-success' : 'border-t-destructive'
      }`}
    >
      <div className="flex flex-col items-center space-y-6">
        {isPass ? (
          <div className="p-6 bg-success/10 rounded-full">
            <CheckCircle2 size={120} className="text-success" />
          </div>
        ) : (
          <div className="p-6 bg-destructive/10 rounded-full">
            <XCircle size={120} className="text-destructive" />
          </div>
        )}
        
        <h2 className={`text-7xl font-black ${isPass ? 'text-success' : 'text-destructive'}`}>
          {isPass ? 'ผ่าน' : 'ไม่ผ่าน'}
        </h2>
      </div>

      <div className="text-center space-y-2">
        <p className="text-2xl text-slate-500 font-medium">ระดับแอลกอฮอล์ที่ตรวจพบ</p>
        <div className="text-8xl font-mono font-bold text-slate-800">
          {value.toFixed(2)} <span className="text-3xl text-slate-400">mg%</span>
        </div>
      </div>

      <div className={`p-6 w-full rounded-2xl text-center text-2xl font-bold ${
        isPass ? 'bg-success/5 text-success' : 'bg-destructive/5 text-destructive'
      }`}>
        {isPass ? 'สามารถปฏิบัติงานได้' : 'กรุณาติดต่อหัวหน้างาน'}
      </div>

      <div className="pt-8 flex flex-col items-center space-y-6 w-full">
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={onReset}
          className="kiosk-button w-full h-20 bg-slate-100 text-slate-600 text-2xl hover:bg-slate-200"
        >
          <ArrowLeft className="mr-3" />
          กลับหน้าหลัก
        </motion.button>
        
        <p className="text-slate-400 text-xl font-medium">
          จะกลับหน้าหลักในอีก <span className="text-primary font-bold">{countdown}</span> วินาที
        </p>
      </div>
    </motion.div>
  );
};

export default ResultCard;

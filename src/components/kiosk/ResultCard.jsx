import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, ArrowLeft, Image as ImageIcon } from 'lucide-react';

const ResultCard = ({ isPass, value, countdown, onReset, isDevMode }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      className={`w-full max-w-5xl kiosk-card p-12 flex flex-col space-y-10 border-t-[16px] ${
        isPass ? 'border-t-success' : 'border-t-destructive'
      }`}
    >
      <div className="text-center">
        <h2 className="text-4xl font-bold text-slate-800">ผลการทดสอบแอลกอฮอล์</h2>
        <p className="text-xl text-slate-500 font-medium mt-2">Alcohol Test Result</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* Left Column: Image placeholder */}
        <div className="relative w-full aspect-square md:aspect-auto md:h-full bg-slate-100 rounded-[2.5rem] overflow-hidden border-4 border-slate-50 flex items-center justify-center shadow-inner">
          <div className="flex flex-col items-center space-y-4 text-slate-400">
            <ImageIcon size={64} className="text-slate-300" />
            <span className="text-xl font-bold">ภาพถ่ายขณะเป่า</span>
            <span className="text-sm font-medium">รอการเชื่อมต่อกล้อง...</span>
          </div>
          {/* <img src={imageSrc} alt="Blowing" className="absolute inset-0 w-full h-full object-cover z-10" /> */}
        </div>

        {/* Right Column: Result Info */}
        <div className="flex flex-col items-center justify-center space-y-8">
          <div className="flex flex-col items-center space-y-4">
            {isPass ? (
              <div className="p-4 bg-success/10 rounded-full">
                <CheckCircle2 size={80} className="text-success" />
              </div>
            ) : (
              <div className="p-4 bg-destructive/10 rounded-full">
                <XCircle size={80} className="text-destructive" />
              </div>
            )}
            
            <h2 className={`text-6xl font-black ${isPass ? 'text-success' : 'text-destructive'}`}>
              {isPass ? 'ผ่าน' : 'ไม่ผ่าน'}
            </h2>
          </div>

          <div className="text-center space-y-1">
            <p className="text-xl text-slate-500 font-medium">ระดับแอลกอฮอล์ที่ตรวจพบ</p>
            <div className="text-7xl font-mono font-bold text-slate-800">
              {value.toFixed(2)} <span className="text-3xl text-slate-400">mg%</span>
            </div>
          </div>

          <div className={`p-4 w-full rounded-2xl text-center text-xl font-bold ${
            isPass ? 'bg-success/5 text-success' : 'bg-destructive/5 text-destructive'
          }`}>
            {isPass ? 'สามารถปฏิบัติงานได้' : 'กรุณาติดต่อหัวหน้างาน'}
          </div>

          <div className="pt-4 flex flex-col items-center space-y-4 w-full">
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={onReset}
              className="kiosk-button w-full h-20 bg-slate-100 text-slate-600 text-2xl hover:bg-slate-200"
            >
              <ArrowLeft className="mr-3" />
              กลับหน้าหลัก
            </motion.button>
            
            {!isDevMode && (
              <p className="text-slate-400 text-lg font-medium">
                จะกลับหน้าหลักในอีก <span className="text-primary font-bold">{countdown}</span> วินาที
              </p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;

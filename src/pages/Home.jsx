import React from 'react';
import { motion } from 'framer-motion';
import { Play, Fingerprint } from 'lucide-react';

const Home = ({ onStart, onRegister }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="flex flex-col items-center justify-center text-center space-y-8"
    >
      {/* Logo Placeholder */}
      <div className="w-32 h-32 bg-primary/10 rounded-3xl flex items-center justify-center mb-4">
        <div className="w-16 h-16 bg-primary rounded-2xl rotate-45" />
      </div>

      <div className="space-y-2">
        <h1 className="text-5xl font-extrabold text-slate-900 tracking-tight">
          ระบบตรวจแอลกอฮอล์
        </h1>
        <p className="text-2xl text-slate-500 font-medium uppercase tracking-widest">
          Alcohol Test System
        </p>
      </div>

      <div className="pt-8 w-full max-w-md space-y-4">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onStart}
          className="kiosk-button w-full h-24 bg-primary text-white text-3xl shadow-lg shadow-primary/20 hover:bg-primary/90"
        >
          <Play className="mr-4 fill-current" size={32} />
          เริ่มใช้งาน
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onRegister}
          className="kiosk-button w-full h-24 bg-slate-100 text-slate-700 text-3xl border-2 border-slate-200 shadow-md hover:bg-slate-200"
        >
          <Fingerprint className="mr-4 text-primary" size={32} />
          ลงทะเบียนลายนิ้วมือ
        </motion.button>
        
        <p className="pt-4 text-slate-400 text-xl">
          กรุณาเตรียมรหัสพนักงาน
        </p>
      </div>
    </motion.div>
  );
};

export default Home;

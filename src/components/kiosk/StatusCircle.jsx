import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const StatusCircle = ({ status, progress, icon: Icon }) => {
  return (
    <div className="relative flex items-center justify-center">
      <AnimatePresence>
        {status === 'detecting' && (
          <>
            <motion.div
              initial={{ scale: 1, opacity: 0.5 }}
              animate={{ scale: 1.5, opacity: 0 }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute w-64 h-64 border-4 border-primary rounded-full"
            />
            <motion.div
              initial={{ scale: 1, opacity: 0.5 }}
              animate={{ scale: 1.8, opacity: 0 }}
              transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
              className="absolute w-64 h-64 border-2 border-primary/50 rounded-full"
            />
          </>
        )}
      </AnimatePresence>

      <motion.div
        animate={status === 'detecting' ? { scale: [1, 1.05, 1] } : {}}
        transition={{ duration: 1, repeat: Infinity }}
        className={`w-64 h-64 rounded-full flex flex-col items-center justify-center z-10 shadow-2xl transition-colors duration-500 ${
          status === 'success' ? 'bg-success text-white' : 'bg-white border-8 border-slate-100 text-primary'
        }`}
      >
        {Icon && <Icon size={80} className={status === 'success' ? 'text-white' : 'text-primary'} />}
        {status === 'detecting' && (
          <span className="text-3xl font-bold mt-2">{progress}%</span>
        )}
      </motion.div>
    </div>
  );
};

export default StatusCircle;

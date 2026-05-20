import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const StatusCircle = ({ status, progress, icon: Icon }) => {
  const isReady = status === 'waiting' || status === 'ready';

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

        {isReady && (
          <>
            <motion.div
              initial={{ scale: 1, opacity: 0.6 }}
              animate={{ scale: 1.6, opacity: 0 }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute w-64 h-64 border-4 border-success rounded-full animate-pulse"
            />
            <motion.div
              initial={{ scale: 1, opacity: 0.6 }}
              animate={{ scale: 1.9, opacity: 0 }}
              transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
              className="absolute w-64 h-64 border-2 border-success/50 rounded-full"
            />
          </>
        )}
      </AnimatePresence>

      <motion.div
        animate={
          status === 'detecting'
            ? { scale: [1, 1.05, 1] }
            : isReady
              ? {
                scale: [1, 1.04, 1],
                backgroundColor: ['#38a169', '#48bb78', '#38a169'],
                boxShadow: [
                  '0 20px 40px -15px rgba(56, 161, 105, 0.3)',
                  '0 25px 50px -10px rgba(56, 161, 105, 0.7)',
                  '0 20px 40px -15px rgba(56, 161, 105, 0.3)'
                ]
              }
              : {}
        }
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        className={`w-64 h-64 rounded-full flex flex-col items-center justify-center z-10 shadow-2xl transition-colors duration-500 ${status === 'success' || isReady
            ? 'bg-success text-white border-0'
            : 'bg-white border-8 border-slate-100 text-primary'
          }`}
      >
        {Icon && (
          <Icon
            size={80}
            className={
              status === 'success' || isReady ? 'text-white' : 'text-primary'
            }
          />
        )}
        {status === 'detecting' && (
          <span className="text-3xl font-bold mt-2">{progress}%</span>
        )}
      </motion.div>
    </div>
  );
};

export default StatusCircle;


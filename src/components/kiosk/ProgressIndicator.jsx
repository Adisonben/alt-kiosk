import React from 'react';
import { motion } from 'framer-motion';

const ProgressIndicator = ({ progress, color = 'bg-primary' }) => {
  return (
    <div className="w-full h-6 bg-slate-200 rounded-full overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        className={`h-full ${color} transition-all duration-300`}
      />
    </div>
  );
};

export default ProgressIndicator;

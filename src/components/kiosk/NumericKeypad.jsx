import React from 'react';
import { Delete, Check } from 'lucide-react';
import { motion } from 'framer-motion';

const NumericKeypad = ({ onKeyPress, onDelete, onConfirm, disabledConfirm }) => {
  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'DEL', '0', 'OK'];

  const handleClick = (key) => {
    if (key === 'OK') {
      if (!disabledConfirm) onConfirm();
    } else if (key === 'DEL') {
      onDelete();
    } else {
      onKeyPress(key);
    }
  };

  return (
    <div className="grid grid-cols-3 gap-6 w-full mx-auto">
      {keys.map((key) => (
        <motion.button
          key={key}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleClick(key)}
          disabled={key === 'OK' && disabledConfirm}
          className={`numpad-button h-24 text-4xl ${key === 'OK'
              ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20'
              : key === 'DEL'
                ? 'text-slate-400'
                : 'text-slate-800'
            } ${key === 'OK' && disabledConfirm ? 'opacity-30 grayscale' : ''}`}
        >
          {key === 'DEL' ? <Delete size={40} /> : key === 'OK' ? <Check size={40} /> : key}
        </motion.button>
      ))}
    </div>
  );
};

export default NumericKeypad;

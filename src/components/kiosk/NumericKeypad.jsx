import React from 'react';
import { Delete, X } from 'lucide-react';
import { motion } from 'framer-motion';

const NumericKeypad = ({ onKeyPress, onDelete, onClear }) => {
  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'C', '0', 'DEL'];

  const handleClick = (key) => {
    if (key === 'C') {
      onClear();
    } else if (key === 'DEL') {
      onDelete();
    } else {
      onKeyPress(key);
    }
  };

  return (
    <div className="grid grid-cols-3 gap-4 w-full max-w-sm mx-auto">
      {keys.map((key) => (
        <motion.button
          key={key}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleClick(key)}
          className={`numpad-button ${
            key === 'C' ? 'text-destructive' : key === 'DEL' ? 'text-slate-500' : 'text-slate-800'
          }`}
        >
          {key === 'DEL' ? <Delete size={32} /> : key === 'C' ? <X size={32} /> : key}
        </motion.button>
      ))}
    </div>
  );
};

export default NumericKeypad;

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, File, X, FileCode, FileText as FileTextIcon } from 'lucide-react';

const ACCEPTED = '.py,.java,.txt,.pdf';
const ACCEPT_MAP = {
  py: { icon: FileCode, color: '#3b82f6', label: 'Python' },
  java: { icon: FileCode, color: '#f97316', label: 'Java' },
  txt: { icon: FileTextIcon, color: '#8b8fa3', label: 'Text' },
  pdf: { icon: File, color: '#ef4444', label: 'PDF' },
};

function getExtension(name) {
  return (name || '').split('.').pop().toLowerCase();
}

export default function FileUpload({ file, onFileChange, disabled }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragOut = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const droppedFile = e.dataTransfer?.files?.[0];
    if (droppedFile) {
      const ext = getExtension(droppedFile.name);
      if (['py', 'java', 'txt', 'pdf'].includes(ext)) {
        onFileChange(droppedFile);
      }
    }
  }, [onFileChange]);

  const handleSelect = (e) => {
    const selected = e.target.files?.[0];
    if (selected) onFileChange(selected);
  };

  const clearFile = (e) => {
    e.stopPropagation();
    onFileChange(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const ext = file ? getExtension(file.name) : null;
  const meta = ext ? ACCEPT_MAP[ext] : null;
  const IconComponent = meta?.icon || File;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.08 }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleSelect}
        className="hidden"
        id="file-upload-input"
      />

      <AnimatePresence mode="wait">
        {file ? (
          /* ── File selected ─────────────────────────────────────────── */
          <motion.div
            key="file-attached"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            className="glass-card flex items-center gap-3 px-4 py-3"
          >
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: `${meta?.color || '#8b5cf6'}15` }}
            >
              <IconComponent size={18} style={{ color: meta?.color || '#8b5cf6' }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                {file.name}
              </p>
              <p className="text-xs text-[var(--text-tertiary)]">
                {meta?.label || ext?.toUpperCase()} · {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <button
              onClick={clearFile}
              disabled={disabled}
              className="w-7 h-7 rounded-lg flex items-center justify-center
                         text-[var(--text-tertiary)] hover:text-[var(--text-primary)]
                         hover:bg-[rgba(255,255,255,0.06)] transition-all cursor-pointer"
            >
              <X size={14} />
            </button>
          </motion.div>
        ) : (
          /* ── Drop zone ─────────────────────────────────────────────── */
          <motion.label
            key="drop-zone"
            htmlFor="file-upload-input"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            onDragEnter={handleDragIn}
            onDragOver={handleDrag}
            onDragLeave={handleDragOut}
            onDrop={handleDrop}
            className={`glass-card flex items-center gap-3 px-4 py-3 cursor-pointer
                        border border-dashed !border-[var(--border-subtle)]
                        hover:!border-[var(--accent-violet)]/40 transition-all duration-200
                        ${isDragging ? 'drop-zone-active' : ''} ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
          >
            <div className="w-9 h-9 rounded-lg bg-[var(--accent-violet-glow)] flex items-center justify-center shrink-0">
              <Upload size={16} className="text-[var(--accent-violet)]" />
            </div>
            <div>
              <p className="text-sm text-[var(--text-secondary)]">
                <span className="text-[var(--text-primary)] font-medium">Drop a file</span> or click to browse
              </p>
              <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
                .py, .java, .txt, .pdf
              </p>
            </div>
          </motion.label>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

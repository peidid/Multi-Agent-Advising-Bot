'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, CalendarDays } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string, planningMode?: boolean) => void;
  disabled?: boolean;
  placeholder?: string;
  showPlanningToggle?: boolean;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Ask me anything about your academic journey...',
  showPlanningToggle = true,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [planningMode, setPlanningMode] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim(), planningMode);
      setMessage('');
      // Reset planning mode after sending
      if (planningMode) {
        setPlanningMode(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t bg-white p-4">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        {/* Planning Mode Toggle */}
        {showPlanningToggle && (
          <button
            type="button"
            onClick={() => setPlanningMode(!planningMode)}
            disabled={disabled}
            className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
              planningMode
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={planningMode ? 'Planning Mode ON - Agents will collaborate to create a course plan' : 'Enable Planning Mode'}
          >
            <CalendarDays className="w-5 h-5" />
          </button>
        )}

        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={planningMode ? 'Describe your course planning request (e.g., "Plan my next 4 semesters for CS major")...' : placeholder}
            disabled={disabled}
            rows={1}
            className={`w-full resize-none rounded-xl border px-4 py-3 pr-12 outline-none disabled:bg-gray-100 disabled:cursor-not-allowed ${
              planningMode
                ? 'border-purple-300 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 bg-purple-50'
                : 'border-gray-300 focus:border-cmu-red focus:ring-1 focus:ring-cmu-red'
            }`}
          />
        </div>
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className={`flex-shrink-0 w-12 h-12 rounded-xl text-white flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            planningMode
              ? 'bg-purple-600 hover:bg-purple-700'
              : 'bg-cmu-red hover:bg-cmu-darkred'
          }`}
        >
          {disabled ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
      <p className="text-center text-xs text-gray-400 mt-2">
        {planningMode ? (
          <span className="text-purple-600 font-medium">
            Planning Mode: Agents will negotiate a course plan (up to 10 rounds)
          </span>
        ) : (
          'Press Enter to send, Shift+Enter for new line'
        )}
      </p>
    </form>
  );
}

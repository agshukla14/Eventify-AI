import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, Sparkles, CheckCircle, ArrowRightLeft, Calendar, Shield } from 'lucide-react';
import { ChatMessage, FullEventPlan } from '../types';
import { sendChatMessage, getChatHistory } from '../api';

interface ChatAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlan: FullEventPlan;
  onPlanUpdated: (newPlan: FullEventPlan) => void;
}

const QUICK_PROMPTS = [
  'Move 5,000 from Decor to Catering',
  'Mark photography as booked',
  'How many days left until my celebration?',
  'What is my catering budget?',
  'Show me all high-risk tasks',
];

export const ChatAssistantDrawer: React.FC<ChatAssistantDrawerProps> = ({
  isOpen,
  onClose,
  currentPlan,
  onPlanUpdated,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && currentPlan) {
      loadHistory();
    }
  }, [isOpen, currentPlan.event_id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadHistory = async () => {
    try {
      const history = await getChatHistory(currentPlan.event_id);
      if (history.length === 0) {
        // Welcome message
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content: `Hello! I'm your AI Celebration Assistant. I am fully grounded in '${currentPlan.intake.title}' (${currentPlan.intake.city}). You can ask me questions about your budget, timeline, or vendors, or ask me to modify your plan directly (e.g. "move budget", "mark vendor as booked", or "postpone date")!`,
            timestamp: new Date().toISOString(),
          },
        ]);
      } else {
        setMessages(history);
      }
    } catch {
      // Set default
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `Hello! I'm your AI Celebration Assistant for '${currentPlan.intake.title}'. How can I help you adjust your plan today?`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || inputValue;
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: Math.random().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      const res = await sendChatMessage(currentPlan.event_id, text);
      const asstMsg: ChatMessage = {
        id: Math.random().toString(),
        role: 'assistant',
        content: res.reply,
        timestamp: new Date().toISOString(),
        tool_calls_executed: res.tools_executed,
      };
      setMessages(prev => [...prev, asstMsg]);

      if (res.updated_plan) {
        onPlanUpdated(res.updated_plan);
      }
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: Math.random().toString(),
        role: 'assistant',
        content: `Sorry, an error occurred: ${err.message || 'Please try again.'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[460px] bg-white border-l border-slate-200 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">

      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-indigo-700 to-emerald-600 text-white flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-white/10 backdrop-blur-md">
            <Bot className="w-5 h-5 text-indigo-200" />
          </div>
          <div>
            <h3 className="font-bold text-sm tracking-tight">AI Planning Assistant</h3>
            <p className="text-2xs text-indigo-100 truncate max-w-[240px]">
              Grounded in: {currentPlan.intake.title}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Quick Prompt Chips */}
      <div className="p-3 bg-slate-50 border-b border-slate-200 flex flex-wrap gap-1.5">
        <div className="w-full text-2xs font-semibold text-slate-400 uppercase tracking-wider mb-0.5">
          Suggested Actions:
        </div>
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(prompt)}
            disabled={isLoading}
            className="px-2.5 py-1 text-2xs font-medium bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-900 border border-slate-200 rounded-lg shadow-2xs transition-colors text-left"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map(msg => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white text-xs ${
                  isUser ? 'bg-slate-800' : 'bg-indigo-600'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-[82%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                  isUser
                    ? 'bg-slate-900 text-white rounded-tr-none'
                    : 'bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200/60'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Tool call badge */}
                {msg.tool_calls_executed && msg.tool_calls_executed.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-200/80 flex flex-wrap gap-1">
                    {msg.tool_calls_executed.map((t, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-0.5 text-2xs font-bold bg-indigo-100 text-indigo-800 rounded-md"
                      >
                        <CheckCircle className="w-3 h-3 text-indigo-600" />
                        Tool Executed: {t.tool || 'Plan Action'}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-slate-400 p-2">
            <div className="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span>AI Assistant is analyzing plan and executing tools...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form
        onSubmit={e => {
          e.preventDefault();
          handleSend();
        }}
        className="p-3.5 bg-white border-t border-slate-200 flex items-center gap-2"
      >
        <input
          type="text"
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          placeholder="Ask a question or type a plan change..."
          disabled={isLoading}
          className="flex-1 px-3.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={!inputValue.trim() || isLoading}
          className="p-2 text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl transition-colors shadow-xs"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};

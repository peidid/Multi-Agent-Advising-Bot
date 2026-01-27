'use client';

import { useState, useEffect, useRef } from 'react';
import { Bot, GraduationCap } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import AgentStatus from '@/components/AgentStatus';
import AuthModal from '@/components/AuthModal';
import ProfileModal from '@/components/ProfileModal';
import {
  auth,
  conversations,
  chat,
  getToken,
  User,
  Conversation,
  Message,
  UserProfile,
} from '@/lib/api';

export default function Home() {
  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [showAuth, setShowAuth] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [loading, setLoading] = useState(true);

  // Chat state
  const [conversationList, setConversationList] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check auth on load
  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const userData = await auth.me();
          setUser(userData);
          await loadConversations();
        } catch {
          auth.logout();
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  // Load conversations
  const loadConversations = async () => {
    try {
      const result = await conversations.list();
      setConversationList(result.conversations);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  // Load a conversation
  const loadConversation = async (id: string) => {
    try {
      const conv = await conversations.get(id);
      setCurrentConversation(conv);
      setMessages(conv.messages || []);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  // Handle auth success
  const handleAuthSuccess = async () => {
    setShowAuth(false);
    const userData = await auth.me();
    setUser(userData);
    await loadConversations();
  };

  // Handle new conversation
  const handleNewConversation = () => {
    setCurrentConversation(null);
    setMessages([]);
    setActiveAgents([]);
    setCompletedAgents([]);
  };

  // Handle select conversation
  const handleSelectConversation = async (id: string) => {
    await loadConversation(id);
    setActiveAgents([]);
    setCompletedAgents([]);
  };

  // Handle delete conversation
  const handleDeleteConversation = async (id: string) => {
    try {
      await conversations.delete(id);
      setConversationList((prev) => prev.filter((c) => c._id !== id));
      if (currentConversation?._id === id) {
        handleNewConversation();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Handle logout
  const handleLogout = () => {
    auth.logout();
    setUser(null);
    setConversationList([]);
    handleNewConversation();
  };

  // Handle profile save
  const handleProfileSave = (profile: UserProfile) => {
    if (user) {
      setUser({ ...user, profile });
    }
  };

  // Handle send message
  const handleSendMessage = async (message: string) => {
    if (!user) {
      setShowAuth(true);
      return;
    }

    // Add user message immediately
    const userMessage: Message = {
      _id: `temp-${Date.now()}`,
      conversation_id: currentConversation?._id || '',
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Show thinking state
    setSending(true);
    setActiveAgents(['coordinator']);
    setCompletedAgents([]);

    try {
      const response = await chat.send(message, currentConversation?._id);

      // Update agents
      setActiveAgents([]);
      setCompletedAgents(response.agents_used);

      // Add assistant message
      const assistantMessage: Message = {
        _id: `temp-${Date.now()}-response`,
        conversation_id: response.conversation_id,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        metadata: { agents_used: response.agents_used },
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Update conversation if new
      if (!currentConversation) {
        const conv = await conversations.get(response.conversation_id);
        setCurrentConversation(conv);
        await loadConversations();
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      // Show error message
      const errorMessage: Message = {
        _id: `temp-${Date.now()}-error`,
        conversation_id: currentConversation?._id || '',
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setSending(false);
      setActiveAgents([]);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Bot className="w-12 h-12 text-cmu-red mx-auto animate-pulse" />
          <p className="mt-2 text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <Sidebar
        user={user}
        conversations={conversationList}
        currentConversationId={currentConversation?._id || null}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onLogout={handleLogout}
        onOpenProfile={() => setShowProfile(true)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <header className="border-b px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-cmu-red rounded-lg flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-gray-900">Academic Advisor</h1>
              <p className="text-sm text-gray-500">CMU Qatar Multi-Agent System</p>
            </div>
          </div>
          {!user && (
            <button
              onClick={() => setShowAuth(true)}
              className="px-4 py-2 bg-cmu-red text-white rounded-lg hover:bg-cmu-darkred transition-colors"
            >
              Sign In
            </button>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-gray-700 mb-2">
                  Welcome to Academic Advisor
                </h2>
                <p className="text-gray-500 max-w-md mx-auto">
                  I'm a multi-agent system designed to help you with academic advising.
                  Ask me about course requirements, schedules, policies, or degree planning.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {[
                    'Can I add a CS minor?',
                    'What courses should I take next semester?',
                    'How do I graduate in 4 years?',
                    'What are the IS degree requirements?',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => handleSendMessage(suggestion)}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <ChatMessage key={msg._id} message={msg} />
                ))}
              </>
            )}

            {/* Agent status while processing */}
            {(activeAgents.length > 0 || completedAgents.length > 0) && (
              <AgentStatus activeAgents={activeAgents} completedAgents={completedAgents} />
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput onSend={handleSendMessage} disabled={sending} />
      </div>

      {/* Modals */}
      {showAuth && (
        <AuthModal
          onSuccess={handleAuthSuccess}
          onClose={() => setShowAuth(false)}
        />
      )}

      {showProfile && user && (
        <ProfileModal
          profile={user.profile}
          onClose={() => setShowProfile(false)}
          onSave={handleProfileSave}
        />
      )}
    </div>
  );
}

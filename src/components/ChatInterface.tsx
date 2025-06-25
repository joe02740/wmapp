import { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import ChatHistory from './ChatHistory';
import { API_BASE } from '../config';
import './ChatInterface.css';

interface Message {
  text: string;
  sender: 'user' | 'ai';
}

interface ChatInterfaceProps {
  loadSessionId?: number | null;
}

const ChatInterface = ({ loadSessionId }: ChatInterfaceProps) => {
  const { user } = useUser();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [searchScope, setSearchScope] = useState('mass_laws');
  const [isLoading, setIsLoading] = useState(false);
  const [usageLimitReached, setUsageLimitReached] = useState(false);
  const [usageLimitMessage, setUsageLimitMessage] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string>('');
  const [showChatHistory, setShowChatHistory] = useState(false);

  // Load specific session if requested
  useEffect(() => {
    if (loadSessionId && loadSessionId > 0) {
      loadChatSession(loadSessionId);
    }
  }, [loadSessionId]);

  // Generate title from first message
  const generateTitle = (firstMessage: string): string => {
    return firstMessage.length > 40 
      ? firstMessage.substring(0, 40) + '...'
      : firstMessage;
  };

  // Save chat session
  const saveChatSession = async (newMessages: Message[]) => {
    if (!user || newMessages.length === 0) return;

    try {
      const title = sessionTitle || generateTitle(newMessages[0].text);
      
      const response = await fetch(`${API_BASE}/api/chat-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          session_id: currentSessionId,
          title: title,
          messages: newMessages
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (!currentSessionId) {
          setCurrentSessionId(data.session_id);
          setSessionTitle(data.title);
        }
      }
    } catch (error) {
      console.error('Error saving chat session:', error);
    }
  };

  // Load chat session
  const loadChatSession = async (sessionId: number) => {
    if (!user || sessionId === 0) {
      // New chat
      setMessages([]);
      setCurrentSessionId(null);
      setSessionTitle('');
      setShowChatHistory(false); // Hide on mobile after selection
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/chat-session/${sessionId}?user_id=${user.id}`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages);
        setCurrentSessionId(sessionId);
        setSessionTitle(data.title);
        setShowChatHistory(false); // Hide on mobile after loading
      }
    } catch (error) {
      console.error('Error loading chat session:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage: Message = { text: input, sender: 'user' };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    
    // Store input before clearing it
    const currentInput = input.trim();
    
    // Clear input and set loading state
    setInput('');
    setIsLoading(true);
    setUsageLimitReached(false);

    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          scope: searchScope,
          user_id: user?.id,
          session_id: currentSessionId
        }),
      });

      const data = await response.json();
      
      if (response.status === 429) {
        // Handle usage limit error
        setUsageLimitReached(true);
        setUsageLimitMessage(data.response || 'Usage limit reached. Please upgrade your subscription.');
        
        const aiMessage: Message = { 
          text: data.response || 'Usage limit reached. Please upgrade your subscription.',
          sender: 'ai' 
        };
        const finalMessages = [...updatedMessages, aiMessage];
        setMessages(finalMessages);
        
        // Save chat session
        await saveChatSession(finalMessages);
      } else if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      } else {
        const aiMessage: Message = { 
          text: data.response, 
          sender: 'ai' 
        };
        
        const finalMessages = [...updatedMessages, aiMessage];
        setMessages(finalMessages);
        
        // Save chat session
        await saveChatSession(finalMessages);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage: Message = { 
        text: `Sorry, I couldn't process your request: ${error instanceof Error ? error.message : 'Unknown error'}`, 
        sender: 'ai' 
      };
      
      const finalMessages = [...updatedMessages, errorMessage];
      setMessages(finalMessages);
      
      // Save chat session
      await saveChatSession(finalMessages);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-interface-container">
      {/* Mobile chat history toggle button */}
      <button 
        className="mobile-history-toggle"
        onClick={() => setShowChatHistory(!showChatHistory)}
      >
        📋 History {showChatHistory ? '→' : '←'}
      </button>

      <div className="chat-interface-layout">
        {/* Chat History Sidebar */}
        <div className={`chat-history-sidebar ${showChatHistory ? 'mobile-open' : ''}`}>
          <ChatHistory 
            onSelectSession={loadChatSession}
            currentSessionId={currentSessionId}
          />
        </div>
        
        {/* Main Chat Area */}
        <div className="chat-interface">
          <div className="search-options">
            <select 
              value={searchScope}
              onChange={(e) => setSearchScope(e.target.value)}
              className="scope-selector"
            >
              <option value="mass_laws">Massachusetts W&M Laws</option>
              <option value="hb44">NIST Handbook 44 - Coming Soon</option>
              <option value="hb130">NIST Handbook 130 - Coming Soon</option>
              <option value="hb133">NIST Handbook 133 - Coming Soon</option>
            </select>
          </div>

          <div className="chat-messages">
            {messages.map((msg, index) => (
              <div 
                key={index} 
                className={`message ${msg.sender === 'user' ? 'user-message' : 'ai-message'}`}
              >
                {msg.text}
              </div>
            ))}
            {isLoading && <div className="loading-indicator">🔍 Analyzing regulations...</div>}
          </div>

          {usageLimitReached && (
            <div className="usage-limit-warning">
              <p>{usageLimitMessage}</p>
              <button 
                className="upgrade-button"
                onClick={() => {
                  // Navigate to profile view - you might need to update this
                  const profileBtn = document.querySelector('li[class="active"]');
                  if (profileBtn) {
                    (profileBtn as HTMLElement).click();
                  }
                }}
              >
                View Subscription Options
              </button>
            </div>
          )}

          <div className="chat-input">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about ${searchScope}...`}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={isLoading}
            />
            <button 
              onClick={handleSendMessage}
              disabled={isLoading || !input.trim()}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Mobile overlay for chat history */}
      {showChatHistory && (
        <div 
          className="mobile-overlay"
          onClick={() => setShowChatHistory(false)}
        />
      )}
    </div>
  );
};

export default ChatInterface;
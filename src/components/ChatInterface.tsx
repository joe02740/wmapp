import { useState } from 'react';
import { useUser } from '@clerk/clerk-react';
import './ChatInterface.css';

interface Message {
  text: string;
  sender: 'user' | 'ai';
}

const ChatInterface = () => {
  const { user } = useUser();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [searchScope, setSearchScope] = useState('mass_laws');
  const [isLoading, setIsLoading] = useState(false);
  const [usageLimitReached, setUsageLimitReached] = useState(false);
  const [usageLimitMessage, setUsageLimitMessage] = useState('');

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage: Message = { text: input, sender: 'user' };
    setMessages([...messages, userMessage]);
    
    // Store input before clearing it
    const currentInput = input.trim();
    
    // Clear input and set loading state
    setInput('');
    setIsLoading(true);
    setUsageLimitReached(false);

    try {
      // Use the relative URL that will be proxied by Vite
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          scope: searchScope,
          user_id: user?.id  // Pass user ID for tracking
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
        setMessages(prevMessages => [...prevMessages, aiMessage]);
      } else if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      } else {
        const aiMessage: Message = { 
          text: data.response, 
          sender: 'ai' 
        };
        
        setMessages(prevMessages => [...prevMessages, aiMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage: Message = { 
        text: `Sorry, I couldn't process your request: ${error instanceof Error ? error.message : 'Unknown error'}`, 
        sender: 'ai' 
      };
      
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="search-options">
        <select 
          value={searchScope}
          onChange={(e) => setSearchScope(e.target.value)}
          className="scope-selector"
        >
          <option value="mass_laws">Massachusetts W&M Laws</option>
          <option value="hb44">NIST Handbook 44</option>
          <option value="hb130">NIST Handbook 130</option>
          <option value="hb133">NIST Handbook 133</option>
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
        {isLoading && <div className="loading-indicator">Loading...</div>}
      </div>

      {usageLimitReached && (
        <div className="usage-limit-warning">
          <p>{usageLimitMessage}</p>
          <button 
            className="upgrade-button"
            onClick={() => {
              // Navigate to profile view
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
  );
};

export default ChatInterface;
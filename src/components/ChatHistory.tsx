import { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import { API_BASE } from '../config';
import './ChatHistory.css';

interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatHistoryProps {
  onSelectSession: (sessionId: number) => void;
  currentSessionId: number | null;
}

const ChatHistory = ({ onSelectSession, currentSessionId }: ChatHistoryProps) => {
  const { user } = useUser();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchChatHistory = async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/chat-history?user_id=${user.id}`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (error) {
      console.error('Error fetching chat history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChatHistory();
  }, [user]);

  const createNewChat = () => {
    onSelectSession(0); // 0 means new chat
  };

  return (
    <div className="chat-history">
      <div className="chat-history-header">
        <h3>Chat History</h3>
        <button className="new-chat-btn" onClick={createNewChat}>
          + New Chat
        </button>
      </div>
      
      <div className="chat-sessions">
        {loading ? (
          <div className="loading">Loading...</div>
        ) : sessions.length > 0 ? (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
              onClick={() => onSelectSession(session.id)}
            >
              <div className="session-title">{session.title}</div>
              <div className="session-date">
                {new Date(session.created_at).toLocaleDateString()}
              </div>
            </div>
          ))
        ) : (
          <div className="no-sessions">No previous chats</div>
        )}
      </div>
    </div>
  );
};

export default ChatHistory;
import { useState } from 'react';
import { SignedIn, SignedOut, SignInButton, UserButton, useUser } from "@clerk/clerk-react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ChatInterface, UserProfile } from './components';
import SuccessPage from './components/SuccessPage';
import CancelPage from './components/CancelPage';
import './App.css';

function MainLayout() {
  const { user } = useUser();
  const [menuOpen, setMenuOpen] = useState(false);
  const [currentView, setCurrentView] = useState<'chat' | 'profile'>('chat');

  const toggleMenu = () => {
    setMenuOpen(!menuOpen);
  };

  const handleMenuClick = (view: 'chat' | 'profile') => {
    setCurrentView(view);
    setMenuOpen(false);
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="menu-button" onClick={toggleMenu}>
          <div className="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
        
        <h1 className="app-title">Weights & Measures Helper</h1>
        
        <div className="auth-buttons">
          <SignedOut>
            <SignInButton />
          </SignedOut>
          <SignedIn>
            <UserButton />
          </SignedIn>
        </div>
      </header>
      
      {menuOpen && (
        <div className="side-menu">
          <div className="menu-close" onClick={toggleMenu}>×</div>
          
          <SignedIn>
            <div className="user-info">
              <img src={user?.imageUrl} alt="Profile" className="user-avatar" />
              <div className="user-details">
                <span className="user-name">{user?.firstName} {user?.lastName}</span>
                <span className="user-email">{user?.primaryEmailAddress?.emailAddress}</span>
              </div>
            </div>
          </SignedIn>
          
          <ul>
            <SignedIn>
              <li className={currentView === 'chat' ? 'active' : ''} onClick={() => handleMenuClick('chat')}>
                Chat
              </li>
              <li className={currentView === 'profile' ? 'active' : ''} onClick={() => handleMenuClick('profile')}>
                My Profile
              </li>
              <li>Settings</li>
              <li>Help</li>
            </SignedIn>
            <SignedOut>
              <li>About</li>
              <li>Help</li>
            </SignedOut>
          </ul>
        </div>
      )}
      
      <main className="app-main">
        <SignedOut>
          <div className="hero-section">
            <div className="hero-content">
              <h1 className="hero-title">
                Stop Hunting Through Regulation Manuals
              </h1>
              <h2 className="hero-subtitle">
                Get instant answers from an AI that actually knows weights & measures law—right from your phone, right in the field.
              </h2>
              
              <div className="hero-features">
                <div className="feature-item">
                  <span className="feature-icon">📱</span>
                  <span>Ask questions on-site during inspections</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⚖️</span>
                  <span>Get citation authority & fine amounts instantly</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">💬</span>
                  <span>Chat history saves your research for later</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">🔄</span>
                  <span>Always updated with latest Mass regulations</span>
                </div>
              </div>

              <div className="hero-testimonial">
                <p className="testimonial-text">
                  "No more driving back to the office to look up laws. No more Ctrl+F through Word docs. 
                  I can handle complex citations confidently right in the field."
                </p>
                <p className="testimonial-author">— Built by a working W&M Inspector</p>
              </div>

              <div className="hero-cta">
                <SignInButton mode="modal">
                  <button className="cta-button">
                    Start Free Trial - 6 Queries
                  </button>
                </SignInButton>
                <p className="cta-subtext">
                  No credit card required • Upgrade to Professional for $20/month
                </p>
              </div>
            </div>

            <div className="hero-visual">
              <div className="phone-mockup">
                <div className="chat-preview">
                  <div className="chat-bubble user">
                    "What's the fine for incorrect pricing on 12 items?"
                  </div>
                  <div className="chat-bubble ai">
                    "Under Mass. Gen. Laws Ch. 98, §§56-57, you can issue fines of $200 per violation. For 12 items, that's $2,400 total. Quote section 56A for your citation authority..."
                  </div>
                </div>
              </div>
            </div>
          </div>
        </SignedOut>
        
        <SignedIn>
          {currentView === 'chat' ? (
            <ChatInterface />
          ) : (
            <UserProfile />
          )}
        </SignedIn>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/success" element={
          <SignedIn>
            <SuccessPage />
          </SignedIn>
        } />
        
        <Route path="/cancel" element={
          <SignedIn>
            <CancelPage />
          </SignedIn>
        } />
        
        <Route path="/" element={<MainLayout />} />
      </Routes>
    </Router>
  );
}

export default App;
import { useState } from 'react';
import { SignedIn, SignedOut, SignInButton, UserButton, useUser } from "@clerk/clerk-react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
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
          <div className="welcome-message">
            <h2>Welcome to the Weights and Measures Helper</h2>
            <p>Sign in to access the AI-enhanced search tool for Massachusetts Weights & Measures laws, regulations, and handbooks.</p>
            <SignInButton mode="modal">
              <button className="sign-in-btn">Sign In</button>
            </SignInButton>
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
import React from 'react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="disclaimer">
          <strong>⚠️ Important Disclaimer:</strong> This AI assistant provides general information only. 
          Always verify with official sources and consult legal counsel for enforcement decisions. 
          AI can make errors - you are responsible for confirming accuracy before taking action.
        </div>
        <div className="footer-links">
          <span>© 2025 W&M Helper</span>
          <span>•</span>
          <span>Built by a working W&M Inspector</span>
          <span>•</span>
          <span>For informational purposes only</span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
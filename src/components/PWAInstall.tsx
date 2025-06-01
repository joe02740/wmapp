import { useState, useEffect } from 'react';
import './PWAInstall.css';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const PWAInstall = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showButton, setShowButton] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Check if app is already installed
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    const isInWebAppiOS = (window.navigator as any).standalone === true;
    
    if (isStandalone || isInWebAppiOS) {
      setIsInstalled(true);
      return;
    }

    // Listen for the beforeinstallprompt event
    const handleBeforeInstallPrompt = (e: Event) => {
      // Prevent the mini-infobar from appearing
      e.preventDefault();
      // Save the event so it can be triggered later
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      // Show the install button
      setShowButton(true);
    };

    // Listen for successful app installation
    const handleAppInstalled = () => {
      setIsInstalled(true);
      setShowButton(false);
      setDeferredPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    // Show the install prompt
    await deferredPrompt.prompt();
    
    // Wait for the user's response
    const choiceResult = await deferredPrompt.userChoice;
    
    if (choiceResult.outcome === 'accepted') {
      console.log('User accepted the install prompt');
    }
    
    // Clear the saved prompt since it can only be used once
    setDeferredPrompt(null);
    setShowButton(false);
  };

  // Don't show anything if app is already installed
  if (isInstalled) {
    return (
      <div className="pwa-install installed">
        <div className="pwa-icon">📱</div>
        <div className="pwa-content">
          <h4>App Installed!</h4>
          <p>W&M Helper is installed on your device for quick access.</p>
        </div>
      </div>
    );
  }

  // Show install button if available
  if (showButton && deferredPrompt) {
    return (
      <div className="pwa-install">
        <div className="pwa-icon">📱</div>
        <div className="pwa-content">
          <h4>Install App</h4>
          <p>Add W&M Helper to your home screen for instant access during inspections.</p>
          <button className="pwa-install-button" onClick={handleInstallClick}>
            Add to Home Screen
          </button>
        </div>
      </div>
    );
  }

  // Show manual instructions for iOS/other browsers
  return (
    <div className="pwa-install manual">
      <div className="pwa-icon">📱</div>
      <div className="pwa-content">
        <h4>Add to Home Screen</h4>
        <div className="manual-instructions">
          <p><strong>iPhone/iPad:</strong></p>
          <ol>
            <li>Tap the Share button <span className="ios-icon">⬆️</span></li>
            <li>Scroll down and tap "Add to Home Screen"</li>
            <li>Tap "Add" in the top right</li>
          </ol>
          <p><strong>Android Chrome:</strong></p>
          <ol>
            <li>Tap the menu (⋮) in Chrome</li>
            <li>Tap "Add to Home screen"</li>
            <li>Tap "Add"</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default PWAInstall;
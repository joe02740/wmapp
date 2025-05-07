import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './SuccessPage.css';

const SuccessPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState<string>('');
  
  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    
    if (sessionId) {
      // The session_id confirms the payment was successful
      // We don't need to verify it again as Stripe has already redirected
      // to this success page, and our webhook will handle the database update
      
      // In a production app, you might want to fetch the user's updated subscription
      // to display the correct tier they've upgraded to
      
      // For demo purposes, simulate a loading state
      setTimeout(() => {
        setLoading(false);
        // This would be fetched from your API in a real implementation
        setTier('premium'); 
      }, 1500);
    } else {
      setError('No session ID found');
      setLoading(false);
    }
  }, [searchParams]);
  
  const handleContinue = () => {
    navigate('/'); // Navigate back to home
  };
  
  if (loading) {
    return (
      <div className="result-page">
        <div className="result-card">
          <div className="loading-spinner"></div>
          <p>Processing your payment...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="result-page">
        <div className="result-card error">
          <h2>Payment Error</h2>
          <p>{error}</p>
          <button className="continue-button" onClick={handleContinue}>
            Return to Home
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="result-page success-page">
      <div className="result-card">
        <div className="success-icon">✓</div>
        <h2>Payment Successful!</h2>
        <p>Your subscription has been upgraded successfully.</p>
        <p>You now have access to all features of the {tier} tier.</p>
        <button className="continue-button" onClick={handleContinue}>
          Continue to App
        </button>
      </div>
    </div>
  );
};

export default SuccessPage;
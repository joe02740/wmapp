import { useNavigate } from 'react-router-dom';
import './SuccessPage.css'; // You can share the same CSS

const CancelPage = () => {
  const navigate = useNavigate();
  
  const handleContinue = () => {
    navigate('/'); // Navigate back to home
  };
  
  return (
    <div className="result-page cancel-page">
      <div className="result-card">
        <h2>Payment Canceled</h2>
        <p>Your subscription upgrade was canceled. No charges have been made.</p>
        <p>You can try again or continue with your current subscription.</p>
        <button className="continue-button" onClick={handleContinue}>
          Return to Home
        </button>
      </div>
    </div>
  );
};

export default CancelPage;
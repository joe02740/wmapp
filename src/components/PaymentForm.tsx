import { useState } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import './PaymentForm.css';

interface PaymentFormProps {
  amount: number;
  tier: string;
  userId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

const PaymentForm = ({ amount, tier, userId, onSuccess, onCancel }: PaymentFormProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [succeeded, setSucceeded] = useState(false);
  
  const stripe = useStripe();
  const elements = useElements();
  
  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!stripe || !elements) {
      // Stripe.js has not loaded yet.
      return;
    }
    
    setLoading(true);
    setError(null);
    
    // NOTE: In a real implementation, you would call your backend here to create a payment intent
    // and then confirm the payment on the client. This is just a demo.
    
    try {
      // Get card element
      const cardElement = elements.getElement(CardElement);
      
      if (!cardElement) {
        throw new Error('Card element not found');
      }
      
      // Simulate a payment processing delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // For demo purposes, we'll just simulate a successful payment
      // In a real implementation, you would use the paymentMethod to confirm the payment
      
      setSucceeded(true);
      setLoading(false);
      
      // Call an API to update the user's subscription
      const response = await fetch('/api/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          tier: tier
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update subscription');
      }
      
      // Notify parent that payment was successful
      onSuccess();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setLoading(false);
    }
  };
  
  const CARD_ELEMENT_OPTIONS = {
    style: {
      base: {
        color: '#32325d',
        fontFamily: '"IM Fell English", serif',
        fontSmoothing: 'antialiased',
        fontSize: '16px',
        '::placeholder': {
          color: '#aab7c4',
        },
      },
      invalid: {
        color: '#fa755a',
        iconColor: '#fa755a',
      },
    },
  };
  
  return (
    <div className="payment-form-container">
      <div className="payment-form-card">
        {succeeded ? (
          <div className="payment-success">
            <h3>Payment Successful!</h3>
            <p>Your subscription has been upgraded to {tier}.</p>
            <button className="payment-button" onClick={onSuccess}>
              Continue
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <h3>Subscribe to {tier} Plan</h3>
            <p className="payment-amount">${amount.toFixed(2)} per month</p>
            
            <div className="form-row">
              <label htmlFor="card-element">Credit or debit card</label>
              <div className="card-element-container">
                <CardElement id="card-element" options={CARD_ELEMENT_OPTIONS} />
              </div>
            </div>
            
            {error && <div className="payment-error">{error}</div>}
            
            <div className="payment-actions">
              <button 
                type="button" 
                className="cancel-button"
                onClick={onCancel}
                disabled={loading}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="payment-button"
                disabled={loading || !stripe}
              >
                {loading ? 'Processing...' : `Pay $${amount.toFixed(2)}`}
              </button>
            </div>
            
            <div className="payment-disclaimer">
              <p>This is a demo. No actual payment will be processed.</p>
              <p>For testing, you can use the card number: 4242 4242 4242 4242</p>
              <p>Use any future expiration date, any 3-digit CVC, and any postal code.</p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default PaymentForm;
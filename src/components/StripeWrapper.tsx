import { Elements } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import PaymentForm from './PaymentForm';

// Mock Stripe public key - replace with your actual publishable key when using in production
const stripePromise = loadStripe('pk_test_TYooMQauvdEDq54NiTphI7jx');

interface StripeWrapperProps {
  amount: number;
  tier: string;
  userId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

const StripeWrapper = ({ amount, tier, userId, onSuccess, onCancel }: StripeWrapperProps) => {
  return (
    <Elements stripe={stripePromise}>
      <PaymentForm 
        amount={amount} 
        tier={tier} 
        userId={userId} 
        onSuccess={onSuccess} 
        onCancel={onCancel} 
      />
    </Elements>
  );
};

export default StripeWrapper;
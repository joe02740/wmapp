import { Elements } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import PaymentForm from './PaymentForm';

// Your actual test publishable key
const stripePromise = loadStripe('pk_test_51RKr9tB1wZPdY9nxxomYqJdK7KtebPA2lwnySGu499AOjNUBRA50IpjCpDhWTYU6b1IYsLkkmKxztcwjVO9v8jcR00GJ4MFauy');

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
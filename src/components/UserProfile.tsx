import { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import { API_BASE } from '../config';
import PWAInstall from './PWAInstall';
import './UserProfile.css';

interface UsageData {
  user_id: string;
  subscription_tier: string;
  subscription_end_date: string | null;
  usage: {
    daily: number;
    daily_limit: number;
    monthly: number;
    monthly_limit: number;
    total: number;
  };
  recent_queries: {
    query: string;
    scope: string;
    tokens_used: number;
    created_at: string;
  }[];
}

const UserProfile = () => {
  const { user } = useUser();
  const [usageData, setUsageData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>('');
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  
  // Plan prices map
  //const tierPrices: { [key: string]: number } = {
    //'free': 0,
    //'paid': 20.00
  //};

  useEffect(() => {
    if (user) {
      fetchUsageData();
    }
  }, [user]);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('success') === 'true') {
      setPaymentSuccess(true);
      fetchUsageData(); // Refresh data
    }
  }, []);

  const fetchUsageData = async () => {
    if (!user) return;
    
    console.log('User object:', user); // Add this line
    console.log('User ID:', user.id);  // Add this line
    
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/usage?user_id=${user.id}`);
      
      if (!response.ok) {
        throw new Error(`Error fetching usage data: ${response.status}`);
      }
      
      const data = await response.json();
      setUsageData(data);
      setSelectedTier(data.subscription_tier);
    } catch (err) {
      console.error('Error fetching usage data:', err);
      setError('Failed to load your usage data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgradeSubscription = async () => {
    if (!user || !selectedTier || selectedTier === usageData?.subscription_tier) return;
    try {
      setLoading(true);
      // If downgrading to free tier, process immediately
      if (selectedTier === 'free') {
        const response = await fetch(`${API_BASE}/api/subscribe`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: user.id,
            tier: selectedTier
          }),
        });
        if (!response.ok) {
          throw new Error(`Error updating subscription: ${response.status}`);
        }
        // Refresh usage data after updating subscription
        await fetchUsageData();
        alert(`Your subscription has been updated to ${selectedTier} tier!`);
      } else {
        // For paid tiers, redirect to Stripe Checkout
        const response = await fetch(`${API_BASE}/api/create-checkout-session`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: user.id,
            tier: selectedTier
          }),
        });
        if (!response.ok) {
          throw new Error(`Error creating checkout session: ${response.status}`);
        }
        const data = await response.json();
        // Redirect to Stripe Checkout
        window.location.href = data.checkoutUrl;
      }
    } catch (err) {
      console.error('Error updating subscription:', err);
      setError(err instanceof Error ? err.message : 'Failed to update your subscription. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  if (loading && !usageData) {
    return <div className="loading">Loading your profile...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="user-profile">
      <h2>Your Profile</h2>
      
      {usageData && (
        <>
          <div className="profile-section">
            <h3>Subscription</h3>
            <div className="subscription-info">
              <p>Current Tier: <span className="tier-badge">{usageData.subscription_tier}</span></p>
              {usageData.subscription_end_date && (
                <p>Expires: {formatDate(usageData.subscription_end_date)}</p>
              )}
            </div>
          </div>
          
          <div className="profile-section">
            <h3>Usage Statistics</h3>
            <div className="usage-stats">
              <div className="usage-meter">
                <p>Daily Usage</p>
                <div className="meter">
                  <div 
                    className="meter-fill" 
                    style={{ 
                      width: `${Math.min(100, (usageData.usage.daily / usageData.usage.daily_limit) * 100)}%`,
                      backgroundColor: usageData.usage.daily > usageData.usage.daily_limit * 0.8 ? '#e74c3c' : '#3498db'
                    }}
                  ></div>
                </div>
                <p className="meter-text">
                  {usageData.usage.daily} of {usageData.usage.daily_limit} queries
                </p>
              </div>
              
              <div className="usage-meter">
                <p>Monthly Usage</p>
                <div className="meter">
                  <div 
                    className="meter-fill" 
                    style={{ 
                      width: `${Math.min(100, (usageData.usage.monthly / usageData.usage.monthly_limit) * 100)}%`,
                      backgroundColor: usageData.usage.monthly > usageData.usage.monthly_limit * 0.8 ? '#e74c3c' : '#3498db'
                    }}
                  ></div>
                </div>
                <p className="meter-text">
                  {usageData.usage.monthly} of {usageData.usage.monthly_limit} queries
                </p>
              </div>
              
              <p className="total-usage">Total Queries: {usageData.usage.total}</p>
            </div>
          </div>
          
          <div className="profile-section">
            <h3>Recent Queries</h3>
            {usageData.recent_queries.length > 0 ? (
              <div className="recent-queries">
                {usageData.recent_queries.map((query, index) => (
                  <div key={index} className="query-item">
                    <div className="query-text">"{query.query}"</div>
                    <div className="query-meta">
                      <span>{query.scope}</span>
                      <span>{formatDate(query.created_at)} at {formatTime(query.created_at)}</span>
                      <span>{query.tokens_used} tokens</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p>No queries yet.</p>
            )}
          </div>
          
          <div className="profile-section">
            <h3>Upgrade Subscription</h3>
            <div className="subscription-plans">
              <div className={`plan ${selectedTier === 'free' ? 'selected' : ''}`} onClick={() => setSelectedTier('free')}>
                <h4>Free Trial</h4>
                <p className="price">$0</p>
                <ul>
                  <li>2 queries per day</li>
                  <li>6 queries per month</li>
                  <li>Basic support</li>
                </ul>
                <div className="plan-badge">Current: {usageData.subscription_tier === 'free' ? 'Yes' : 'No'}</div>
              </div>
              
              <div className={`plan ${selectedTier === 'paid' ? 'selected' : ''}`} onClick={() => setSelectedTier('paid')}>
                <h4>Professional</h4>
                <p className="price">$20 / month</p>
                <ul>
                  <li>50 queries per day</li>
                  <li>500 queries per month</li>
                  <li>Priority support</li>
                  <li>Advanced features</li>
                </ul>
                <div className="plan-badge">Current: {usageData.subscription_tier === 'paid' ? 'Yes' : 'No'}</div>
              </div>
            </div>
            
            <button 
              className="upgrade-button"
              disabled={selectedTier === usageData.subscription_tier || loading}
              onClick={handleUpgradeSubscription}
            >
              {loading ? 'Processing...' : `Upgrade to ${selectedTier !== usageData.subscription_tier ? selectedTier : 'selected'} tier`}
            </button>
            <p className="disclaimer">* Free downgrades are processed immediately. Paid upgrades require payment information.</p>
          </div>

          <div className="profile-section">
            <h3>📱 Mobile App</h3>
            <PWAInstall />
          </div>
        </>
      )}
      {paymentSuccess && <div>Payment was successful!</div>}
    </div>
  );
};

export default UserProfile;
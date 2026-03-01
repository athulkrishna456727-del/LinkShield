import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { Check, Shield, Star, Crown } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Plans = () => {
  const { user, token, refreshUser } = useAuth();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await axios.get(`${API_URL}/billing/plans`);
      setPlans(response.data);
    } catch (error) {
      console.error('Failed to fetch plans', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleUpgrade = async (planName) => {
    if (planName === 'free') {
      toast.info('You are already on the free plan or cannot downgrade via payment');
      return;
    }

    setUpgrading(true);

    try {
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        toast.error('Failed to load payment gateway. Please try again.');
        setUpgrading(false);
        return;
      }

      const orderResponse = await axios.post(
        `${API_URL}/billing/create-order`,
        { plan: planName },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const { order_id, amount, currency, key_id } = orderResponse.data;

      const options = {
        key: key_id,
        amount: amount * 100,
        currency: currency,
        name: 'Link Shield',
        description: `Upgrade to ${planName.toUpperCase()} plan`,
        order_id: order_id,
        handler: async function (response) {
          try {
            await axios.post(
              `${API_URL}/billing/verify-payment`,
              {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                plan: planName
              },
              { headers: { Authorization: `Bearer ${token}` } }
            );

            toast.success('Payment successful! Your plan has been upgraded.');
            refreshUser();
          } catch (error) {
            toast.error('Payment verification failed. Please contact support.');
          }
        },
        prefill: {
          name: user?.name,
          email: user?.email
        },
        theme: {
          color: '#00FF94'
        },
        modal: {
          ondismiss: function () {
            setUpgrading(false);
          }
        }
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
      setUpgrading(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate payment');
      setUpgrading(false);
    }
  };

  const getPlanIcon = (planName) => {
    if (planName === 'free') return Shield;
    if (planName === 'premium') return Star;
    return Crown;
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <p className="text-muted-foreground">Loading plans...</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12" data-testid="plans-page">
        <div className="text-center mb-12">
          <h1 className="font-heading text-4xl md:text-5xl font-bold mb-4">Choose Your Plan</h1>
          <p className="text-muted-foreground text-lg">Flexible pricing for all your security needs</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan) => {
            const Icon = getPlanIcon(plan.name);
            const isCurrentPlan = user?.plan === plan.name;
            const isPremium = plan.name === 'premium';
            
            return (
              <div
                key={plan.name}
                className={`bg-card rounded-xl p-8 border-2 transition-all ${
                  isPremium
                    ? 'border-primary shadow-[0_0_30px_rgba(0,255,148,0.2)]'
                    : 'border-border hover:border-primary/50'
                }`}
                data-testid={`plan-${plan.name.toLowerCase()}`}
              >
                <div className="flex items-center justify-between mb-6">
                  <Icon className={`h-10 w-10 ${isPremium ? 'text-primary' : 'text-muted-foreground'}`} />
                  {isCurrentPlan && (
                    <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full border border-primary/20" data-testid="current-plan-badge">
                      CURRENT
                    </span>
                  )}
                </div>

                <h2 className="font-heading text-3xl font-bold mb-2 capitalize">{plan.name}</h2>
                <div className="mb-6">
                  <span className="font-heading text-4xl font-bold">
                    {plan.price === 0 ? 'Free' : `₹${plan.price}`}
                  </span>
                  {plan.price > 0 && <span className="text-muted-foreground ml-2">/ month</span>}
                </div>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start space-x-3">
                      <Check className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                {isCurrentPlan ? (
                  <Button
                    disabled
                    className="w-full"
                    variant="outline"
                    data-testid={`plan-btn-${plan.name.toLowerCase()}`}
                  >
                    Current Plan
                  </Button>
                ) : (
                  <Button
                    onClick={() => handleUpgrade(plan.name)}
                    disabled={upgrading}
                    className={`w-full ${
                      isPremium
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)]'
                        : ''
                    }`}
                    data-testid={`plan-btn-${plan.name.toLowerCase()}`}
                  >
                    {upgrading ? 'Processing...' : plan.price === 0 ? 'Contact Admin' : 'Upgrade Now'}
                  </Button>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-12 text-center">
          <p className="text-muted-foreground text-sm">
            All plans include secure threat scanning and real-time analysis. Upgrade or downgrade anytime.
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default Plans;

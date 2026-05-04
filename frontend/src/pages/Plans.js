import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Check, Crown, Zap, Shield } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Plans = () => {
  const { user, token } = useAuth();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const res = await axios.get(`${API_URL}/billing/plans`);
      setPlans(res.data);
    } catch (error) {
      console.error('Failed to fetch plans');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planName) => {
    toast.info('Payment gateway integration pending. Contact admin to upgrade.');
  };

  const icons = { free: Shield, premium: Zap, enterprise: Crown };
  const colors = {
    free: 'border-zinc-700',
    premium: 'border-yellow-500/40 bg-yellow-500/5',
    enterprise: 'border-purple-500/40 bg-purple-500/5'
  };

  if (loading) return <Layout><div className="flex items-center justify-center py-20"><p>Loading...</p></div></Layout>;

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="plans-page">
        <div className="text-center mb-10">
          <h1 className="font-heading text-4xl font-bold mb-2">Choose Your Plan</h1>
          <p className="text-muted-foreground">Unlock advanced scanning, IOC extraction, API access, and more</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map(plan => {
            const Icon = icons[plan.name] || Shield;
            const isCurrentPlan = user?.plan === plan.name;
            return (
              <div
                key={plan.name}
                className={`bg-card border rounded-xl p-6 relative ${colors[plan.name]} ${isCurrentPlan ? 'ring-2 ring-primary' : ''}`}
                data-testid={`plan-card-${plan.name}`}
              >
                {isCurrentPlan && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-primary text-primary-foreground text-xs font-semibold rounded-full">
                    CURRENT
                  </div>
                )}
                <div className="text-center mb-6">
                  <Icon className={`h-10 w-10 mx-auto mb-3 ${plan.name === 'enterprise' ? 'text-purple-400' : plan.name === 'premium' ? 'text-yellow-400' : 'text-zinc-400'}`} />
                  <h2 className="font-heading text-2xl font-bold capitalize">{plan.name}</h2>
                  <div className="mt-2">
                    {plan.price === 0 ? (
                      <span className="text-3xl font-bold">Free</span>
                    ) : (
                      <span className="text-3xl font-bold">{plan.price}<span className="text-sm text-muted-foreground font-normal"> INR/mo</span></span>
                    )}
                  </div>
                </div>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-sm">
                      <Check className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {isCurrentPlan ? (
                  <Button disabled className="w-full" variant="outline">Current Plan</Button>
                ) : plan.price === 0 ? (
                  <Button disabled className="w-full" variant="outline">Default</Button>
                ) : (
                  <Button
                    className="w-full"
                    onClick={() => handleUpgrade(plan.name)}
                    data-testid={`upgrade-${plan.name}-btn`}
                  >
                    Upgrade to {plan.name}
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Layout>
  );
};

export default Plans;

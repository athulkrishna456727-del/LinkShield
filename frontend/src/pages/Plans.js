import React from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { Check, Zap, Shield, Star } from 'lucide-react';
import { Button } from '../components/ui/button';

const Plans = () => {
  const { user } = useAuth();

  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      icon: Shield,
      features: [
        '50 initial credits',
        'Basic URL scanning',
        'Basic file analysis',
        'Limited scans per day',
        'Standard processing speed',
        'Basic threat detection',
        'Max 10MB file upload'
      ],
      current: user?.plan === 'free'
    },
    {
      name: 'Premium',
      price: '$29',
      period: 'per month',
      icon: Star,
      features: [
        '500 monthly credits',
        'Advanced URL scanning',
        'Advanced file analysis',
        'Unlimited scans',
        'Priority processing',
        'Advanced threat intelligence',
        'Max 100MB file upload',
        'IOC extraction',
        'Priority support'
      ],
      current: user?.plan === 'premium',
      highlight: true
    }
  ];

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12" data-testid="plans-page">
        <div className="text-center mb-12">
          <h1 className="font-heading text-4xl md:text-5xl font-bold mb-4">Choose Your Plan</h1>
          <p className="text-muted-foreground text-lg">Select the plan that best fits your security needs</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan, index) => {
            const Icon = plan.icon;
            return (
              <div
                key={plan.name}
                className={`bg-card rounded-xl p-8 border-2 transition-all ${
                  plan.highlight
                    ? 'border-primary shadow-[0_0_30px_rgba(0,255,148,0.2)]'
                    : 'border-border hover:border-primary/50'
                }`}
                data-testid={`plan-${plan.name.toLowerCase()}`}
              >
                <div className="flex items-center justify-between mb-6">
                  <Icon className={`h-10 w-10 ${plan.highlight ? 'text-primary' : 'text-muted-foreground'}`} />
                  {plan.current && (
                    <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full border border-primary/20" data-testid="current-plan-badge">
                      CURRENT PLAN
                    </span>
                  )}
                </div>

                <h2 className="font-heading text-3xl font-bold mb-2">{plan.name}</h2>
                <div className="mb-6">
                  <span className="font-heading text-4xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground ml-2">/ {plan.period}</span>
                </div>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start space-x-3">
                      <Check className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                {plan.current ? (
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
                    className={`w-full ${
                      plan.highlight
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_-5px_rgba(0,255,148,0.4)]'
                        : ''
                    }`}
                    data-testid={`plan-btn-${plan.name.toLowerCase()}`}
                  >
                    Contact Admin to Upgrade
                  </Button>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-12 text-center">
          <p className="text-muted-foreground">
            Need a custom plan? Contact our admin team for enterprise solutions.
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default Plans;
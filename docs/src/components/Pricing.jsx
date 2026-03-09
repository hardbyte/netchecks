import { Container } from '@/components/Container'
import { Button } from '@/components/Button'

function CheckIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M9.307 12.248a.75.75 0 1 0-1.114 1.004l1.114-1.004ZM11 15.25l-.557.502a.75.75 0 0 0 1.15-.043L11 15.25Zm4.844-5.041a.75.75 0 0 0-1.188-.918l1.188.918Zm-7.651 3.043 2.25 2.5 1.114-1.004-2.25-2.5-1.114 1.004Zm3.4 2.457 4.25-5.5-1.187-.918-4.25 5.5 1.188.918Z"
        fill="currentColor"
      />
      <circle
        cx="12"
        cy="12"
        r="8.25"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const plans = [
  {
    name: 'Open Source',
    price: 'Free',
    description:
      'For security professionals, small businesses, students, hobbyists, and open source projects.',
    href: '/docs/getting-started',
    cta: 'Get started',
    featured: true,
    features: [
      'Unlimited operator installs',
      'Unlimited NetworkAssertions',
      'HTTP, DNS, and TCP probes',
      'PolicyReports & Prometheus metrics',
      'Community support via GitHub',
    ],
  },
  {
    name: 'Compliance Pro',
    price: 'Contact us',
    description:
      'Automated compliance reporting for regulated environments.',
    href: 'https://buy.stripe.com/cN25or9rA8Ur6xa4gi',
    cta: 'Get Compliance Pro',
    featured: false,
    features: [
      'Everything in Open Source',
      'CIS Kubernetes Benchmark checks',
      'PCI-DSS v4 network controls',
      'SOC 2 network monitoring evidence',
      'Exportable compliance reports',
      'Priority support',
    ],
  },
]

export function Pricing() {
  return (
    <section id="pricing" className="bg-slate-900 py-20 sm:py-28">
      <Container>
        <div className="text-center">
          <h2 className="font-display text-3xl tracking-tight text-white sm:text-4xl">
            Simple pricing, for everyone
          </h2>
          <p className="mt-4 text-lg text-slate-400">
            Open source at its core. Compliance features when you need them.
          </p>
        </div>
        <div className="mx-auto mt-16 grid max-w-4xl grid-cols-1 gap-8 lg:grid-cols-2">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-3xl px-6 py-8 sm:px-8 ${
                plan.featured
                  ? 'bg-sky-500 ring-1 ring-sky-500'
                  : 'ring-1 ring-slate-700'
              }`}
            >
              <h3 className="font-display text-2xl text-white">
                {plan.name}
              </h3>
              <p
                className={`mt-2 text-sm ${
                  plan.featured ? 'text-sky-100' : 'text-slate-400'
                }`}
              >
                {plan.description}
              </p>
              <p className="mt-6 font-display text-4xl font-light tracking-tight text-white">
                {plan.price}
              </p>
              <ul className="mt-8 space-y-3 text-sm text-white">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex">
                    <CheckIcon
                      className={`h-6 w-6 flex-none ${
                        plan.featured ? 'text-white' : 'text-slate-400'
                      }`}
                    />
                    <span className="ml-3">{feature}</span>
                  </li>
                ))}
              </ul>
              <Button
                href={plan.href}
                variant={plan.featured ? 'primary' : 'secondary'}
                className="mt-8 w-full justify-center"
              >
                {plan.cta}
              </Button>
            </div>
          ))}
        </div>
      </Container>
    </section>
  )
}

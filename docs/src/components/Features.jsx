import { Container } from '@/components/Container'

const features = [
  {
    title: 'Proactive Monitoring',
    description:
      'Periodically probe the network to detect when security assumptions are violated. Continuous validation of live workload environments increases confidence in security controls.',
    icon: ShieldIcon,
  },
  {
    title: 'Cloud Native',
    description:
      'A Kubernetes operator configured by custom resources. Outputs use PolicyReports — an emerging standard used by Kyverno and other security tools.',
    icon: CloudIcon,
  },
  {
    title: 'Alerting and Reporting',
    description:
      'Outputs PolicyReports with Prometheus metrics. Integrate with Grafana, Slack, Discord, email, or MS Teams using Policy Reporter.',
    icon: BellIcon,
  },
  {
    title: 'Independent from Controls',
    description:
      'Verifies whether your cluster can carry out network activity, independent of how controls are implemented — NetworkPolicies, Cilium, or external firewalls.',
    icon: LockIcon,
  },
]

function ShieldIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  )
}

function CloudIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 0 0 4.5 4.5H18a3.75 3.75 0 0 0 1.332-7.257 3 3 0 0 0-3.758-3.848 5.25 5.25 0 0 0-10.233 2.33A4.502 4.502 0 0 0 2.25 15Z" />
    </svg>
  )
}

function BellIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
    </svg>
  )
}

function LockIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
    </svg>
  )
}

export function Features() {
  return (
    <section id="features" className="bg-slate-50 py-20 dark:bg-slate-800/50 sm:py-28">
      <Container>
        <div className="text-center">
          <h2 className="font-display text-3xl tracking-tight text-slate-900 dark:text-white sm:text-4xl">
            Concerned your security controls could be weakened?
          </h2>
          <p className="mt-4 text-lg text-slate-600 dark:text-slate-400">
            Actively test your cloud infrastructure with automated, declarative
            network assertions.
          </p>
        </div>
        <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-700 dark:bg-slate-800"
            >
              <feature.icon className="h-8 w-8 text-sky-500" />
              <h3 className="mt-4 font-display text-lg font-medium text-slate-900 dark:text-white">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  )
}

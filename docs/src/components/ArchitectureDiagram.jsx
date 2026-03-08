export function ArchitectureDiagram() {
  return (
    <div className="not-prose my-10 overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-sky-50 shadow-xl shadow-slate-900/5 dark:border-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
      <div className="border-b border-slate-200/80 bg-white/80 px-6 py-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
        <p className="m-0 font-display text-lg text-slate-900 dark:text-white">
          Netchecks high-level lifecycle
        </p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          The operator watches NetworkAssertions, schedules probe jobs, collects
          results, and publishes PolicyReports.
        </p>
      </div>

      <div className="px-5 py-6 sm:px-6">
        {/* External services row */}
        <div className="rounded-2xl border border-slate-200/70 bg-slate-50/70 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/40">
          <p className="m-0 text-center text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
            External services
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <DiagramChip
              title="DNS"
              subtitle="e.g. CloudFlare, Google"
              tone="slate"
            />
            <DiagramChip
              title="HTTP endpoints"
              subtitle="externally hosted services"
              tone="slate"
            />
            <DiagramChip
              title="TCP services"
              subtitle="arbitrary host:port targets"
              tone="slate"
            />
          </div>
        </div>

        <div className="flex justify-center py-3">
          <VerticalArrow />
        </div>

        {/* Kubernetes cluster */}
        <div className="rounded-[2rem] border border-sky-200 bg-white/90 p-5 shadow-lg shadow-slate-900/5 dark:border-sky-900/60 dark:bg-slate-900/80">
          <p className="m-0 text-center text-xs font-semibold uppercase tracking-[0.2em] text-sky-700 dark:text-sky-300">
            Kubernetes cluster
          </p>

          {/* Kubernetes API resources */}
          <div className="mt-4 rounded-2xl border border-sky-200/70 bg-sky-50/60 px-4 py-3 dark:border-sky-900/60 dark:bg-sky-950/30">
            <p className="m-0 text-center text-xs font-semibold uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
              Kubernetes API
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <DiagramChip
                title="NetworkAssertion"
                subtitle="custom resource defining tests"
                tone="sky"
              />
              <DiagramChip
                title="CronJob / Job"
                subtitle="scheduled probe execution"
                tone="sky"
              />
              <DiagramChip
                title="PolicyReport"
                subtitle="assertion results per resource"
                tone="emerald"
              />
            </div>
          </div>

          <div className="flex justify-center py-3">
            <VerticalArrow />
          </div>

          {/* Operator and probe */}
          <div className="grid gap-4 md:grid-cols-2">
            <DiagramPanel
              eyebrow="Operator"
              title="netchecks-operator"
              tone="sky"
              items={[
                'Watches NetworkAssertion resources',
                'Creates CronJobs (or Jobs) for each assertion',
                'Parses results from probe Pod logs',
                'Creates and updates PolicyReport resources',
              ]}
            />
            <DiagramPanel
              eyebrow="Probe"
              title="netchecks probe pod"
              tone="amber"
              items={[
                'Runs DNS, HTTP, and TCP probes',
                'Validates responses with CEL expressions',
                'Mounts external data (Secrets, ConfigMaps)',
                'Outputs structured JSON results',
              ]}
            />
          </div>

          <div className="flex justify-center py-3">
            <VerticalArrow />
          </div>

          {/* Policy Reporter */}
          <DiagramTerminal
            title="Policy Reporter (optional)"
            subtitle="Exposes metrics, dashboards, and notifications from PolicyReport resources"
            tone="emerald"
          />
        </div>

        <div className="flex justify-center py-3">
          <VerticalArrow />
        </div>

        {/* Outputs */}
        <div className="grid gap-4 md:grid-cols-3">
          <DiagramTerminal
            title="Prometheus metrics"
            subtitle="scrape PolicyReport status"
            tone="slate"
          />
          <DiagramTerminal
            title="Grafana dashboards"
            subtitle="visualize assertion results"
            tone="slate"
          />
          <DiagramTerminal
            title="Alerts & notifications"
            subtitle="Slack, email, webhooks"
            tone="amber"
          />
        </div>
      </div>
    </div>
  )
}

function DiagramChip({ title, subtitle, tone }) {
  const tones = {
    sky: 'border-sky-200 bg-white text-sky-900 dark:border-sky-900/60 dark:bg-slate-900/80 dark:text-sky-200',
    amber:
      'border-amber-200 bg-white text-amber-900 dark:border-amber-900/60 dark:bg-slate-900/80 dark:text-amber-200',
    emerald:
      'border-emerald-200 bg-white text-emerald-900 dark:border-emerald-900/60 dark:bg-slate-900/80 dark:text-emerald-200',
    slate:
      'border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-200',
  }

  return (
    <div className={`rounded-2xl border px-3 py-3 text-left ${tones[tone]}`}>
      <p className="m-0 text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs opacity-80">{subtitle}</p>
    </div>
  )
}

function DiagramPanel({ eyebrow, title, items, tone }) {
  const tones = {
    sky: 'border-sky-200/80 bg-sky-50/80 dark:border-sky-900/60 dark:bg-sky-950/30',
    slate: 'border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950/40',
    amber:
      'border-amber-200/80 bg-amber-50/80 dark:border-amber-900/60 dark:bg-amber-950/20',
    emerald:
      'border-emerald-200/80 bg-emerald-50/80 dark:border-emerald-900/60 dark:bg-emerald-950/20',
  }

  return (
    <div className={`rounded-3xl border p-4 ${tones[tone]}`}>
      <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
        {eyebrow}
      </p>
      <p className="mt-2 font-display text-lg text-slate-900 dark:text-white">
        {title}
      </p>
      <ul className="mt-4 space-y-2 text-sm text-slate-700 dark:text-slate-300">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-1 h-2 w-2 flex-none rounded-full bg-slate-400/80 dark:bg-slate-500" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function DiagramTerminal({ title, subtitle, tone }) {
  const tones = {
    slate:
      'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/80',
    emerald:
      'border-emerald-200 bg-white dark:border-emerald-900/60 dark:bg-slate-900/80',
    amber:
      'border-amber-200 bg-white dark:border-amber-900/60 dark:bg-slate-900/80',
  }

  return (
    <div className={`rounded-3xl border px-5 py-4 shadow-sm ${tones[tone]}`}>
      <p className="m-0 font-display text-lg text-slate-900 dark:text-white">
        {title}
      </p>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        {subtitle}
      </p>
    </div>
  )
}

function VerticalArrow() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 48"
      className="h-10 w-5 text-sky-500 dark:text-sky-400"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2v38" />
      <path d="M6 34l6 10 6-10" />
    </svg>
  )
}

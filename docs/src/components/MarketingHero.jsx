import { Button } from '@/components/Button'
import { HeroBackground } from '@/components/HeroBackground'
import { Container } from '@/components/Container'

export function MarketingHero() {
  return (
    <div className="overflow-hidden bg-slate-900">
      <div className="py-20 sm:px-2 lg:relative lg:py-28 lg:px-0">
        <div className="mx-auto max-w-2xl items-center px-4 lg:max-w-8xl lg:px-8 xl:px-12">
          <div className="relative z-10 text-center">
            <div className="absolute inset-0 -z-10 flex justify-center">
              <HeroBackground className="opacity-30 w-full max-w-3xl" />
            </div>
            <div className="relative">
              <h1 className="inline bg-gradient-to-r from-indigo-200 via-sky-400 to-indigo-200 bg-clip-text font-display text-5xl tracking-tight text-transparent sm:text-7xl">
                Verify your security controls are working
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-lg tracking-tight text-slate-400">
                Netchecks proactively tests your Kubernetes network policies and
                security controls. Cloud native, policy as code, no assumptions
                about your implementation.
              </p>
              <div className="mt-10 flex justify-center gap-4">
                <Button href="/docs/getting-started">Get started</Button>
                <Button
                  href="https://github.com/hardbyte/netchecks"
                  variant="secondary"
                >
                  View on GitHub
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

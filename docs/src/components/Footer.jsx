import Link from 'next/link'
import { Container } from '@/components/Container'
import { Logomark } from '@/components/Logo'

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white py-12 dark:border-slate-800 dark:bg-slate-900">
      <Container>
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
          <div className="flex items-center gap-3">
            <Logomark className="h-7 w-7" />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              Netchecks
            </span>
          </div>
          <nav className="flex gap-6 text-sm text-slate-600 dark:text-slate-400">
            <Link href="/docs/getting-started" className="hover:text-slate-900 dark:hover:text-white">
              Docs
            </Link>
            <Link href="/docs/compliance" className="hover:text-slate-900 dark:hover:text-white">
              Compliance
            </Link>
            <Link href="https://github.com/hardbyte/netchecks" className="hover:text-slate-900 dark:hover:text-white">
              GitHub
            </Link>
          </nav>
          <p className="text-sm text-slate-500 dark:text-slate-500">
            &copy; {new Date().getFullYear()} Netchecks
          </p>
        </div>
      </Container>
    </footer>
  )
}

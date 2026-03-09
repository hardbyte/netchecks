import Head from 'next/head'
import { MarketingHero } from '@/components/MarketingHero'
import { Features } from '@/components/Features'
import { Pricing } from '@/components/Pricing'
import { Footer } from '@/components/Footer'

export default function IndexPage() {
  return (
    <>
      <Head>
        <title>Netchecks - Verify your security controls are working</title>
        <meta
          name="description"
          content="Netchecks proactively tests your Kubernetes network policies and security controls. Cloud native, policy as code."
        />
      </Head>
      <MarketingHero />
      <Features />
      <Pricing />
      <Footer />
    </>
  )
}

IndexPage.getLayout = (page) => page

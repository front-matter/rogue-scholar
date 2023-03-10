import 'focus-visible'
import '../styles/tailwind.css'

import { Inter } from '@next/font/google'
import { createBrowserSupabaseClient } from '@supabase/auth-helpers-nextjs'
import { SessionContextProvider } from '@supabase/auth-helpers-react'
import PlausibleProvider from 'next-plausible'
import { useState } from 'react'

// If loading a variable font, you don't need to specify the font weight
const inter = Inter({ subsets: ['latin'] })

export default function App({ Component, pageProps }) {
  // Create a new supabase browser client on every first render.
  const [supabaseClient] = useState(() => createBrowserSupabaseClient())

  return (
    <PlausibleProvider domain="rogue-scholar.org">
      <SessionContextProvider
        supabaseClient={supabaseClient}
        initialSession={pageProps.initialSession}
      >
        <main className={inter.className}>
          <Component {...pageProps} />
        </main>
      </SessionContextProvider>
    </PlausibleProvider>
  )
}

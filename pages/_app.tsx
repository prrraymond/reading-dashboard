import './globals.css';
import { useEffect } from 'react';
import mixpanel from 'mixpanel-browser';
import type { AppProps } from 'next/app';

function MyApp({ Component, pageProps }: AppProps) {
  useEffect(() => {
    // Initialize Mixpanel only once when the app loads
    mixpanel.init(process.env.NEXT_PUBLIC_MIXPANEL_TOKEN || '', {
      debug: process.env.NODE_ENV === 'development',
      track_pageview: true,
      persistence: 'localStorage',
    });
  }, []);

  return <Component {...pageProps} />;
}

export default MyApp;
# Deployment

`fangye.cc` is a static Astro site. It can be deployed to Cloudflare Pages, Vercel, Netlify, or any static host.

## Local Commands

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Build the production site:

```powershell
npm run build
```

Preview the production build:

```powershell
npm run preview
```

## Cloudflare Pages

Recommended settings:

- Framework preset: Astro
- Build command: `npm run build`
- Output directory: `dist`
- Node.js version: 20 or newer

After the first successful deployment, add the custom domain `fangye.cc` in Cloudflare Pages.

## Domain Binding

The exact DNS records depend on the hosting provider.

For Cloudflare Pages:

1. Add `fangye.cc` as a custom domain in the Pages project.
2. Follow Cloudflare's prompted DNS setup.
3. Wait for DNS and HTTPS certificate activation.
4. Set `www.fangye.cc` as an optional redirect or additional custom domain if needed.

For Vercel or Netlify, add `fangye.cc` in that provider's domain settings, then create the DNS records they show in their dashboard.

## Notes

- The Astro `site` value is set to `https://fangye.cc` in `astro.config.mjs`.
- Sitemap output is generated during `npm run build`.
- RSS is available at `/rss.xml`.

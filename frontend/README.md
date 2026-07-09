# Adaptive Learning AI Frontend

Next.js 15 product-demo frontend for the Adaptive Learning AI Platform.

## Local setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to the deployed FastAPI backend URL. The local default points to `http://localhost:8000`; `vercel.json` sets the Render production URL.

## Verification

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

The app is Vercel-ready. Override `NEXT_PUBLIC_API_URL` in Vercel only if the Render service URL changes.

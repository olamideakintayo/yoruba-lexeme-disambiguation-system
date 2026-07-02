# Render Backend + Vercel Frontend Deployment

Use Render for the FastAPI backend and managed PostgreSQL. Use Vercel for the React frontend.

## Render Backend

1. Push this repo to GitHub.
2. In Render, choose **New +** > **Blueprint**.
3. Connect the GitHub repo.
4. Render will read `render.yaml` and create:
   - `yoruba-lexeme-api`
   - `yoruba-lexeme-db`
5. Before the final deploy, replace the placeholder `FRONTEND_ORIGIN` value with your Vercel URL:
   ```env
   FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
   ```
6. Deploy the blueprint.

Render provides `DATABASE_URL` automatically from the managed PostgreSQL database. The backend converts Render's `postgresql://` URL into SQLAlchemy's async `postgresql+psycopg://` format at startup.

The deployment pins Python to `3.11.9` through `render.yaml` and `.python-version` files. This avoids Python 3.14 build failures from compiled dependencies such as `greenlet`.

## Backend URL

After deploy, Render gives a backend URL like:

```text
https://yoruba-lexeme-api.onrender.com
```

Verify:

```bash
curl https://yoruba-lexeme-api.onrender.com/api/health
curl https://yoruba-lexeme-api.onrender.com/api/keyboard
curl "https://yoruba-lexeme-api.onrender.com/api/search?q=owo"
```

## Vercel Frontend

Create a Vercel project from the same GitHub repo:

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable:
  ```env
  VITE_API_BASE_URL=https://yoruba-lexeme-api.onrender.com
  ```

If Vercel asks for a multi-service `vercel.json`, do not use the backend service template. The backend is deployed on Render, so Vercel should deploy only the `frontend` project. This repo includes `frontend/vercel.json` for the Vite frontend.

If the keyboard does not show and search says `Failed to fetch`, check these two environment variables first:

- In Vercel, `VITE_API_BASE_URL` must be the Render backend URL, for example:
  ```env
  VITE_API_BASE_URL=https://yoruba-lexeme-disambiguation-system.onrender.com
  ```
- In Render, `FRONTEND_ORIGIN` must be the Vercel frontend URL, for example:
  ```env
  FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
  ```

After changing either variable, redeploy the affected service. Vite reads `VITE_API_BASE_URL` only at build time, so changing it in Vercel requires a new Vercel deployment.

Deploy the frontend. Then copy the final Vercel URL back into Render as:

```env
FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
```

Redeploy the Render backend after changing `FRONTEND_ORIGIN`.

## About The 21-Hour Reboot

Do not use the EC2 reboot cron on Render. Render manages the container lifecycle and may restart services automatically. If a scheduled refresh is still needed later, use a Render cron job or external uptime monitor to call a health endpoint, but do not try to reboot the server because there is no EC2 server to reboot.

## Notes

- Render free services can sleep after inactivity, so the first request may be slow.
- The backend start command runs migrations and dictionary seed scripts on each deploy. The import code is idempotent, so redeploys keep the database usable.

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

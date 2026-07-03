# Production Runbook — On İki Sepet (KUT Finans)

Bu belge Cloud Run + Cloud SQL PostgreSQL + GCS ortamında operasyonel işlemleri açıklar.

## Mimari

| Bileşen | Servis |
|---------|--------|
| Uygulama | Google Cloud Run (Docker + Gunicorn) |
| Veritabanı | Cloud SQL PostgreSQL |
| Fiş dosyaları | Google Cloud Storage (`GCS_MEDIA_BUCKET_NAME`) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Deploy | GitHub Actions (`.github/workflows/deploy-gcp.yml`, manuel) |

## Ortam değişkenleri

```bash
DJANGO_SETTINGS_MODULE=config.production_settings
DJANGO_SECRET_KEY=<Secret Manager>
DJANGO_ALLOWED_HOSTS=finans.kutkilisesi.org
DATABASE_URL=postgres://user:pass@/oniki_sepet?host=/cloudsql/PROJECT:REGION:INSTANCE
DJANGO_FILE_STORAGE_BACKEND=gcs
GCS_MEDIA_BUCKET_NAME=kut-finans-media
DJANGO_SECURE_SSL_REDIRECT=true
```

Cloud Run, Cloud SQL bağlantısı için `--add-cloudsql-instances` ile Unix socket kullanır.

## Health check

- **Endpoint:** `GET /health/`
- **Başarılı yanıt:** `200 {"status": "ok"}`
- **Veritabanı erişilemez:** `503 {"status": "unavailable"}`

Cloud Run startup/liveness probe olarak yapılandırın:

```bash
gcloud run services update kut-finans \
  --region europe-west1 \
  --startup-probe httpGet.path=/health/,httpGet.port=8000,initialDelaySeconds=10,periodSeconds=10,failureThreshold=3
```

Manuel kontrol:

```bash
curl -sf "https://finans.kutkilisesi.org/health/"
```

## Deploy pipeline

1. GitHub repo secret'larını tanımlayın:
   - `GCP_PROJECT_ID`, `GCP_ARTIFACT_REGISTRY`
   - `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`
   - `CLOUD_SQL_INSTANCE`, `GCS_MEDIA_BUCKET_NAME`, `DJANGO_ALLOWED_HOSTS`
2. Secret Manager'da `DJANGO_SECRET_KEY` ve `DATABASE_URL` oluşturun.
3. Actions → **Deploy to GCP** → **Run workflow** ile deploy edin.
4. Workflow image build → Artifact Registry push → Cloud Run deploy → `/health/` doğrulaması yapar.

Container başlangıcında `docker/entrypoint.sh` otomatik `migrate --noinput` çalıştırır.

## Backup (Cloud SQL)

### Otomatik (önerilen)

Cloud SQL yedekleme penceresi:

```bash
gcloud sql instances patch INSTANCE_NAME \
  --backup-start-time=03:00 \
  --retained-backups-count=14
```

### Manuel pg_dump (Cloud SQL Auth Proxy ile)

```bash
cloud-sql-proxy PROJECT:REGION:INSTANCE &
export DATABASE_URL="postgres://USER:PASS@127.0.0.1:5432/oniki_sepet"
./scripts/backup_database.sh
```

Yedekler `./backups/oniki_sepet_YYYYMMDD_HHMMSS.dump` formatında oluşur.

### Restore

```bash
pg_restore --clean --if-exists --no-owner \
  --dbname="${DATABASE_URL}" backups/oniki_sepet_YYYYMMDD_HHMMSS.dump
```

Restore öncesi uygulamayı durdurun veya bakım moduna alın.

## Olay müdahalesi

| Belirti | Kontrol | Aksiyon |
|---------|---------|---------|
| 503 `/health/` | Cloud SQL durumu | Instance restart, bağlantı limiti |
| 5xx uygulama | Cloud Run logları | `gcloud run services logs read kut-finans` |
| Fiş yüklenmiyor | GCS bucket IAM | Service account'a `storage.objectAdmin` |
| Migration hatası | Deploy logları | `gcloud run jobs` veya geçici revision ile `migrate` |

## Rollback

```bash
gcloud run services update-traffic kut-finans \
  --region europe-west1 \
  --to-revisions PREVIOUS_REVISION=100
```

## Yerel Docker doğrulama

```bash
docker build -t kut-finans .
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=local-test-key \
  -e DJANGO_ALLOWED_HOSTS=localhost \
  -e DATABASE_URL=postgres://user:pass@host.docker.internal:5432/oniki_sepet \
  kut-finans
curl http://localhost:8000/health/
```

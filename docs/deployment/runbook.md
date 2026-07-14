# Production Runbook — On İki Sepet (KUT Finans)

Bu belge Cloud Run + Cloud SQL PostgreSQL + GCS ortamında operasyonel işlemleri açıklar.

## Mimari

| Bileşen | Servis |
|---------|--------|
| Uygulama | Google Cloud Run (Docker + Gunicorn) |
| Veritabanı | Cloud SQL PostgreSQL |
| Fiş dosyaları | Google Cloud Storage (`GCS_MEDIA_BUCKET_NAME`) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Deploy | GCP Cloud Build trigger (`cloudbuild.yaml`, main'e her push'ta otomatik) |
| Proje / Instance | `lifebalance-nuxt` / `lb-db2` (us-central1) |

## Ortam değişkenleri

```bash
DJANGO_SETTINGS_MODULE=config.production_settings
DJANGO_SECRET_KEY=<Secret Manager>
DJANGO_ALLOWED_HOSTS=.run.app
DATABASE_URL=postgres://user:pass@/oniki_sepet?host=/cloudsql/PROJECT:REGION:INSTANCE
DJANGO_FILE_STORAGE_BACKEND=gcs
GCS_MEDIA_BUCKET_NAME=kut-finans-media
DJANGO_SECURE_SSL_REDIRECT=true
```

`DJANGO_ALLOWED_HOSTS=.run.app` (baştaki nokta Django'da subdomain wildcard'dır) — servisin
gerçek Cloud Run URL'si ilk deploy'dan önce bilinmiyor, bu yüzden herhangi bir `*.run.app`
host'una izin veriyoruz. Özel domain (`finans.kutkilisesi.org` vb.) bağlanınca bunu tam
domain'e daraltın.

Cloud Run, Cloud SQL bağlantısı için `--add-cloudsql-instances` ile Unix socket kullanır.

## Health check

- **Endpoint:** `GET /health/`
- **Başarılı yanıt:** `200 {"status": "ok"}`
- **Veritabanı erişilemez:** `503 {"status": "unavailable"}`

Cloud Run startup/liveness probe olarak yapılandırın:

```bash
gcloud run services update kut-finans \
  --region us-central1 \
  --startup-probe httpGet.path=/health/,httpGet.port=8000,initialDelaySeconds=10,periodSeconds=10,failureThreshold=3
```

Manuel kontrol (ilk deploy sonrası gerçek URL için `gcloud run services describe kut-finans
--region us-central1 --format='value(status.url)'`):

```bash
curl -sf "$(gcloud run services describe kut-finans --region us-central1 --format='value(status.url)')/health/"
```

## Deploy pipeline

Deploy tamamen otomatik: `main` branch'ine her push, GCP Cloud Build trigger'ını tetikler
(`cloudbuild.yaml`). Manuel adım yok.

Pipeline adımları (`cloudbuild.yaml`):
1. Docker image build + `us.gcr.io/lifebalance-nuxt/kut-finans` push (`:$COMMIT_SHA` ve `:latest`)
2. **Pre-deploy migration** — `exec-wrapper` ile Cloud SQL soketi üzerinden `manage.py migrate --noinput`
   (container başlangıcında migration ÇALIŞTIRILMAZ — eşzamanlı cold start'larda migration
   yarışını önlemek için)
3. `gcloud run deploy kut-finans` (region `us-central1`, `--add-cloudsql-instances`,
   secrets: `oniki-sepet-django-secret-key`, `oniki-sepet-database-url`)

Sırlar zaten Secret Manager'da: `oniki-sepet-django-secret-key`, `oniki-sepet-database-url`.
Veritabanı kullanıcısı `oniki_sepet_app` `oniki_sepet` veritabanının sahibidir; `PUBLIC`
erişimi bu veritabanı üzerinde REVOKE edildi, yani diğer instance kullanıcıları bu DB'ye
erişemez. Not: Cloud SQL Postgres'te her uygulama kullanıcısı `cloudsqlsuperuser` grubunun
üyesi olarak oluşturulur — bu, `oniki_sepet_app`'in teoride instance'taki diğer DB'lere
bağlanabildiği anlamına gelir (platformun kendi kısıtı, tam izolasyon mümkün değil). Pratikte
risk düşük: kimlik bilgileri yalnızca bu uygulamanın Secret Manager sırlarında bulunuyor.

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
  --region us-central1 \
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

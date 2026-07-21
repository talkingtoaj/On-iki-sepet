AMOUNT_MUST_BE_POSITIVE = "Tutar 0'dan büyük olmalıdır."

INCOME_REQUIRES_TARGET_ACCOUNT = "Gelir işlemleri için hedef hesap gereklidir."
INCOME_REQUIRES_INCOME_CATEGORY = "Gelir işlemleri için gelir kategorisi gereklidir."
INCOME_REQUIRES_ACCOUNT = "Gelir işlemleri için bir hesap seçilmelidir."

EXPENSE_REQUIRES_SOURCE_ACCOUNT = "Gider işlemleri için kaynak hesap gereklidir."
EXPENSE_REQUIRES_EXPENSE_CATEGORY = "Gider işlemleri için gider kategorisi gereklidir."
EXPENSE_REQUIRES_ACCOUNT = "Gider işlemleri için bir hesap seçilmelidir."

TRANSFER_REQUIRES_SOURCE_ACCOUNT = "Transfer işlemleri için kaynak hesap gereklidir."
TRANSFER_REQUIRES_TARGET_ACCOUNT = "Transfer işlemleri için hedef hesap gereklidir."
TRANSFER_ACCOUNTS_MUST_DIFFER = "Transfer hesapları farklı olmalıdır."
TRANSFER_CROSS_CURRENCY_NOT_SUPPORTED = (
    "Farklı para birimleri arasında transfer MVP'de desteklenmiyor."
)

RECEIPT_TRANSACTION_REQUIRED = "Bu alan zorunludur."
RECEIPTS_EXPENSE_ONLY = "Fişler yalnızca gider işlemleri için eklenebilir."
RECEIPTS_EXPENSE_ACCOUNT_NOT_SUPPORTED = (
    "Fişler yalnızca nakit veya banka gider işlemleri için eklenebilir."
)

UNSUPPORTED_RECEIPT_FILE = (
    "Desteklenmeyen fiş dosya türü. Lütfen PDF, JPG, JPEG veya PNG yükleyin."
)

OPENING_BALANCE_IMMUTABLE = "Açılış bakiyesi oluşturulduktan sonra değiştirilemez."

PERMISSION_CREATE_CATEGORIES = "Kategori oluşturma yetkiniz yok."
PERMISSION_CREATE_ACCOUNTS = "Hesap oluşturma yetkiniz yok."
PERMISSION_REQUEST_ACCOUNT_CHANGES = "Hesap değişikliği talep etme yetkiniz yok."
PERMISSION_CREATE_CASH_EXPENSES = "Nakit gider oluşturma yetkiniz yok."
PERMISSION_CREATE_CASH_INCOME = "Nakit gelir oluşturma yetkiniz yok."
PERMISSION_CREATE_BANK_EXPENSES = "Banka gideri oluşturma yetkiniz yok."
PERMISSION_CREATE_ONLINE_DONATION = "Online bağış geliri oluşturma yetkiniz yok."
PERMISSION_CREATE_TRANSFERS = "Transfer oluşturma yetkiniz yok."
PERMISSION_IMPORT_BANK_STATEMENTS = "Banka ekstresi yükleme yetkiniz yok."
PERMISSION_CONFIRM_BANK_IMPORT = "Banka ekstresi onaylama yetkiniz yok."
PERMISSION_EDIT_TRANSACTIONS = "İşlem düzenleme yetkiniz yok."
TRANSACTION_RESUBMITTED = "İşlem düzeltildi ve yeniden onaya gönderildi."
REJECTION_REASON_REQUIRED = "Red nedeni zorunludur."
PERMISSION_APPROVE_TRANSACTIONS = "İşlem onaylama yetkiniz yok."
BULK_APPROVE_NONE_SELECTED = "Onaylanacak işlem seçilmedi."


def bulk_approve_success_message(count):
    return f"{count} işlem onaylandı."
PERMISSION_ACCESS_APPLICATION = "Bu uygulamaya erişim yetkiniz yok."
PERMISSION_MANAGE_USERS = "Kullanıcı yönetimi yetkiniz yok."
PERMISSION_VIEW_OPERATIONAL_PAGES = "Bu sayfayı görüntüleme yetkiniz yok."
PERMISSION_VIEW_RECORD_GUIDE = "Kayıt rehberini görüntüleme yetkiniz yok."

INCOME_TO_EXPENSE_ACCOUNT_FORBIDDEN = "Gelir işlemleri gider hesabına kaydedilemez."
EXPENSE_FROM_ONLINE_DONATION_FORBIDDEN = "Online bağış hesabından gider yapılamaz."
TRANSFER_TO_ONLINE_DONATION_FORBIDDEN = (
    "Online bağış hesabına transfer yapılamaz; gelir olarak kaydedin."
)

UNSUPPORTED_BANK_IMPORT_FILE = (
    "Desteklenmeyen dosya türü. Lütfen CSV, Excel (.xlsx) veya PDF yükleyin."
)
BANK_IMPORT_PDF_NO_PARSEABLE_ROWS = (
    "PDF dosyasından tablo okunamadı. Enpara gibi banka ekstrelerinde "
    "Tarih, Hareket tipi, Açıklama ve İşlem Tutarı sütunları bulunmalıdır."
)
BANK_IMPORT_PDF_REQUIRES_ACCOUNT = (
    "PDF ekstre yüklerken hangi hesaba ait olduğunu seçmelisiniz."
)
BANK_IMPORT_MISSING_COLUMNS = "Dosyada gerekli sütunlar eksik: {columns}."
BANK_IMPORT_EMPTY_FILE = "Dosyada işlenecek satır bulunamadı."
BANK_IMPORT_ALREADY_CONFIRMED = "Bu ekstre zaten kaydedildi."
BANK_IMPORT_NOT_READY = "Kaydedilecek geçerli satır bulunamadı."
BANK_IMPORT_ROW_INVALID = "Satır {row_number} geçersiz: {error}"
BANK_IMPORT_ROW_REQUIRES_TYPE = "Satır {row_number} için işlem türü seçilmelidir."
BANK_IMPORT_ROW_REQUIRES_CATEGORY = "Satır {row_number} için kategori seçilmelidir."
BANK_IMPORT_ROW_REQUIRES_TARGET_ACCOUNT = (
    "Satır {row_number} için hedef hesap seçilmelidir."
)
ONLINE_DONATION_IMPORT_CATEGORY_NAME = "Online Bağış"
BANK_IMPORT_UPLOAD_HELP_CSV = (
    "CSV veya Excel için örnek şablonu indirip hesap adını sistemdekiyle aynı yazın."
)
BANK_IMPORT_UPLOAD_HELP_PDF = (
    "PDF okunmuyorsa: hesabın seçili olduğundan emin olun; "
    "Tarih, Hareket tipi, Açıklama ve İşlem Tutarı sütunları olmalı; "
    "olmuyorsa bankadan CSV/Excel indirin."
)


def bank_import_partial_success_message(imported_count, pending_count):
    return (
        f"{imported_count} işlem kaydedildi. "
        f"{pending_count} satır daha sonra sınıflandırılmak üzere bekliyor."
    )


def bank_import_full_success_message(imported_count):
    return f"{imported_count} işlem içe aktarıldı."

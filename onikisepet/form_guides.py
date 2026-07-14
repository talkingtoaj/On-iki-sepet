FORM_GUIDES = {
    "cash_income": {
        "title": "Nakit Gelir",
        "intro": (
            "Defter'e elden alınan bağışları buraya girin. "
            "Onay sonrası rapora yansır."
        ),
    },
    "cash_expense": {
        "title": "Nakit Gider",
        "intro": (
            "Kasadan yapılan harcamaları buraya girin. "
            "Makbuz yüklemeniz gerekir."
        ),
    },
    "bank_expense": {
        "title": "Banka Gideri",
        "intro": (
            "Banka hesabından yapılan ödemeleri buraya girin. "
            "Dekont yüklemek isteğe bağlıdır."
        ),
    },
    "online_donation": {
        "title": "Online Bağış",
        "intro": (
            "PayPal, iyzico ve benzeri platformlardan gelen bağışları buraya girin. "
            "Onay sonrası rapora yansır."
        ),
    },
    "transfer": {
        "title": "Transfer",
        "intro": (
            "Hesaplar arası para hareketini buraya girin. "
            "Transfer gelir veya gider sayılmaz."
        ),
        "notice": "Transferler onay sonrası hesap bakiyelerine yansır.",
    },
    "bank_import": {
        "title": "Ekstre Yükle",
        "intro": (
            "Banka ekstresini CSV, Excel veya PDF olarak yükleyin. "
            "Satırları sınıflandırıp onay sonrası işlem olarak kaydedin."
        ),
    },
}

RECORD_TYPE_GUIDE = {
    "intro": (
        "Doğru kayıt formunu seçmek için önce paranın nereden geldiğini "
        "veya nereye gittiğini düşünün."
    ),
    "groups": [
        {
            "title": "Elden / Kasa (Defter)",
            "summary": "Nakit kasada toplanan veya kasadan yapılan işlemler",
            "items": [
                {
                    "guide_key": "cash_income",
                    "url_name": "cash_income_create",
                    "when": "Elden bağış veya nakit gelir alındığında",
                },
                {
                    "guide_key": "cash_expense",
                    "url_name": "cash_expense_create",
                    "when": "Kasadan nakit gider ödendiğinde",
                },
            ],
        },
        {
            "title": "Banka",
            "summary": "Banka hesaplarındaki gelir ve gider hareketleri",
            "items": [
                {
                    "guide_key": "online_donation",
                    "url_name": "online_donation_income_create",
                    "when": "Online platformdan bağış geldiğinde",
                },
                {
                    "guide_key": "bank_expense",
                    "url_name": "bank_expense_create",
                    "when": "Banka hesabından tek tek gider kaydı girildiğinde",
                },
                {
                    "guide_key": "bank_import",
                    "url_name": "import_new",
                    "when": "Banka ekstresinden toplu kayıt aktarılacağında",
                },
            ],
        },
        {
            "title": "Hesaplar arası",
            "summary": "Gelir veya gider sayılmayan para transferleri",
            "items": [
                {
                    "guide_key": "transfer",
                    "url_name": "transfer_create",
                    "when": "Para bir hesaptan diğerine taşındığında",
                },
            ],
        },
    ],
}


def get_form_guide(key):
    try:
        return FORM_GUIDES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown form guide key: {key}") from exc


def get_record_type_guide():
    return RECORD_TYPE_GUIDE


def build_record_type_guide_context():
    from django.urls import reverse

    guide = get_record_type_guide()
    return {
        "intro": guide["intro"],
        "groups": [
            {
                "title": group["title"],
                "summary": group["summary"],
                "items": [
                    {
                        "when": item["when"],
                        "guide": get_form_guide(item["guide_key"]),
                        "url": reverse(item["url_name"]),
                    }
                    for item in group["items"]
                ],
            }
            for group in guide["groups"]
        ],
    }

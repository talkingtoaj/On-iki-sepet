from onikisepet.models import Category

KUT_CATEGORIES = [
    {
        "name": "Bağış",
        "category_type": Category.CategoryType.INCOME,
    },
    {
        "name": "Online Bağış",
        "category_type": Category.CategoryType.INCOME,
    },
    {
        "name": "Özel Destek",
        "category_type": Category.CategoryType.INCOME,
    },
    {
        "name": "Kira",
        "category_type": Category.CategoryType.EXPENSE,
    },
    {
        "name": "Faturalar",
        "category_type": Category.CategoryType.EXPENSE,
    },
    {
        "name": "Personel",
        "category_type": Category.CategoryType.EXPENSE,
    },
    {
        "name": "Yardım",
        "category_type": Category.CategoryType.EXPENSE,
    },
    {
        "name": "Ofis ve Malzeme",
        "category_type": Category.CategoryType.EXPENSE,
    },
]


def load_kut_categories():
    created_count = 0

    for spec in KUT_CATEGORIES:
        _category, created = Category.objects.get_or_create(
            name=spec["name"],
            defaults={
                "category_type": spec["category_type"],
                "is_active": True,
            },
        )
        if created:
            created_count += 1

    return created_count

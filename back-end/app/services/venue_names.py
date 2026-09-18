import unicodedata


def normalize_venue_name(value: str | None) -> str:
    name = "".join(unicodedata.normalize("NFKC", value or "").split())
    return {
        "美育馆研讨室(西)": "大学生研讨室1",
        "美育馆研讨室(东)": "大学生研讨室2",
    }.get(name, name)

"""BCP 47 locale validation, script detection and lint category settings."""

from typing import Any, Dict, List

from langcodes import Language
from langcodes.tag_parser import LanguageTagError

SUPPORTED_LOCALES = ("en-US", "en-GB", "zh-CN", "zh-HK", "zh-TW", "off")
LEGACY_LOCALES = {"en-uk": "en-GB", "none": "off"}
DEFAULT_CATEGORIES = {"variant": True, "grammar": False, "style": False}
HANS_MARKERS = frozenset('汉简体语电说国学会东车马鸟门问间数云无来个们这')
HANT_MARKERS = frozenset('漢簡體語電說國學會東車馬鳥門問間數雲無來個們這')


def normalize_locale(value: str) -> str:
    """Normalises a supported BCP 47 tag and rejects legacy values."""
    if not isinstance(value, str):
        raise ValueError("Locale must be a string")
    tag = value.strip()
    lowered = tag.lower()
    if lowered in LEGACY_LOCALES:
        raise ValueError(
            f"Legacy locale '{tag}' is not valid. Use '{LEGACY_LOCALES[lowered]}'."
        )
    if lowered == 'off':
        return 'off'
    try:
        normalized = str(Language.get(tag))
    except LanguageTagError as error:
        raise ValueError(f"Invalid locale '{tag}'") from error
    if normalized not in SUPPORTED_LOCALES:
        raise ValueError(
            f"Unsupported locale '{tag}'. Use one of {', '.join(SUPPORTED_LOCALES)}."
        )
    return normalized


def detect_script(text: str) -> str:
    """Returns hans, hant, mixed or latin from marker characters."""
    hans = sum(1 for char in text if char in HANS_MARKERS)
    hant = sum(1 for char in text if char in HANT_MARKERS)
    if hans and hant:
        return 'mixed'
    if hans:
        return 'hans'
    if hant:
        return 'hant'
    return 'latin'


def auto_locale(locale: str, text: str, enabled: bool) -> str:
    """Applies opt-in script detection to a locale for a text block."""
    if not enabled:
        return locale
    script = detect_script(text)
    if script == 'hans':
        return 'zh-CN'
    if script == 'hant' and not locale.startswith('zh-'):
        return 'zh-TW'
    return locale


def auto_apply_categories(config: Dict[str, Any]) -> Dict[str, bool]:
    """Returns the enabled lint categories from the config."""
    categories = dict(DEFAULT_CATEGORIES)
    settings = config.get('filters', {}).get('linting', {}).get('auto_apply', {})
    if not isinstance(settings, dict):
        return categories
    for name in categories:
        if isinstance(settings.get(name), bool):
            categories[name] = settings[name]
    return categories


def script_detection_enabled(config: Dict[str, Any]) -> bool:
    """Reports whether opt-in script detection is on."""
    spelling = config.get('filters', {}).get('linting', {}).get('spelling', {})
    return spelling.get('auto_detect_script') is True


def locale_dictionary(
    config: Dict[str, Any], locale: str
) -> List[str]:
    """Returns the ignore list for one locale from the config."""
    spelling = config.get('filters', {}).get('linting', {}).get('spelling', {})
    value = spelling.get('ignore_locale_strings', [])
    if isinstance(value, dict):
        value = value.get(locale, value.get('default', []))
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

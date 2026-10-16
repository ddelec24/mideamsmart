"""Maintain the Jeedom translation files of the plugin (core/i18n/<lang>.json).

Usage:
  python3 tools/i18n.py check
      List the strings that are missing or untranslated, per language.
  python3 tools/i18n.py update [translations.json]
      Rebuild every core/i18n/<lang>.json from the strings found in the sources:
      existing translations are kept, obsolete ones are dropped and the optional
      translations file ({"en_US": {"French text": "Translation"}, ...}) fills in
      the gaps for every source file using that French text.

Strings are extracted the way the core translates them: the raw text between
{{ }} in php/js/html files, and the evaluated string of __('...', __FILE__).
"""

import json
import re
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
PLUGIN_ID = PLUGIN_DIR.name
LANGUAGES = ('en_US', 'es_ES', 'it_IT', 'ru_RU', 'pt_PT', 'de_DE')
EXTENSIONS = ('.php', '.js', '.html', '.json')
EXCLUDED_DIRS = ('tools', 'docs', 'resources', 'core/i18n', 'plugin_info', '3rdparty', '.git')
# plugin_info/configuration.php is the only translated file of plugin_info
INCLUDED_FILES = ('plugin_info/configuration.php',)

TEMPLATE_RE = re.compile(r'{{(.*?)}}', re.S)
PHP_SINGLE_RE = re.compile(r"__\(\s*'((?:[^'\\]|\\.)*)'\s*,\s*__FILE__\s*\)")
PHP_DOUBLE_RE = re.compile(r'__\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*__FILE__\s*\)')


def source_files():
    for path in sorted(PLUGIN_DIR.rglob('*')):
        relative = path.relative_to(PLUGIN_DIR).as_posix()
        if relative not in INCLUDED_FILES and (path.suffix not in EXTENSIONS or any(relative.startswith(d + '/') for d in EXCLUDED_DIRS)):
            continue
        yield path, relative


def extract_strings():
    strings = {}
    for path, relative in source_files():
        content = path.read_text(encoding='utf-8')
        found = [text for text in TEMPLATE_RE.findall(content) if text.strip()]
        if path.suffix == '.php':
            found += [text.replace("\\'", "'").replace('\\\\', '\\') for text in PHP_SINGLE_RE.findall(content)]
            found += [text.replace('\\"', '"').replace('\\\\', '\\') for text in PHP_DOUBLE_RE.findall(content)]
        if found:
            strings[f'plugins/{PLUGIN_ID}/{relative}'] = sorted(set(found))
    return strings


def i18n_path(language):
    return PLUGIN_DIR / 'core' / 'i18n' / f'{language}.json'


def load(language):
    path = i18n_path(language)
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {}


def check():
    strings = extract_strings()
    missing_total = 0
    for language in LANGUAGES:
        current = load(language)
        missing = [(name, text) for name, texts in strings.items() for text in texts
                   if not current.get(name, {}).get(text)]
        missing_total += len(missing)
        print(f'{language}: {len(missing)} missing')
        for name, text in missing:
            print(f'  {name}: {text}')
    return 1 if missing_total else 0


def update(translations_file=None):
    strings = extract_strings()
    extra = json.loads(Path(translations_file).read_text(encoding='utf-8')) if translations_file else {}
    for language in LANGUAGES:
        current = load(language)
        provided = extra.get(language, {})
        result = {}
        for name, texts in strings.items():
            result[name] = {}
            for text in texts:
                value = provided.get(text) or current.get(name, {}).get(text, '')
                result[name][text] = value
        i18n_path(language).parent.mkdir(parents=True, exist_ok=True)
        i18n_path(language).write_text(json.dumps(result, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
    return check()


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('check', 'update'):
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == 'check':
        sys.exit(check())
    sys.exit(update(sys.argv[2] if len(sys.argv) > 2 else None))

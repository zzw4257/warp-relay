"""Offline checks for the public README and documentation. No network access.

Verifies, for every Markdown file in the release tree:
  * relative links and images resolve to files or directories inside the tree;
  * `#anchors` exist (GitHub heading slugs, explicit ids);
  * images have alt text, stay within the size budget and are PNG/SVG;
  * inline HTML uses only tags/attributes GitHub keeps after sanitizing;
  * badges are static shields.io badges wrapped in links to local targets;
  * no placeholder hosts, unpublished repository URLs or stale film references.
Exit status is non-zero when any error is found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
# Files the release maintains directly; stale-copy rules apply only to these.
RELEASE_DOCS = ['README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md', 'docs/README.md',
                'docs/architecture.md', 'docs/maintaining.md', 'docs/reproduction.md', 'docs/release-scope.md']
IMAGE_BUDGET = 320 * 1024
ALLOWED_TAGS = {'a', 'img', 'picture', 'source', 'p', 'br', 'h1', 'h2', 'h3', 'sub', 'sup', 'b', 'strong',
                'em', 'i', 'code', 'details', 'summary', 'div', 'kbd', 'table', 'tr', 'td', 'th', 'thead', 'tbody'}
ALLOWED_ATTRS = {'align', 'width', 'height', 'alt', 'src', 'href', 'srcset', 'media', 'id', 'name', 'title', 'open'}
PLACEHOLDER = re.compile(r'example\.com|your[-_]?(org|user|name)|<owner>|OWNER/|USERNAME|REPLACE_ME|TODO|xxx', re.I)
UNPUBLISHED_REPO = re.compile(r'github\.com/[^/\s)"]+/warp[-_]?relay', re.I)
DYNAMIC_BADGE = re.compile(r'img\.shields\.io/(?!badge/)|badge\.svg|codecov\.io|badge\.fury|/actions/workflows/', re.I)
STALE = re.compile(r'151(\.47)?[- ]second|\b151s\b|\bR42\b|round42', re.I)


def slug(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[`*_~]|\[([^\]]*)\]\([^)]*\)', lambda m: m.group(1) or '', text)
    text = text.strip().lower()
    text = re.sub(r'[^\w\- ]', '', text)
    return text.replace(' ', '-')


def strip_code(md: str) -> str:
    md = re.sub(r'^(```|~~~).*?^\1\s*$', '', md, flags=re.M | re.S)
    return re.sub(r'`[^`\n]*`', '', md)


def anchors(md: str) -> set[str]:
    found, seen = set(), {}
    for line in strip_code(md).splitlines():
        m = re.match(r'^(#{1,6})\s+(.*?)\s*#*\s*$', line)
        if m:
            base = slug(m.group(2))
            n = seen.get(base, 0)
            found.add(base if n == 0 else f'{base}-{n}')
            seen[base] = n + 1
    for m in re.finditer(r'<h[1-6][^>]*>(.*?)</h[1-6]>', md, re.S):
        found.add(slug(m.group(1)))
    found |= set(re.findall(r'<a\s+(?:id|name)="([^"]+)"', md))
    return found


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


def check(root: Path) -> dict:
    errors, warnings, stats = [], [], {'files': 0, 'links': 0, 'images': 0, 'badges': 0, 'external': set()}
    md_files = sorted(p for p in root.rglob('*.md') if not any(x in p.parts for x in ('node_modules', 'runs', 'vendor')))
    anchor_cache = {}

    def anchors_of(path: Path):
        if path not in anchor_cache:
            anchor_cache[path] = anchors(path.read_text(encoding='utf-8'))
        return anchor_cache[path]

    def resolve(src: Path, target: str, kind: str):
        rel = src.relative_to(root).as_posix()
        if not target or target.startswith(('mailto:',)):
            return
        parts = urlsplit(target)
        if parts.scheme in ('http', 'https'):
            stats['external'].add(parts.netloc)
            if PLACEHOLDER.search(target) or UNPUBLISHED_REPO.search(target):
                errors.append(f'{rel}: placeholder or unpublished repository URL: {target}')
            if DYNAMIC_BADGE.search(target):
                errors.append(f'{rel}: dynamic/CI badge not backed by a real service: {target}')
            return
        if parts.scheme:
            errors.append(f'{rel}: unsupported link scheme: {target}')
            return
        path = (src.parent / unquote(parts.path)).resolve() if parts.path else src
        if not path.is_relative_to(root):
            errors.append(f'{rel}: {kind} escapes the tree: {target}')
            return
        if not path.exists():
            errors.append(f'{rel}: missing {kind} target: {target}')
            return
        if parts.fragment:
            if path.is_file() and path.suffix == '.md':
                if parts.fragment not in anchors_of(path):
                    errors.append(f'{rel}: missing anchor #{parts.fragment} in {path.relative_to(root)}')
        if kind == 'image':
            stats['images'] += 1
            if path.suffix.lower() not in ('.png', '.svg'):
                errors.append(f'{rel}: image must be PNG or SVG: {target}')
            if path.stat().st_size > IMAGE_BUDGET:
                errors.append(f'{rel}: image over {IMAGE_BUDGET // 1024} KB: {target}')

    for src in md_files:
        stats['files'] += 1
        rel = src.relative_to(root).as_posix()
        raw = src.read_text(encoding='utf-8')
        md = strip_code(raw)
        if rel in RELEASE_DOCS and STALE.search(md):
            errors.append(f'{rel}: stale film reference: {STALE.search(md).group(0)}')
        if PLACEHOLDER.search(re.sub(r'<!--.*?-->', '', md, flags=re.S)):
            errors.append(f'{rel}: placeholder text: {PLACEHOLDER.search(md).group(0)}')
        for m in re.finditer(r'(!?)\[([^\]]*)\]\(<?([^)\s>]+)>?(?:\s+"[^"]*")?\)', md):
            stats['links'] += 1
            if m.group(1) and not m.group(2).strip():
                errors.append(f'{rel}: Markdown image without alt text: {m.group(3)}')
            resolve(src, m.group(3), 'image' if m.group(1) else 'link')
        for m in re.finditer(r'<(https?://[^>\s]+)>', md):
            stats['links'] += 1
            resolve(src, m.group(1), 'link')
        parser = Tags()
        parser.feed(re.sub(r'<https?://[^>\s]+>', '', md))  # autolinks are Markdown, not HTML
        for i, (tag, attrs) in enumerate(parser.items):
            if tag not in ALLOWED_TAGS:
                errors.append(f'{rel}: HTML tag <{tag}> is removed by GitHub sanitizing')
            for name in attrs:
                if name not in ALLOWED_ATTRS:
                    errors.append(f'{rel}: attribute {name}= on <{tag}> is removed by GitHub sanitizing')
            if tag == 'a' and 'href' in attrs:
                stats['links'] += 1
                resolve(src, attrs['href'], 'link')
            if tag == 'img':
                if not (attrs.get('alt') or '').strip():
                    errors.append(f'{rel}: <img> without alt text: {attrs.get("src")}')
                src_url = attrs.get('src', '')
                if 'img.shields.io' in src_url:
                    stats['badges'] += 1
                    link = next((a for t, a in reversed(parser.items[:i]) if t == 'a'), None)
                    href = (link or {}).get('href', '')
                    if not href or urlsplit(href).scheme:
                        errors.append(f'{rel}: badge must link to a local file or anchor: {src_url}')
                resolve(src, src_url, 'image')
                if rel == 'README.md' and not urlsplit(src_url).scheme and 'width' not in attrs:
                    warnings.append(f'{rel}: README image without width: {src_url}')
            if tag == 'source' and attrs.get('srcset'):
                resolve(src, attrs['srcset'], 'image')

    readme = (root / 'README.md').read_text(encoding='utf-8')
    if 'Unpublished' not in readme:
        errors.append('README.md: unpublished status is not stated')
    stats['external'] = sorted(stats['external'])
    return {'root': '.', 'errors': errors, 'warnings': warnings, **stats, 'network_requests': 0}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--root', type=Path, default=ROOT)
    args = ap.parse_args()
    report = check(args.root.resolve())
    print(json.dumps(report, indent=2))
    sys.exit(1 if report['errors'] else 0)

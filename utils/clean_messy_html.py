#!/usr/bin/env python3
import sys
import os
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# adjust or extend as needed
DOC_EXTENSIONS = {
    '.pdf':    'PDF',
    '.doc':    'Word document',
    '.docx':   'Word document',
    '.xls':    'Excel spreadsheet',
    '.xlsx':   'Excel spreadsheet',
    '.ppt':    'PowerPoint presentation',
    '.pptx':   'PowerPoint presentation',
}

def is_relative(url):
    return not bool(urlparse(url).netloc)

def is_internal(url):
    return is_relative(url) or 'musc' in url.lower()

def is_document(url):
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    return ext in DOC_EXTENSIONS

def file_type_label(url):
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    return DOC_EXTENSIONS.get(ext, ext.lstrip('.').upper())

def site_label(url):
    host = urlparse(url).netloc.lower()
    if host.startswith('www.'):
        host = host[4:]
    return host

def process_link(a):
    href = a.get('href', '').strip()
    if not href:
        return

    if is_document(href):
        # PDF/Word/etc.
        label = file_type_label(href)
        a['title']  = f'{label} format, opens in new window.'
        a['target'] = '_blank'
        return

    if is_internal(href):
        # MUSC or relative → strip extra attrs
        for attr in ('title', 'target', 'rel'):
            a.attrs.pop(attr, None)
        return

    # external site
    host = site_label(href)
    a['title'] = (
        f'{host} site. You are being directed to a website outside of MUSC. '
        'MUSC is not responsible for any content or other aspects of the external website.'
    )
    return

def clean_file(path, inplace=True):
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    for a in soup.find_all('a'):
        process_link(a)

    out = str(soup)
    if inplace:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(out)
    else:
        sys.stdout.write(out)

def main():
    p = argparse.ArgumentParser(
        description='Clean up <a> tags in one or more HTML files.'
    )
    p.add_argument('html_files', nargs='+', help='.html files to process')
    p.add_argument(
        '-n', '--dry-run', action='store_true',
        help='print results to stdout instead of overwriting files'
    )
    args = p.parse_args()

    for fp in args.html_files:
        if not os.path.isfile(fp):
            print(f'ERROR: {fp} does not exist or is not a file', file=sys.stderr)
            continue
        clean_file(fp, inplace=not args.dry_run)

if __name__ == '__main__':
    main()
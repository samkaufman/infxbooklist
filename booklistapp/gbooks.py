import sys
import urllib
import utils
from elementtree import ElementTree


class Book(object):
    def __init__(self, title, authors, thumbnail_url, isbn, gid, link):
        super(Book, self).__init__()
        self.title = title
        self.authors = authors
        self.thumbnail_url = thumbnail_url
        self.isbn = isbn
        self.gid = gid
        self.link = link


def get(gid):
    openurl = urllib.urlopen('http://books.google.com/books/feeds/volumes/'+gid)
    try:
        parsed = _parse_url(openurl)
        assert len(parsed) == 1
        return parsed[0]
    finally:
        openurl.close()


def search(query):
    p = urllib.urlencode({'q': query, 'max-results': '20'})
    openurl = urllib.urlopen('http://books.google.com/books/feeds/volumes?'+p)
    try:
        return _parse_url(openurl)
    finally:
        openurl.close()


def _parse_url(openurl):
    def gimmeall(tree):
        if tree.getroot().tag == '{http://www.w3.org/2005/Atom}entry':
            return [tree.getroot()]
        else:
            return tree.findall('{http://www.w3.org/2005/Atom}entry')
    out = []
    for e in gimmeall(ElementTree.parse(openurl)):
        info_eles = [c for c in e.findall('{http://www.w3.org/2005/Atom}link')
                     if c.attrib['rel'] == 'http://schemas.google.com/books/2008/info']
        if len(info_eles) > 0:
            info = info_eles[0].attrib['href']
            if len(info_eles) > 1:
                print >>sys.stderr, 'Multiple info URLs found. Saved first one'
        else:
            info = None
            print >>sys.stderr, 'No info URL found found'
        
        isbn13_eles = [c for c in e.findall('{http://purl.org/dc/terms}identifier')
                       if c.text.upper().startswith('ISBN:') and len(c.text) == 13+5]
        isbn10_eles = [c for c in e.findall('{http://purl.org/dc/terms}identifier')
                       if c.text.upper().startswith('ISBN:') and len(c.text) == 10+5]
        if len(isbn13_eles) > 0:
            isbn = isbn13_eles[0].text[5:]
            if len(isbn13_eles) > 1:
                print >>sys.stderr, 'Multiple ISBN-13 idents found. Saved first one'
                print >>sys.stderr, 'They were', repr([x.text for x in isbn13_eles])
        elif len(isbn10_eles) > 0:
            isbn = isbn10_eles[0].text[5:]
            if len(isbn10_eles) > 1:
                print >>sys.stderr, 'No ISBN-13 and multiple ISBN-10 idents found. Saved first one'
                print >>sys.stderr, 'They were', repr([x.text for x in isbn10_eles])
        else:
            isbn = None
        
        gid_eles = [c for c in e.findall('{http://purl.org/dc/terms}identifier')
                    if ':' not in c.text]
        if len(gid_eles) > 0:
            gid = gid_eles[0].text
            if len(gid_eles) > 1:
                print >>sys.stderr, 'Multiple GIDs found. Saved first one'
                print >>sys.stderr, 'They were', repr([repr(x.text) for x in gid_eles])
        else:
            gid = None
            print >>sys.stderr, 'No GID found'
        
        title = e.findtext('{http://www.w3.org/2005/Atom}title')
        author_list = [x.text for x in e.findall('{http://purl.org/dc/terms}creator')]
        authors = utils.english_list(author_list)
        
        print 'all links', [(c.attrib['rel'], c.attrib['href']) for c in e.findall('{http://www.w3.org/2005/Atom}link')]
        img_links = [c for c in e.findall('{http://www.w3.org/2005/Atom}link')
                     if c.attrib['rel'] == 'http://schemas.google.com/books/2008/thumbnail']
        if len(img_links) > 0:
            img_url = img_links[0].attrib['href']
            if len(img_links) > 1:
                print >>sys.stderr, 'Multiple image links found. Taking first one as cover'
        else:
            img_url = None
        out.append(Book(title, authors, img_url, isbn, gid, link=info))
    return out


if __name__ == '__main__':
    print get_books('football Nazis')
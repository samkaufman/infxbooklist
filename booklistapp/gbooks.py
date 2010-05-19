import sys
import urllib
import utils
from elementtree import ElementTree


class Book(object):
    def __init__(self, title, authors, thumbnail_url, isbn, link):
        super(Book, self).__init__()
        self.title = title
        self.authors = authors
        self.thumbnail_url = thumbnail_url
        self.isbn = isbn
        self.link = link


def get_books(query):
    p = urllib.urlencode({'q': query, 'max-results': '20'})
    openurl = urllib.urlopen('http://books.google.com/books/feeds/volumes?'+p)
    tree = ElementTree.parse(openurl)
    out = []
    for e in tree.findall('{http://www.w3.org/2005/Atom}entry'):
        info_eles = [c for c in e.findall('{http://www.w3.org/2005/Atom}link')
                     if c.attrib['rel'] == 'http://schemas.google.com/books/2008/info']
        if len(info_eles) > 0:
            info = info_eles[0].attrib['href']
            if len(info_eles) > 1:
                print >>sys.stderr, 'Multiple info URLs found. Taking first one'
        else:
            info = None
            print >>sys.stderr, 'No info URL found found'
        isbn_eles = [c for c in e.findall('{http://purl.org/dc/terms}identifier')
                     if c.text.upper().startswith('ISBN:')]
        if len(isbn_eles) > 0:
            isbn = isbn_eles[0].text
            if len(isbn_eles) > 1:
                print >>sys.stderr, 'Multiple ISBN idents found. Taking first one'
        else:
            isbn = None
            print >>sys.stderr, 'No ISBN found'
        title = e.find('{http://www.w3.org/2005/Atom}title')
        author_list = [x.text for x in e.findall('{http://purl.org/dc/terms}creator')]
        authors = utils.english_list(author_list)
        img_links = [c for c in e.findall('{http://www.w3.org/2005/Atom}link')
                     if c.attrib['rel'] == 'http://schemas.google.com/books/2008/thumbnail']
        if len(img_links) > 0:
            img_url = img_links[0].attrib['href']
            if len(img_links) > 1:
                print >>sys.stderr, 'Multiple image links found. Taking first one as cover'
        else:
            img_url = None
        out.append(Book(title, authors, img_url, isbn, link=info))
    return out


print get_books('football Nazis')
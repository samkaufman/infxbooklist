from django.db import models
from django.template.defaultfilters import slugify
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from settings import AMAZON_KEY
from utils import english_list
import ecs, urllib2


class StringChunker:
    '''
    A dirty trick. This wraps a str
    and adds a generator 'chunks()' such
    that it can be passed to Django's
    File.save_image.
    '''
    def __init__(self, s):
        self.inner = s
    def chunks(self):
        yield self.inner
    def __getattr__(self, name):
        return getattr(self.inner, name)

class Book(models.Model):
    asin = models.CharField('Amazon.com standard ident. number', max_length=10, unique=True)
    isbn = models.CharField('13-char ISBN', max_length=13)
    title = models.CharField(max_length=200)
    authors = models.CharField(max_length=200)
    cover_image = models.FileField(upload_to='bookcovers')
    added = models.DateTimeField(auto_now_add=True)
    edited = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return "\""+str(self.title)+"\" by "+str(self.authors)
    def url(self):
        return 'http://www.amazon.com/gp/product/'+self.asin
    def get_comments(self):
        return [r for r in self.recommendation_set.all() if r.comment]
    def get_silent_recommendations(self):
        return [r for r in self.recommendation_set.all() if not r.comment]
    def update_from_amazon(self):
        if self.asin:
            item = ecs.ItemLookup(AWSAccessKeyId=AMAZON_KEY, ItemId=self.asin, ResponseGroup="Small,Images")
        elif self.isbn:
            item = ecs.ItemLookup(AWSAccessKeyId=AMAZON_KEY, ItemId=self.isbn, ResponseGroup="Small,Images", SearchIndex="Books", IdType="ISBN")
        else:
            raise "No ASIN or ISBN with which to update"
        assert len(item) == 1
        item = item[0]
        if not self.title.strip():
            self.title = item.Title
        if not self.authors.strip():
            self.authors = english_list(item.Author)
        if not self.asin.strip():
            self.asin = item.ASIN
        try:
            image_link = urllib2.urlopen(item.SmallImage.URL)
            image_data = image_link.read()
            image_link.close()
            self.cover_image.save(item.SmallImage.URL.split('/')[-1],
                                  StringChunker(image_data), save=True)
        except Exception, e:
            import sys
            print >> sys.stderr, 'Failed to download book cover from Amazon:', e
            import traceback
            traceback.print_tb(sys.exc_info()[2])
    
class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=50)
    books = models.ManyToManyField(Book, null=True, blank=True)
    category_type = models.ForeignKey('CategoryType')
    class Meta:
        verbose_name_plural = "categories"
    def __unicode__(self):
        return self.name
    #TODO: turn following into permalink
    def get_absolute_url(self):
        return "/%i/" % self.slug
        
class CategoryType(models.Model):
    """
    A category of categories, so to speak.
    This is largely to group categories
    on the index page by, say, whether
    they describe the audience or subject
    matter.
    """
    description = models.CharField(max_length=64)
    def get_categories(self):
        return self.category_set.all()
    def __unicode__(self):
        return self.description
            
class User(models.Model):
    ucinetid = models.CharField(max_length=8)
    def __unicode__(self):
        return self.ucinetid
    
class Recommendation(models.Model):
    user = models.ForeignKey(User)
    book = models.ForeignKey(Book)
    added = models.DateTimeField(auto_now_add=True)
    edited = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True)
    def __unicode__(self):
        return self.book.authors[:7]+": "+str(self.user)+": "+self.comment[:20]

class FeedbackNote(models.Model):
    """A note left by a user."""
    text = models.TextField()
    def __unicode__(self):
        return self.text[:100]
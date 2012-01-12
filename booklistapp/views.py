from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.views import redirect_to_login
from django.views.generic.list_detail import object_list
from models import Book, Category, CategoryType, FeedbackNote, Recommendation, User
from settings import AMAZON_KEY, DEBUG
from booklistapp.utils import english_list
import urllib
import urllib2
import ecs
import random
import os
import sys
import datetime
import gbooks


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


def index(request, category):
    # Simple or Complete view
    if 'view' in request.GET:
        if request.GET['view'] in ('simple','complete'):
            view = request.GET['view']
            request.session['view'] = view
    elif 'view' in request.session:
        if request.session['view'] in ('simple','complete'):
            view = request.session['view']
    else:
        view = 'complete'
    # What books to display
    if category:
        if category[-1] == '/':
            category = category[:-1]
        category_s = get_object_or_404(Category, slug=category)
        books_to_display = category_s.books.all().order_by('-edited')
        page_title = category_s.name
    else:
        books_to_display = Book.objects.all().order_by('-edited')
        page_title = ''
    # Finish and render
    return object_list(request, queryset=books_to_display,
                       template_object_name='book',
                       paginate_by=10,
                       extra_context={'page_title': page_title,
                                      'complete_view': view=='complete',
                                      'category_types': CategoryType.objects.all(),
                                      'current_slug': category})
    
    
def edit(request):
    # TODO: Clean up this messy method.
    
    # Require login.
    if not (request.user.is_authenticated()):
        return redirect_to_login(request.get_full_path())

    recs = Recommendation.objects.filter(user=request.user)
    category_types = CategoryType.objects.all()
    all_categories = Category.objects.all()
    context = {'recs': recs,
               'category_types': category_types,
               'cat_check_htmls': []}
    books_in_c = {}
    for c in all_categories:
        books_in_c[c] = [r for r in recs.filter(book__category=c) \
                                        .distinct()]
    print >>sys.stderr, repr(books_in_c)
    for rec in recs:
	    b = ''
	    for ct in category_types:
	        b += '<p style="font-weight: bold">%s</p>' % ct.description
	        for c in ct.get_categories():
	            b += '<input type="checkbox" name="{0}" id="{1}{0}"'.format(c.slug, rec.id)
	            if rec in books_in_c[c]:
	                b += 'checked="checked" '
	            b += '/><label for="%d%s">%s</label><br />' % (rec.id, c.slug, c.name)
	    context['cat_check_htmls'].append(b)
             
    if 'keywords' in request.GET:
        context['results'] = gbooks.search(request.GET['keywords'])
    elif 'gid' in request.POST:
        if 'action' in request.POST:
            b = Book.objects.get(gid=request.POST['gid'])
            r = Recommendation.objects.get(user=request.user,
                                           book=b)
            if request.POST['action'] == 'update':
                for c in Category.objects.all():
                    if c.slug in request.POST:
                        c.books.add(b)
                    else:
                        c.books.remove(b)
                r.comment = request.POST['blurb']
                r.save()
                print >>sys.stderr, repr(request.POST)
            elif request.POST['action'] == 'delete':
                if len(Recommendation.objects.filter(book=r.book)) == 1:
                    os.unlink(os.path.join('/opt/infxbooklist/bookcovers/', r.book.cover_image))
                    r.book.delete()
                r.delete()
        else:
            # Make the book if doesn't exist, update if does
            gb = gbooks.get(request.POST['gid'])
            b = Book.objects.get_or_create(gid=gb.gid)[0]
            b.title = gb.title
            b.authors = gb.authors
            b.isbn = gb.isbn
            try:
                # Download the thumbnail image from Google
                req = urllib2.Request(gb.thumbnail_url)
                req.add_header("User-Agent", "Mozilla")
                try:
                    # TODO: These images are never deleted. Write a cron script to
                    #       scrub the dir of images that tables no longer reference.
                    image_link = urllib2.urlopen(req)
                    img_data = image_link.read()
                    image_link.close()
                    rand_fn = datetime.datetime.utcnow().isoformat()+'__'+str(random.randint(0, sys.maxint))
                    rand_pth = os.path.join('/opt/infxbooklist/bookcovers', rand_fn)
                    with open(rand_pth, 'w') as f:
                        f.write(img_data)
                    b.cover_image = rand_fn
                except Exception, e:
                    print >>sys.stderr, "Tried to save thumbnail, but got exception:", repr(e)
            finally:
                b.save()
            # Create a Recommendation, which links User and Book
            Recommendation(user=request.user, book=b).save()
        # Redirect to avoid refresh issues
        return HttpResponseRedirect("/edit/")
    # Go.
    return render_to_response('edit.html', context)
    
    
def feedback(request):
    if 'text' in request.POST:
        f = FeedbackNote(text=request.POST['text'])
        f.save()
    return HttpResponse('Thanks!');
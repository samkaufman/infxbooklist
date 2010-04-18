from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.paginator import Paginator
from django.contrib.auth.views import redirect_to_login
from django.views.generic.list_detail import object_list
from models import Book, Category, CategoryType, FeedbackNote, Recommendation, User
from settings import AMAZON_KEY, DEBUG
from booklistapp.utils import english_list
from urllib import urlencode
import ecs, datetime

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
        category_s = Category.objects.get(slug=category)
        books_to_display = category_s.books.all().order_by('-edited')
        page_title = category_s.name
    else:
        books_to_display = Book.objects.all().order_by('-edited')
        page_title = ''
    # Finish and render
    print 'queryset is', books_to_display
    return object_list(request, queryset=books_to_display,
                       template_object_name='book',
                       paginate_by=10,
                       extra_context={'page_title': page_title,
                                      'complete_view': view=='complete',
                                      'category_types': CategoryType.objects.all(),
                                      'current_slug': category})
    
    
def edit(request):
    context = {}
    
    #
    # Require login.
    #
    if not (request.user.is_authenticated()):
        return redirect_to_login(request.get_full_path())
    
    #
    # Adding books
    #
    if 'keywords' in request.GET:
        results = []
        books = ecs.ItemSearch(AWSAccessKeyId=AMAZON_KEY, ResponseGroup="Small", SearchIndex="Books", Keywords=request.GET['keywords'])
        for i,b in zip(xrange(10),books):
            x = Book()
            x.title = b.Title
            try:
                x.authors = english_list(b.Author)
            except:
                pass
            x.asin = b.ASIN
            results.append(x)
        context['results'] = results
    elif 'asin' in request.POST:
        b = Book(asin=request.POST['asin'], added=datetime.datetime.now())
        b.update_from_amazon()
        b.save()
        
    #
    # User's recommendations and contacts
    #
    context['recs'] = Recommendation.objects.filter(user=request.user)

    # Go.
    return render_to_response('edit.html', context)
    
    
def feedback(request):
    if 'text' in request.POST:
        f = FeedbackNote(text=request.POST['text'])
        f.save()
        print 'Just saved',f.text
    return HttpResponse('Thanks!');
AMAZON_KEY = "10XP3WT61QS7AY0S2W02"

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Sam Kaufman', 'kaufmans@uci.edu'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'     # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'booklist.db'   # Or path to database file if using sqlite3.
DATABASE_USER = 'booklist'      # Not used with sqlite3.
DATABASE_PASSWORD = 'elektric7' # Not used with sqlite3.
DATABASE_HOST = ''              # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''              # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '-bgt35&!q3(3sz384+zo@=oeqw*!06c1*$j32q-1%$bco_t^p('

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'infxbooklist.urls'

TEMPLATE_DIRS = (
    '/Users/emrys/Code/infxbooklist/templates'
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.humanize',
    'infxbooklist.booklistapp'
)

LOGIN_URL = "/login/"

# If there is a local_settings module,
# it should be allowed to override the
# above. This is for clean deployment.
try:
    from local_settings import *
except ImportError:
    pass
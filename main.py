import falcon
import falcon.asgi
import jinja2
import json
import datetime
import gettext
import os
from babel.dates import format_date, format_time
from babel.numbers import format_decimal
import logging

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO
)


##### Globals
STATIC_PATH = os.path.join(os.getcwd(), 'static')
IMAGE_PATH  = os.path.join(STATIC_PATH, 'img')

MEDIA_PATH = os.path.join(os.getcwd(), 'media')
AUDIO_PATH = os.path.join(MEDIA_PATH, 'audio')
TEXT_PATH = os.path.join(MEDIA_PATH, 'text')
VIDEO_PATH = os.path.join(MEDIA_PATH, 'video')

DEFAULT_LOCALE = 'en'
LOCALE_DIR = 'locales'

def get_supported_languages(locale_dir):
    return [x for x in os.listdir(locale_dir)
                       if os.path.isdir(os.path.join(locale_dir, x))]
SUPPORTED_LANGS = get_supported_languages(LOCALE_DIR)


def get_translations(locale_dir):
    translations = {}
    for lang in SUPPORTED_LANGS:
        translations[lang] = gettext.translation(
            'messages',
            localedir=locale_dir,
            languages=[lang]
        )
    return translations
TRANSLATIONS = get_translations(LOCALE_DIR)


##### Funcs & Resources

def get_template_locale(locale_dir):
    tmpl = jinja2.Environment(
        extensions=['jinja2.ext.i18n'],
        loader=jinja2.FileSystemLoader('templates')
    )
    tmpl.install_gettext_translations(TRANSLATIONS[DEFAULT_LOCALE])
    tmpl.filters['num_filter'] = num_filter
    tmpl.filters['date_filter'] = date_filter
    tmpl.filters['time_filter'] = time_filter
    return tmpl


def get_active_locale(context, locale):
    if context:
        context_locale = context.get('locale', DEFAULT_LOCALE)
    else:
        context_locale = locale
    return context_locale


@jinja2.pass_context
def num_filter(context, input, locale=DEFAULT_LOCALE):
    context_locale = get_active_locale(context, locale)
    return format_decimal(input, locale=context_locale)


@jinja2.pass_context
def date_filter(context, input, locale=DEFAULT_LOCALE):
    context_locale = get_active_locale(context, locale)
    return format_date(input, format='full', locale=context_locale)


@jinja2.pass_context
def time_filter(context, input, locale=DEFAULT_LOCALE):
    context_locale = get_active_locale(context, locale)
    return format_time(input, locale=context_locale)


class MainResource:
    async def on_get(self, req, resp, locale):
        if(locale not in SUPPORTED_LANGS):
            locale = DEFAULT_LOCALE

        tmpl = get_template_locale(LOCALE_DIR)
        tmpl.install_gettext_translations(TRANSLATIONS[locale])

        # mock data
        data = {
            "event_date": datetime.date(2021, 12, 4),
            "event_time": datetime.time(10, 30, 0)
        }

        resp.status = falcon.HTTP_200
        resp.content_type = 'text/html'
        template = tmpl.get_template("index.html")
        resp.text = template.render(**data, locale=locale)


async def upload_audio(req, name, audio_id):
    filepath = None
    form = await req.get_media()
    async for part in form:
        if filepath == None:
            audio_id = "%s-%s" % (audio_id, part.secure_filename)
            filepath = os.path.join(AUDIO_PATH, f'{audio_id}')
            fp = open(filepath, 'ab')
        if part.name == name:
            # Do something with the uploaded data (file)
            async for chunk in part.stream:
                fp.write(chunk)
    fp.close()
    return audio_id


class APIAudioResource:
    async def on_get(self, req, resp):
        resp.status = falcon.HTTP_400
        resp.content_type = 'application/json'
        resp.text = json.dumps({'error': "unavailable"})
        return

    async def on_post(self, req, resp):
        audio_id = "default_filename" # str(uuid.uuid4())
        #try:
        #    #audio_body = req.get_param('file')
        #    #raw = audio_body.file.read()
        #except Exception as e:
        #    print(e)
        #    raise falcon.HTTPBadRequest(
        #      success=False,
        #      error="Failed to upload audio",
        #      description="There is a bad request for uploading the Audio."
        #    )
        try:
            audio_id = await upload_audio(req, 'file', audio_id)
        except Exception as e:
            print(e)
            raise falcon.HTTPInternalServerError(
              success=False,
              error="Failed to fetch audio",
              description="An issue occurred while fetching the Audio."
            )
        resp.status = falcon.HTTP_200
        resp.content_type = 'application/json'
        resp.text = json.dumps({'success': True, 'audio_id': audio_id})


class RedirectResource:
    async def on_get(self, req, resp):
        raise falcon.HTTPFound(req.prefix + '/en/main')


#### __main__

mainHandler = MainResource()
apiAudioHandler = APIAudioResource()
redirect = RedirectResource()

app = falcon.asgi.App()
app.add_static_route('/img', IMAGE_PATH)
app.add_route('/{locale}/main', mainHandler)
app.add_route('/api/audio', apiAudioHandler)
app.add_route('/', redirect)

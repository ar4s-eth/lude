import falcon
import falcon.asgi
import jinja2
import datetime
import gettext
import os
from babel.dates import format_date, format_time
from babel.numbers import format_decimal

app = falcon.asgi.App()
translations = {}
default_fallback = 'en'
tmpl = jinja2.Environment(extensions=['jinja2.ext.i18n'], loader=jinja2.FileSystemLoader('templates'))

base_dir = 'locales'
supported_langs = [x for x in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, x))]

for lang in supported_langs:
    translations[lang] = gettext.translation('messages', localedir='locales', languages=[lang])

tmpl.install_gettext_translations(translations[default_fallback])


def get_active_locale(context, locale):
    if context:
        context_locale = context.get('locale', default_fallback)
    else:
        context_locale = locale
    return context_locale


@jinja2.pass_context
def num_filter(context, input, locale=default_fallback):
    context_locale = get_active_locale(context, locale)
    return format_decimal(input, locale=context_locale)


@jinja2.pass_context
def date_filter(context, input, locale=default_fallback):
    context_locale = get_active_locale(context, locale)
    return format_date(input, format='full', locale=context_locale)


@jinja2.pass_context
def time_filter(context, input, locale=default_fallback):
    context_locale = get_active_locale(context, locale)
    return format_time(input, locale=context_locale)


tmpl.filters['num_filter'] = num_filter
tmpl.filters['date_filter'] = date_filter
tmpl.filters['time_filter'] = time_filter


class ExampleResource:
    async def on_get(self, req, resp, locale):
        if(locale not in supported_langs):
            locale = default_fallback

        tmpl.install_gettext_translations(translations[locale])

        # mock data
        data = {
            "event_attendee": 1234,
            "event_date": datetime.date(2021, 12, 4),
            "event_time": datetime.time(10, 30, 0)
        }

        resp.status = falcon.HTTP_200
        resp.content_type = 'text/html'
        template = tmpl.get_template("index.html")
        resp.text = template.render(**data, locale=locale)


class RedirectResource:
    async def on_get(self, req, resp):
        raise falcon.HTTPFound(req.prefix + '/en/main')


static_path = os.path.join(os.getcwd(), 'static')
example = ExampleResource()
redirect = RedirectResource()

app.add_static_route('/img', os.path.join(static_path, 'img'))
app.add_route('/{locale}/main', example)
app.add_route('/', redirect)

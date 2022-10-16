import falcon
import falcon.asgi
from falcon import media
import jinja2
import json
import datetime
import gettext
import os
from babel.dates import format_date, format_time
from babel.numbers import format_decimal
import logging

import whisper

import pylude  ## local relative import
print("pyLuDe activated version: %s" % pylude.__VERSION__)

##### Globals
ABSOLUTE_ROOT_PATH = os.getcwd()

STATIC_PATH = os.path.join(ABSOLUTE_ROOT_PATH, 'static')
IMAGE_PATH  = os.path.join(STATIC_PATH, 'img')

MEDIA_PATH = os.path.join(ABSOLUTE_ROOT_PATH, 'media')
AUDIO_PATH = os.path.join(MEDIA_PATH, 'audio')
TEXT_PATH = os.path.join(MEDIA_PATH, 'text')
FRAMEDATA_PATH = os.path.join(MEDIA_PATH, 'framedata')
FRAMES_PATH = os.path.join(MEDIA_PATH, 'frames')
VIDEO_PATH = os.path.join(MEDIA_PATH, 'video')
FONTS_PATH = os.path.join(MEDIA_PATH, 'fonts')

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


def trim_path(absolute_path, trim_path):
    return absolute_path.replace(trim_path, "")


##### Funcs & Resources

def load_whisper_model():
    model = whisper.load_model("base")
    print("Model Device: %s" % model.device)
    return model

def transcribe(audio_id):
    filepath = os.path.join(TEXT_PATH, f'{audio_id}')
    if os.path.isfile(filepath):
        print("%s transcription exists, returning that" % filepath)
        with open(filepath, 'r') as fp:
            return fp.readlines()
    model = WHISPER_MODEL
    audio_file = os.path.join(AUDIO_PATH, audio_id)
    audio = whisper.load_audio(audio_file)
    audio = whisper.pad_or_trim(audio)  ## this trims audio to 1min, on local machine the run panics otherwise

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions(fp16=False)
    result = whisper.decode(model, mel, options)
    with open(filepath, 'w') as fp:
        fp.write(result.text)
    return result.text


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


async def update_transcript(req, audio_id):
    transcript = await req.get_media()
    script_filepath = os.path.join(TEXT_PATH, audio_id)
    with open(script_filepath, 'w') as fp:
        fp.write(transcript)
    return script_filepath


class APITranscribeResource:
    async def on_get(self, req, resp, audio_id):
        try:
            transcription = transcribe(audio_id)
        except Exception as e:
            print(e)
            raise falcon.HTTPInternalServerError(
              success=False,
              error="Failed to transcribe audio",
              description="An issue occurred while transcribing the Audio."
            )
        resp.status = falcon.HTTP_200
        resp.content_type = 'application/json'
        resp.text = json.dumps({'success': True, 'text': transcription})
        return

    async def on_post(self, req, resp, audio_id):
        try:
            await update_transcript(req, audio_id)
        except Exception as e:
            print(e)
            raise falcon.HTTPInternalServerError(
              success=False,
              error="Failed to generate video",
              description="An issue occurred while generating the video."
            )
        resp.status = falcon.HTTP_200
        resp.content_type = 'application/json'
        resp.text = json.dumps({'success': True, 'task': 'script updated'})


class APIVideoResource:
    async def on_get(self, req, resp):
        resp.status = falcon.HTTP_400
        resp.content_type = 'application/json'
        resp.text = json.dumps({'error': "unavailable"})
        return

    async def on_post(self, req, resp, audio_id):
        my_video_file = os.path.join(VIDEO_PATH, audio_id)
        try:
            script_filepath = os.path.join(TEXT_PATH, audio_id)
            framedata_file = pylude.generate_framedata(script_filepath, FRAMEDATA_PATH)

            my_frames_dir = os.path.join(FRAMES_PATH, audio_id)
            frame_specs = pylude.generate_frames(framedata_file, my_frames_dir, FONTS_PATH)

            video_fps = frame_specs['fps']
            my_video_file = os.path.splitext(my_video_file)[0] + ".mp4"
            pylude.generate_video(my_frames_dir, my_video_file, video_fps)
        except Exception as e:
            print(e)
            raise falcon.HTTPInternalServerError(
              success=False,
              error="Failed to generate video",
              description="An issue occurred while generating the video."
            )
        if not os.path.isfile(my_video_file):
            raise falcon.HTTPInternalServerError(
                success=False,
                error="Failed to generate video",
                description="The process completed but no video file can be located."
            )
        resp.status = falcon.HTTP_200
        resp.content_type = 'application/json'
        resp.text = json.dumps({
            'success': True,
            'video_link': trim_path(my_video_file, MEDIA_PATH),
        })


class APIAudioResource:
    async def on_get(self, req, resp):
        resp.status = falcon.HTTP_400
        resp.content_type = 'application/json'
        resp.text = json.dumps({'error': "unavailable"})
        return

    async def on_post(self, req, resp):
        audio_id = "default_filename" # str(uuid.uuid4())
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


class PlainTextHandler(media.BaseHandler):
    def serialize(self, media, content_type):
        return str(media).encode()

    def deserialize(self, stream, content_type, content_length):
        return stream.read().decode()


#### __main__

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO
)

WHISPER_MODEL = load_whisper_model()

mainHandler = MainResource()
apiAudioHandler = APIAudioResource()
apiVideoHandler = APIVideoResource()
apiTranscribeHandler = APITranscribeResource()
redirect = RedirectResource()

extra_handlers = {
    'text/plain': PlainTextHandler(),
}

app = falcon.asgi.App()
app.req_options.media_handlers.update(extra_handlers)
app.add_static_route('/img', IMAGE_PATH)
app.add_static_route('/video', VIDEO_PATH)
app.add_route('/{locale}/main', mainHandler)
app.add_route('/api/audio', apiAudioHandler)
app.add_route('/api/transcribe/{audio_id}', apiTranscribeHandler)
app.add_route('/api/video/{audio_id}', apiVideoHandler)
app.add_route('/', redirect)

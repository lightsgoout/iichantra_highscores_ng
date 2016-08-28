import base64
import itertools
import json

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from highscores.models import Score, GameMode, Version, Checksum


def index(request):
    in_version = request.GET.get('version', settings.CURRENT_IICHANTRA_VERSION)
    obj_version = Version.objects.get(version=unicode(in_version))
    in_mode = request.GET.get('mode', settings.DEFAULT_IICHANTRA_MODE)

    try:
        obj_mode = GameMode.objects.get(version=obj_version, number=in_mode)
    except GameMode.DoesNotExist:
        # Fallback for 1.2 iichantra
        obj_mode = GameMode.objects.get(version=obj_version, number=(int(in_mode)-2))

    score_list = Score.objects.filter(version=obj_version, mode__number=in_mode).order_by('-score', 'seconds')
    paginator = Paginator(score_list, 50)

    version_list = Version.objects.filter(is_public=True).order_by('-id')
    mode_list = GameMode.objects.filter(is_public=True, version=obj_version).order_by('id')

    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1

    try:
        scores = paginator.page(page)
    except (EmptyPage, InvalidPage):
        scores = paginator.page(paginator.num_pages)

    return render_to_response(
        'table.html',
        {
            'scores': scores,
            'version_list': version_list,
            'current_version': obj_version,
            'mode_list': mode_list,
            'current_mode': obj_mode
        }
    )


def xor_crypt_string(data, key):
    return ''.join(unichr(ord(x) ^ ord(y)).encode('utf8') for (x,y) in itertools.izip(data, itertools.cycle(key)))


def validation_error(reason):
    return HttpResponse("VALIDATION_ERROR: {}".format(reason))


@csrf_exempt
def submit(request):
    if request.META['HTTP_USER_AGENT'] != settings.EXPECTED_USER_AGENT:
        raise Exception('Invalid useragent')

    input_token = request.POST.get('token')

    if not input_token:
        raise Exception('No token')

    token_unpacked = xor_crypt_string(input_token, settings.CRYPT_SALT)
    tmp_arr = token_unpacked.split("$$$")
    input_version = tmp_arr[3]

    if not input_version:
        return validation_error("no reason")

    if input_version == "2011_winter":
        # Fallback for old version
        input_nickname, input_score, input_seconds, input_version, input_checksums = token_unpacked.split("$$$", 5)
        input_character = None
        input_mode = None
        input_achievements = None
    else:
        (
            input_nickname,
            input_score,
            input_seconds,
            input_version,
            input_character,
            input_mode,
            input_achievements,
            input_checksums
        ) = token_unpacked.split("$$$", 8)

        input_nickname = base64.b64decode(input_nickname)

    if not input_checksums:
        return validation_error("empty checksums")

    crc32_pairs = input_checksums.split("|")

    version_obj = Version.objects.get(version=input_version)
    valid_checksums = Checksum.objects.filter(enabled=True, version=version_obj)

    for valid_checksum in valid_checksums:
        found = False
        for crc32_pair in crc32_pairs:
            the_filename, the_crc32 = crc32_pair.split(":", 2)
            if valid_checksum.filename == the_filename:
                found = True

        if not found:
            return validation_error("Checksum %s missing" % valid_checksum)

    for pair in crc32_pairs:
        the_filename, the_crc32 = pair.split(":", 2)
        try:
            Checksum.objects.get(filename=the_filename, crc32=the_crc32)
        except Checksum.DoesNotExist:
            return validation_error("Checksum %s missing" % the_filename)

    if not input_nickname:
        return validation_error("No nickname")

    if not input_score:
        return validation_error("No score")

    if not input_seconds:
        return validation_error("No seconds")

    try:
        input_score = int(input_score)
    except ValueError:
        return validation_error("Invalid score")

    if input_score < 0:
        return validation_error("Invalid score")

    try:
        input_seconds = int(input_seconds)
    except ValueError:
        return validation_error("Invalid seconds")

    mode_obj = GameMode.objects.get(version=version_obj, number=input_mode)

    UP_ROWS = request.POST.get('up_rows', 2)
    DOWN_ROWS = request.POST.get('down_rows', 2)

    my_score = Score(nickname=input_nickname, score=input_score, seconds=input_seconds, version=version_obj,
                     character=input_character, mode=mode_obj, achievements=input_achievements)
    my_score.save()

    position = Score.objects.filter(
        (Q(score__gt=input_score) | (Q(score=input_score) & Q(seconds__lte=input_seconds))) & Q(
            version=version_obj), Q(mode=mode_obj)).exclude(pk=my_score.pk).count() + 1

    it_score = Score.objects.get(pk=my_score.pk)
    it_score.position = position

    up_rows = Score.objects.filter(
        (Q(score__gt=input_score) | (Q(score=input_score) & Q(seconds__lte=input_seconds))) & Q(
            version=version_obj), Q(mode=mode_obj)).exclude(pk=it_score.pk).order_by('score', 'seconds')[:UP_ROWS]
    down_rows = Score.objects.filter(
        (Q(score__lt=input_score) | (Q(score=input_score) & Q(seconds__gte=input_seconds))) & Q(
            version=version_obj), Q(mode=mode_obj)).exclude(pk=it_score.pk).order_by('-score', '-seconds')[
                :DOWN_ROWS]
    data = list(up_rows) + list(down_rows) + list([it_score])

    return HttpResponse(json.dumps(data), content_type='application/json')


@csrf_exempt
def validate_client(request):
    if request.META['HTTP_USER_AGENT'] != settings.EXPECTED_USER_AGENT:
        return validation_error("Invalid user agent")

    input_version = request.POST.get('version')
    obj_version = Version.objects.get(version=unicode(input_version))

    data = Checksum.objects.filter(enabled=True, version=obj_version).order_by('filename')

    string = ""
    for checksum in data:
        string += "%s\n" % checksum.filename

    resp = HttpResponse(string, content_type="text/plain")
    resp['Cache-Control'] = 'no-cache'
    resp['Content-Length'] = len(string)

    return resp

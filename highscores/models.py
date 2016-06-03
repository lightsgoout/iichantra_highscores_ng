from django.db import models


class Version(models.Model):
    version = models.CharField(max_length=32)
    is_public = models.BooleanField(default=True)
    title = models.CharField(max_length=32)

    def __unicode__(self):
        return self.version


class Checksum(models.Model):
    filename = models.CharField(max_length=128, unique=True)
    crc32 = models.BigIntegerField()
    enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    version = models.ForeignKey(Version)

    def __unicode__(self):
        return "%s (%s)" % (self.filename, self.crc32)


class GameMode(models.Model):
    name = models.CharField(max_length=32)
    version = models.ForeignKey(Version)
    is_public = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s" % self.name


class Score(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    nickname = models.CharField(max_length=32)
    score = models.IntegerField()
    seconds = models.IntegerField()
    version = models.ForeignKey(Version)
    character = models.CharField(max_length=16, null=True, blank=True)
    mode = models.ForeignKey(GameMode, null=True, blank=True)
    achievements = models.IntegerField(null=True, blank=True)

    position = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return "%s (%s seconds) by %s at %s" % (self.score, self.seconds, self.nickname, self.date)

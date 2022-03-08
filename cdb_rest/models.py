from __future__ import unicode_literals
# from django.conf import settings

from django.db import models
from django.utils.encoding import smart_text as smart_unicode
# from django.utils.translation import ugettext_lazy as _

class GlobalTagStatus(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    #name = models.CharField(primary_key=True, max_length=80, db_column='name', unique=True)
    name = models.CharField(max_length=80, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'GlobalTagStatus'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class GlobalTagType(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    #name = models.CharField(primary_key=True, max_length=80, db_column='name',unique=True)
    name = models.CharField(max_length=80, db_column='name',unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'GlobalTagType'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class GlobalTag(models.Model):
    #id = models.BigIntegerField(primary_key=True, db_column='id')
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    name = models.CharField(max_length=80, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    status = models.ForeignKey(GlobalTagStatus, on_delete=models.CASCADE)
    type = models.ForeignKey(GlobalTagType, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'GlobalTag'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class PayloadType(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    #name = models.CharField(primary_key=True, max_length=80, db_column='name',unique=True)
    name = models.CharField(max_length=80, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'PayloadType'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class PayloadListIdSequence(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)

    class Meta:
        db_table = u'PayloadListIdSequence'

    def __int__(self):
        return self.id
    def __str__(self):
        return smart_unicode(self.id)
    def __unicode__(self):
        return smart_unicode(self.id)


class PayloadList(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='id', unique=True)
    #id  = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    name = models.CharField(max_length=255, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    global_tag = models.ForeignKey(GlobalTag, related_name='payload_lists', on_delete=models.CASCADE, null=True)
    payload_type = models.ForeignKey(PayloadType, on_delete=models.CASCADE)
    #freeze_time = models.BigIntegerField(db_column='freeze_time', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'PayloadList'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class PayloadIOV(models.Model):
    #id = models.BigIntegerField(primary_key=True, db_column='id',unique=True)
    id = models.BigAutoField(primary_key = True, db_column = 'id', unique=True)
    payload_url = models.CharField(max_length=255, db_column='payload_url')
    major_iov = models.BigIntegerField(db_column='major_iov')
    minor_iov = models.BigIntegerField(db_column='minor_iov')
    major_iov_end = models.BigIntegerField(db_column='major_iov_end')
    minor_iov_end = models.BigIntegerField(db_column='minor_iov_end')
    payload_list = models.ForeignKey(PayloadList, related_name='payload_iov', on_delete=models.CASCADE, null=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    inserted = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'PayloadIOV'

        indexes = [
            models.Index(fields=['major_iov', 'minor_iov', ]),
        ]

    def __str__(self):
        return smart_unicode(self.payload_url)

    def __unicode__(self):
        return smart_unicode(self.payload_url)




from __future__ import unicode_literals
# from django.conf import settings

from django.db import models
from django.utils.encoding import smart_text as smart_unicode
# from django.utils.translation import ugettext_lazy as _

class GlobalTagStatus(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='id')
    name = models.CharField(max_length=80, db_column='name')
    description = models.CharField(max_length=255, db_column='description')
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'GlobalTagStatus'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class GlobalTagType(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='id')
    name = models.CharField(max_length=80, db_column='name',unique=True)
    description = models.CharField(max_length=255, db_column='description')
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'GlobalTagType'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class GlobalTag(models.Model):
    #id = models.BigIntegerField(primary_key=True, db_column='id')
    id = models.AutoField(primary_key=True, db_column='id')
    name = models.CharField(max_length=80, db_column='name')
    description = models.CharField(max_length=255, db_column='description')
    status = models.ForeignKey(GlobalTagStatus, on_delete=models.CASCADE, null=True)
    type = models.ForeignKey(GlobalTagType, on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'GlobalTag'

    def __unicode__(self):
        return smart_unicode(self.name)

class PayloadType(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='id')
    name = models.CharField(max_length=80, db_column='name',unique=True)
    description = models.CharField(max_length=255, db_column='description')
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'PayloadType'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

class PayloadList(models.Model):
    #id = models.BigIntegerField(primary_key=True, db_column='id')
    id  = models.AutoField(primary_key=True, db_column='id')
    name = models.CharField(max_length=255, db_column='name')
    description = models.CharField(max_length=255, db_column='description')
    global_tag = models.ForeignKey(GlobalTag, related_name='payload_lists', on_delete=models.CASCADE, null=True)
    payload_type = models.ForeignKey(PayloadType, on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'PayloadList'

    def __str__(self):
        return smart_unicode(self.name)

    def __unicode__(self):
        return smart_unicode(self.name)

#class PayloadIOV(models.Model):
#    major_iov = models.BigIntegerField(db_column='major_iov')
#    minor_iov = models.BigIntegerField(db_column='minor_iov')
#    payload = models.ForeignKey(Payload, related_name='payload', on_delete=models.CASCADE, null=True)

class PayloadIOV(models.Model):
    #id = models.BigIntegerField(primary_key=True, db_column='id',unique=True)
    id = models.AutoField(primary_key = True, db_column = 'id')
    payload_url = models.CharField(max_length=255, db_column='payload_url')
    major_iov = models.BigIntegerField(db_column='major_iov')
    minor_iov = models.BigIntegerField(db_column='minor_iov')
    payload_list = models.ForeignKey(PayloadList, related_name='payload_iov', on_delete=models.CASCADE, null=True)
    description = models.CharField(max_length=255, db_column='description')
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'PayloadIOV'

    def __str__(self):
        return smart_unicode(self.payload_url)

    def __unicode__(self):
        return smart_unicode(self.payload_url)




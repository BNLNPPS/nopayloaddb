from __future__ import unicode_literals

from django.db import models
from django.db.models import F
from django.utils.encoding import smart_str


class GlobalTagStatus(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    name = models.CharField(max_length=80, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'GlobalTagStatus'

    def __str__(self):
        return smart_str(self.name)

    def __unicode__(self):
        return smart_str(self.name)


class GlobalTag(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    name = models.CharField(max_length=80, db_column='name', unique=True)
    author = models.CharField(max_length=80, db_column='author', null=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    status = models.ForeignKey(GlobalTagStatus, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'GlobalTag'

    def __str__(self):
        return smart_str(self.name)

    def __unicode__(self):
        return smart_str(self.name)


class PayloadType(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    name = models.CharField(max_length=80, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')

    class Meta:
        db_table = u'PayloadType'

    def __str__(self):
        return smart_str(self.name)

    def __unicode__(self):
        return smart_str(self.name)


class PayloadListIdSequence(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)

    class Meta:
        db_table = u'PayloadListIdSequence'

    def __int__(self):
        return self.id

    def __str__(self):
        return smart_str(self.id)

    def __unicode__(self):
        return smart_str(self.id)


class PayloadList(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column='id', unique=True)
    name = models.CharField(max_length=255, db_column='name', unique=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    global_tag = models.ForeignKey(GlobalTag, related_name='payload_lists', on_delete=models.CASCADE, null=True)
    payload_type = models.ForeignKey(PayloadType, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')

    class Meta:
        db_table = u'PayloadList'

    def __str__(self):
        return smart_str(self.name)

    def __unicode__(self):
        return smart_str(self.name)


class PayloadIOV(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='id', unique=True)
    payload_url = models.CharField(max_length=255, db_column='payload_url')
    checksum = models.CharField(max_length=255, db_column='checksum')
    major_iov = models.BigIntegerField(db_column='major_iov')
    minor_iov = models.BigIntegerField(db_column='minor_iov')
    major_iov_end = models.BigIntegerField(db_column='major_iov_end')
    minor_iov_end = models.BigIntegerField(db_column='minor_iov_end')
    payload_list = models.ForeignKey(PayloadList, related_name='payload_iov', on_delete=models.CASCADE, null=True)
    description = models.CharField(max_length=255, db_column='description', null=True)
    inserted = models.DateTimeField(auto_now_add=True, db_column='created')
    updated = models.DateTimeField(auto_now=True, db_column='updated')
    comb_iov = models.DecimalField(db_column='comb_iov', max_digits=38, decimal_places=19, null=True)

    class Meta:
        db_table = u'PayloadIOV'

        indexes = [
            models.Index('payload_list', F('comb_iov').desc(nulls_last=True), name='covering_idx')
        ]

    def __str__(self):
        return smart_str(self.payload_url)

    def __unicode__(self):
        return smart_str(self.payload_url)

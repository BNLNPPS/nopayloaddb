# from django.contrib.auth.models import User
from rest_framework import serializers
from cdb_rest.models import GlobalTag, GlobalTagStatus, GlobalTagType, PayloadType, PayloadList, PayloadIOV


class GlobalTagStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = GlobalTagStatus
        fields = ("id","name","created")


class GlobalTagTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = GlobalTagType
        fields = ("id", "name", "created")

class GlobalTagCreateSerializer(serializers.ModelSerializer):

    #type = serializers.SlugRelatedField(slug_field="name", queryset=GlobalTagType.objects.all())

    class Meta:
        model = GlobalTag
        fields = ("id", "name", "status", "type", "created", "updated")
        #depth = 1

class PayloadTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayloadType
        fields = ("id", "name", "created")

class PayloadListCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayloadList
        fields = ("id", "name", "global_tag", "payload_type", "created")

class PayloadIOVSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayloadIOV
        fields = ("id", "payload_url", "major_iov", "minor_iov", "payload_list", "created")
        #depth = 1

class PayloadListReadSerializer(serializers.ModelSerializer):

    payload_iov = PayloadIOVSerializer(many=True, read_only=True)

    class Meta:
        model = PayloadList
        fields = ("id", "name", "global_tag", "payload_type", "payload_iov", "created")
        #depth = 1

class GlobalTagReadSerializer(serializers.ModelSerializer):

    #type = serializers.SlugRelatedField(slug_field="name", queryset=GlobalTagType.objects.all())
    payload_lists = PayloadListReadSerializer(many=True, read_only=True)

    class Meta:
        model = GlobalTag
        fields = ("id", "name", "status", "type", "payload_lists", "created", "updated")
        depth = 1








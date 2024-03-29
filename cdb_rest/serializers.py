from rest_framework import serializers
from cdb_rest.models import GlobalTag, GlobalTagStatus, PayloadType, PayloadList, PayloadIOV


class GlobalTagStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = GlobalTagStatus
        fields = ("id", "name", "created")


class GlobalTagCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = GlobalTag
        fields = ("id", "name", "author", "status", "created", "updated")


class PayloadTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayloadType
        fields = ("id", "name", "created")


class PayloadListCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayloadList
        fields = ("id", "name", "global_tag", "payload_type", "created")


class PayloadListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayloadList
        fields = ("id", "name", "global_tag", "payload_type", "created")


class PayloadIOVSerializer(serializers.ModelSerializer):

    payload_list = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = PayloadIOV
        fields = ("id", "payload_url", "checksum", "major_iov", "minor_iov", "comb_iov", "major_iov_end", "minor_iov_end", "payload_list", "inserted")


class PayloadListReadSerializer(serializers.ModelSerializer):

    payload_iov = PayloadIOVSerializer(many=True, read_only=True)
    payload_type = serializers.SlugRelatedField(slug_field="name", read_only=True)
    global_tag = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = PayloadList
        fields = ("id", "name", "global_tag", "payload_type", "payload_iov", "created")


class GlobalTagReadSerializer(serializers.ModelSerializer):

    payload_lists = PayloadListReadSerializer(many=True, read_only=True)

    class Meta:
        model = GlobalTag
        fields = ("id", "name", "author", "status", "payload_lists", "created", "updated")
        depth = 1


class GlobalTagListSerializer(serializers.ModelSerializer):

    payload_lists_count = serializers.SerializerMethodField()
    payload_iov_count = serializers.SerializerMethodField()
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)
    type = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = GlobalTag
        fields = ("id", "name", "author", "status", "type", "payload_lists_count", "payload_iov_count", "created", "updated")

    @staticmethod
    def get_payload_lists_count(obj):
        return obj.payload_lists.count()

    @staticmethod
    def get_payload_iov_count(obj):
        return PayloadIOV.objects.filter(payload_list__in=obj.payload_lists.all()).count()


class PayloadListReadShortSerializer(serializers.ModelSerializer):

    payload_type = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = PayloadList
        fields = ("payload_type", "name")

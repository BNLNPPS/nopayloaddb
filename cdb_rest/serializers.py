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


# ── Browse serializers (lightweight, for paginated endpoints) ────────────────

class GlobalTagBrowseSerializer(serializers.ModelSerializer):
    """GT list item for paginated browsing; counts come from queryset annotations."""

    status = serializers.SlugRelatedField(slug_field="name", read_only=True)
    payload_lists_count = serializers.IntegerField(read_only=True, default=0)
    payload_iov_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = GlobalTag
        fields = ("id", "name", "author", "status", "payload_lists_count", "payload_iov_count", "created", "updated")


class PayloadListBrowseSerializer(serializers.ModelSerializer):
    """PayloadList without nested IOVs; iov_count comes from queryset annotation."""

    global_tag = serializers.SlugRelatedField(slug_field="name", read_only=True)
    payload_type = serializers.SlugRelatedField(slug_field="name", read_only=True)
    iov_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = PayloadList
        fields = ("id", "name", "global_tag", "payload_type", "iov_count", "created")


class PayloadIOVBrowseSerializer(serializers.ModelSerializer):
    """Flat PayloadIOV row with payload list / global tag / payload type names."""

    payload_list = serializers.SlugRelatedField(slug_field="name", read_only=True)
    global_tag = serializers.SerializerMethodField()
    payload_type = serializers.SerializerMethodField()

    class Meta:
        model = PayloadIOV
        fields = ("id", "payload_url", "checksum", "major_iov", "minor_iov",
                  "major_iov_end", "minor_iov_end", "payload_list", "global_tag", "payload_type", "inserted")

    @staticmethod
    def get_global_tag(obj):
        pl = obj.payload_list
        return pl.global_tag.name if pl and pl.global_tag else None

    @staticmethod
    def get_payload_type(obj):
        pl = obj.payload_list
        return pl.payload_type.name if pl and pl.payload_type else None

import sys
import time
import random
from decimal import Decimal

from django.conf import settings
from django.db import transaction, connections
from django.db.models import Prefetch, Q, Max
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView, CreateAPIView, ListAPIView,
    UpdateAPIView, RetrieveAPIView, DestroyAPIView
)
from rest_framework.response import Response
from rest_framework.views import APIView

from cdb_rest.models import (
    GlobalTag, GlobalTagStatus, PayloadList, PayloadType,
    PayloadIOV, PayloadListIdSequence
)
from cdb_rest.serializers import (
    GlobalTagCreateSerializer, GlobalTagReadSerializer,
    GlobalTagStatusSerializer, GlobalTagListSerializer,
    PayloadListCreateSerializer, PayloadListReadSerializer,
    PayloadTypeSerializer, PayloadIOVSerializer,
    PayloadListSerializer, PayloadListReadShortSerializer
)
import cdb_rest.queries
from .iov_comparisons import get_iov_config, compute_comb_iov
from .utils import load_permission_plugin, load_auth_class


class WriteAuthMixin:
    """Require JWT authentication for write methods (POST/PUT/PATCH/DELETE), allow anonymous reads."""
    def get_authenticators(self):
        if self.request and self.request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            auth_class = load_auth_class()
            if auth_class:
                return [auth_class()]
        return []


# ── GlobalTag views ──────────────────────────────────────────────────────────

class GlobalTagDetailAPIView(WriteAuthMixin, RetrieveAPIView):
    serializer_class = GlobalTagReadSerializer
    queryset = GlobalTag.objects.all()


class GlobalTagByNameDetailAPIView(WriteAuthMixin, RetrieveAPIView):
    serializer_class = GlobalTagReadSerializer
    queryset = GlobalTag.objects.all()
    lookup_url_kwarg = 'globalTagName'

    def get_object(self):
        gt_name = self.kwargs.get('globalTagName')
        queryset = GlobalTag.objects.all()
        obj = get_object_or_404(queryset, name=gt_name)
        return obj


class TimeoutListAPIView(WriteAuthMixin, ListAPIView):
    """Test endpoint that simulates a long-running request by sleeping.

    Accepts an optional duration in seconds (``/timeout/<seconds>``), clamped
    to ``MAX_TIMEOUT_SECONDS`` so a caller cannot hold a worker indefinitely.
    Without a parameter it falls back to ``DEFAULT_TIMEOUT_SECONDS``.
    """

    DEFAULT_TIMEOUT_SECONDS = 1800
    MAX_TIMEOUT_SECONDS = 1800

    def list(self, request, *args, **kwargs):
        seconds = self.kwargs.get('seconds')
        if seconds is None:
            seconds = self.DEFAULT_TIMEOUT_SECONDS
        seconds = min(seconds, self.MAX_TIMEOUT_SECONDS)
        time.sleep(seconds)
        return Response()


class GlobalTagListCreationAPIView(WriteAuthMixin, ListCreateAPIView):
    """List all GlobalTags (GET) or create a new one (POST). Requires admin permission to create."""
    serializer_class = GlobalTagCreateSerializer

    def get_queryset(self):
        return GlobalTag.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = GlobalTagReadSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data
        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "admin", "name": data['name']}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            gt_status = GlobalTagStatus.objects.get(name=data['status'])
            data['status'] = gt_status.pk
        except KeyError:
            return Response({"detail": "GlobalTagStatus not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "GlobalTag creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "GlobalTag was not saved to DB."}, status=500)

        ret = serializer.data
        ret['status'] = gt_status.name
        return Response(ret)


class GlobalTagDeleteAPIView(WriteAuthMixin, DestroyAPIView):
    """Delete a GlobalTag by name. Locked and frozen GTs are immutable."""
    serializer_class = GlobalTagReadSerializer
    lookup_url_kwarg = 'globalTagName'
    lookup_field = 'name'

    def get_gtag(self):
        try:
            return GlobalTag.objects.get(name=self.kwargs['globalTagName'])
        except GlobalTag.DoesNotExist:
            return None

    def destroy(self, request, *args, **kwargs):
        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "admin", "name": self.kwargs['globalTagName']}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        gt = self.get_gtag()
        if not gt:
            return Response({"detail": "GlobalTag %s doesn't exist" % self.kwargs['globalTagName']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        gt_status = GlobalTagStatus.objects.get(id=gt.status_id)
        if gt_status.name in ['locked', 'frozen']:
            return Response({"detail": "Global Tag is %s." % gt_status.name}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(gt)
        if not ret:
            ret = {"detail": "Global tag %s deleted." % gt.name}
        return Response(ret)



# ── PayloadIOV views ─────────────────────────────────────────────────────────

class PayloadIOVDeleteAPIView(WriteAuthMixin, DestroyAPIView):
    """Delete a PayloadIOV. Frozen GTs are immutable."""
    serializer_class = PayloadIOVSerializer

    def get_object(self):
        if 'major_iov_end' not in self.kwargs:
            self.kwargs['major_iov_end'] = sys.maxsize
        if 'minor_iov_end' not in self.kwargs:
            self.kwargs['minor_iov_end'] = sys.maxsize

        try:
            return PayloadIOV.objects.get(
                payload_list__global_tag__name=self.kwargs['globalTagName'],
                payload_list__payload_type__name=self.kwargs['payloadType'],
                major_iov=self.kwargs['major_iov'],
                minor_iov=self.kwargs['minor_iov'],
                major_iov_end=self.kwargs['major_iov_end'],
                minor_iov_end=self.kwargs['minor_iov_end']
            )
        except:
            return None

    def destroy(self, request, *args, **kwargs):
        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "admin", "name": self.kwargs['globalTagName']}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        piov = self.get_object()
        if not piov:
            return Response({"detail": "PayloadIOV with given parameters doesn't exist"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        gt = GlobalTag.objects.get(name=self.kwargs['globalTagName'])
        gt_status = GlobalTagStatus.objects.get(id=gt.status_id)

        if gt_status.name == 'frozen':
            return Response({"detail": "Global Tag is %s." % gt_status.name}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(piov)
        if not ret:
            ret = {"detail": "PayloadIOV %s deleted." % piov.payload_url}
        return Response(ret)



# ── PayloadType views ────────────────────────────────────────────────────────

class PayloadTypeDeleteAPIView(WriteAuthMixin, DestroyAPIView):
    """Delete a PayloadType. Fails if any PayloadLists reference it."""
    serializer_class = PayloadTypeSerializer

    def get_ptype(self):
        try:
            return PayloadType.objects.get(name=self.kwargs['payloadTypeName'])
        except PayloadType.DoesNotExist:
            return None

    def get_plists(self, ptype):
        try:
            return PayloadList.objects.filter(payload_type=ptype)
        except PayloadList.DoesNotExist:
            return None

    def destroy(self, request, *args, **kwargs):
        ret = {}
        ptype = self.get_ptype()
        if not ptype:
            return Response({"detail": "PayloadType %s doesn't exist" % self.kwargs['payloadTypeName']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        plists = list(self.get_plists(ptype))
        if plists:
            return Response({"detail": "PayloadType is used by %d PayloadLists" % len(plists)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(ptype)
        if not ret:
            ret = {"detail": "Payload Type %s deleted." % ptype.name}
        return Response(ret)



# ── PayloadList views ────────────────────────────────────────────────────────

class PayloadListDeleteAPIView(WriteAuthMixin, DestroyAPIView):
    """Delete a PayloadList. Fails if it contains any PayloadIOVs."""
    serializer_class = PayloadListSerializer

    def get_plist(self):
        try:
            return PayloadList.objects.get(name=self.kwargs['payloadListName'])
        except PayloadList.DoesNotExist:
            return None

    def get_piovs(self, plist):
        try:
            return PayloadIOV.objects.filter(payload_list=plist)
        except PayloadIOV.DoesNotExist:
            return None

    def destroy(self, request, *args, **kwargs):
        ret = {}
        plist = self.get_plist()
        if not plist:
            return Response({"detail": "PayloadList %s doesn't exist" % self.kwargs['payloadListName']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        piovs = list(self.get_piovs(plist))
        if piovs:
            return Response({"detail": "PayloadList contains %d PayloadIOVs" % len(piovs)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(plist)
        if not ret:
            ret = {"detail": "Payload Type %s deleted." % plist.name}
        return Response(ret)



# ── List views ───────────────────────────────────────────────────────────────

class GlobalTagsListAPIView(WriteAuthMixin, ListAPIView):
    """List all GlobalTags with attached PayloadLists summary."""
    serializer_class = GlobalTagListSerializer

    def get_queryset(self):
        return GlobalTag.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = GlobalTagListSerializer(queryset, many=True)
        return Response(serializer.data)


class GlobalTagsPayloadListsListAPIView(WriteAuthMixin, ListAPIView):
    """List PayloadLists for a given GlobalTag as a {payload_type: name} map."""

    def get_queryset(self):
        gt_name = self.kwargs.get('globalTagName')
        return PayloadList.objects.filter(global_tag__name=gt_name)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = PayloadListReadShortSerializer(queryset, many=True)
        ret = {}
        if serializer.data:
            for pl in serializer.data:
                ret[pl['payload_type']] = pl['name']
        return Response(ret)



# ── Status views ─────────────────────────────────────────────────────────────

class GlobalTagStatusCreationAPIView(WriteAuthMixin, ListCreateAPIView):
    """List or create GlobalTag statuses (unlocked, locked, frozen)."""
    serializer_class = GlobalTagStatusSerializer
    lookup_field = 'name'

    def get_queryset(self):
        return GlobalTagStatus.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = GlobalTagStatusSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "GlobalTagStatus creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "GlobalTagStatus was not saved to DB."}, status=500)

        return Response(serializer.data)



# ── Creation views ───────────────────────────────────────────────────────────

class PayloadListListCreationAPIView(WriteAuthMixin, ListCreateAPIView):
    """List all PayloadLists (GET) or create a new one (POST). Auto-generates name from PayloadType + sequence ID."""
    serializer_class = PayloadListCreateSerializer

    @staticmethod
    def get_next_id():
        return PayloadListIdSequence.objects.create()

    def get_queryset(self):
        return PayloadList.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadListReadSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data
        next_id = self.get_next_id()

        data['id'] = int(next_id)
        data['name'] = data['payload_type'] + '_' + str(next_id)

        try:
            payload_type = PayloadType.objects.get(name=data['payload_type'])
            data['payload_type'] = payload_type.pk
        except KeyError:
            return Response({"detail": "PayloadType not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data['global_tag'] = None

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "PayloadList creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "PayloadList was not saved to DB."}, status=500)

        ret = serializer.data
        ret['payload_type'] = payload_type.name
        return Response(ret)


class PayloadListDetailAPIView(WriteAuthMixin, RetrieveAPIView):
    serializer_class = PayloadListCreateSerializer
    queryset = PayloadList.objects.all()


class PayloadTypeListCreationAPIView(WriteAuthMixin, ListCreateAPIView):
    """List all PayloadTypes (GET) or create a new one (POST)."""
    serializer_class = PayloadTypeSerializer

    def get_queryset(self):
        return PayloadType.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "PayloadType creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "PayloadType was not saved to DB."}, status=500)

        return Response(serializer.data)


class PayloadIOVListCreationAPIView(WriteAuthMixin, ListCreateAPIView):
    """List all PayloadIOVs (GET) or create a new one (POST). Validates IOV ranges based on CDB_IOV_MODE."""
    serializer_class = PayloadIOVSerializer

    def get_queryset(self):
        return PayloadIOV.objects.all()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadIOVSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        iov_config = get_iov_config(settings.CDB_IOV_MODE)

        data = request.data

        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "createpayload", "name": self.kwargs['payload_url']}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        if 'major_iov_end' not in data:
            data['major_iov_end'] = sys.maxsize
        if 'minor_iov_end' not in data:
            data['minor_iov_end'] = sys.maxsize

        data['comb_iov'] = compute_comb_iov(data['major_iov'], data['minor_iov'])

        if iov_config['is_invalid_iov_range'](data):
            err_msg = "%s PayloadIOV ending IOVs should be greater or equal than starting." \
                      " Provided end IOVs: major_iov: %d major_iov_end: %d minor_iov: %d minor_iov_end: %d" % \
                      (data['payload_url'], data['major_iov'], data['major_iov_end'], data['minor_iov'],
                       data['minor_iov_end'])
            return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "PayloadIOV creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "PayloadIOV was not saved to DB."}, status=500)

        ret = serializer.data
        return Response(ret)


class PayloadIOVDetailAPIView(WriteAuthMixin, RetrieveAPIView):
    serializer_class = PayloadIOVSerializer
    queryset = PayloadIOV.objects.all()


class PayloadIOVBulkCreationAPIView(WriteAuthMixin, CreateAPIView):
    """Bulk-create PayloadIOVs from a JSON array. Skips individual validation for performance."""
    serializer_class = PayloadIOVSerializer

    def get_queryset(self):
        return PayloadIOV.objects.all()

    def create(self, request, *args, **kwargs):
        data = request.data
        batch = [PayloadIOV(id=None, payload_url=obj["payload_url"],
                            major_iov=obj["major_iov"], minor_iov=obj["minor_iov"],
                            major_iov_end=sys.maxsize, minor_iov_end=sys.maxsize,
                            payload_list=PayloadList.objects.get(name=obj['payload_list']),
                            inserted=None,
                            comb_iov=Decimal(Decimal(obj["major_iov"]) + Decimal(obj["minor_iov"]) / 10 ** 19))
                 for obj in data]

        PayloadIOV.objects.bulk_create(batch)
        return Response()



# ── Clone / Attach views ─────────────────────────────────────────────────────

class GlobalTagCloneAPIView(WriteAuthMixin, CreateAPIView):
    """Deep-copy a GlobalTag: duplicates the GT, all its PayloadLists, and their PayloadIOVs."""
    serializer_class = GlobalTagReadSerializer

    def get_global_tag(self):
        source_name = self.kwargs.get('globalTagName')
        return GlobalTag.objects.get(name=source_name)

    def get_clone_name(self):
        return self.kwargs.get('cloneName')

    @staticmethod
    def get_payload_lists(global_tag):
        return PayloadList.objects.filter(global_tag=global_tag)

    @staticmethod
    def get_payload_iovs(payload_list):
        return PayloadIOV.objects.filter(payload_list=payload_list)

    @staticmethod
    def get_next_id():
        return PayloadListIdSequence.objects.create()

    @transaction.atomic
    def create(self, request, globalTagName, cloneName):
        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "admin", "name": self.get_clone_name()}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        global_tag = self.get_global_tag()
        payload_lists = self.get_payload_lists(global_tag)

        global_tag.id = None
        global_tag.name = self.get_clone_name()
        global_tag.status = GlobalTagStatus.objects.get(name='unlocked')
        serializer = GlobalTagCreateSerializer(instance=global_tag, data=model_to_dict(global_tag))
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "GlobalTag creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "GlobalTag was not saved to DB."}, status=500)

        for p_list in payload_lists:
            payload_iovs = self.get_payload_iovs(p_list)
            p_list_id = self.get_next_id()
            p_list.id = p_list_id
            p_list.name = str(p_list.payload_type) + '_' + str(p_list_id)
            p_list.global_tag = global_tag

            serializer = PayloadListCreateSerializer(instance=p_list, data=model_to_dict(p_list))
            serializer.is_valid(raise_exception=True)

            try:
                instance = serializer.save()
            except Exception as e:
                return Response({"detail": "PayloadList creation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if instance.pk is None:
                return Response({"detail": "PayloadList was not saved to DB."}, status=500)

            rp = []
            for payload in payload_iovs:
                payload.id = None
                payload.payload_list = p_list
                rp.append(payload)

            try:
                PayloadIOV.objects.bulk_create(rp)
            except Exception as e:
                return Response({"detail": "PayloadIOV bulk creation failed."}, status=500)

        serializer = GlobalTagListSerializer(global_tag)
        return Response(serializer.data)



# ── Query views ──────────────────────────────────────────────────────────────

class PayloadIOVsORMMaxListAPIView(WriteAuthMixin, ListAPIView):
    """Get latest PayloadIOVs per PayloadList for a given GT and IOV point, using ORM MAX aggregation."""

    def get_queryset(self):
        gt_name = self.request.GET.get('gtName')
        major_iov = self.request.GET.get('majorIOV')
        minor_iov = self.request.GET.get('minorIOV')

        tmp1 = PayloadIOV.objects.filter(payload_list__global_tag__name=gt_name) \
            .filter(comb_iov__lte=Decimal(Decimal(major_iov) + Decimal(minor_iov) / 10 ** 19)) \
            .values('payload_list_id').annotate(max_comb_iov=Max('comb_iov'))

        q_statement = Q()
        for pair in tmp1:
            q_statement |= (Q(payload_list_id=pair['payload_list_id']) & Q(comb_iov=pair['max_comb_iov']))

        return PayloadIOV.objects.filter(q_statement)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadIOVSerializer(queryset, many=True)
        return Response(serializer.data)


class PayloadIOVsORMOrderByListAPIView(WriteAuthMixin, ListAPIView):
    """Get latest PayloadIOVs per PayloadList using ORM ORDER BY + DISTINCT."""

    def get_queryset(self):
        gt_name = self.request.GET.get('gtName')
        major_iov = self.request.GET.get('majorIOV')
        minor_iov = self.request.GET.get('minorIOV')

        queryset = PayloadIOV.objects.filter(payload_list__global_tag__name=gt_name) \
            .filter(comb_iov__lte=Decimal(Decimal(major_iov) + Decimal(minor_iov) / 10 ** 19)) \
            .order_by('payload_list_id', '-comb_iov').distinct('payload_list_id')
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadIOVSerializer(queryset, many=True)
        return Response(serializer.data)


def _resolve_query(setting_name, default):
    """Resolve a SQL query function by name from settings, falling back to default."""
    query_name = getattr(settings, setting_name, None)
    if query_name:
        return getattr(cdb_rest.queries, query_name)
    return default


class PayloadIOVsSQLListAPIView(WriteAuthMixin, ListAPIView):
    """Get PayloadIOVs using raw SQL for performance. Distributes reads across read replicas."""

    def list(self, request):
        read_dbs = [db for db in settings.DATABASES.keys() if db.startswith("read_db_")]
        read_db = random.choice(read_dbs) if read_dbs else "default"

        query = _resolve_query('CDB_PAYLOAD_IOVS_QUERY', cdb_rest.queries.get_payload_iovs)

        with connections[read_db].cursor() as cursor:
            cursor.execute(query,
                           {'my_major_iov': self.request.GET.get('majorIOV'),
                            'my_minor_iov': self.request.GET.get('minorIOV'),
                            'my_gt': self.request.GET.get('gtName')})
            if self.request.GET.get('shape') == 'dict':
                columns = [col[0] for col in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                result = cursor.fetchall()

        return Response(result)


class PayloadIOVsRangesListAPIView(WriteAuthMixin, ListAPIView):
    """Get PayloadIOVs within a given IOV range, grouped by PayloadList."""

    def get_queryset(self):
        gt_name = self.request.GET.get('gtName')
        start_major_iov = self.request.GET.get('startMajorIOV')
        start_minor_iov = self.request.GET.get('startMinorIOV')
        end_major_iov = self.request.GET.get('endMajorIOV')
        end_minor_iov = self.request.GET.get('endMinorIOV')

        q = {'major_iov__gte': start_major_iov, 'minor_iov__gte': start_minor_iov}
        if end_major_iov != '-1':
            q.update({'major_iov__lte': end_major_iov})
        if end_minor_iov != '-1':
            q.update({'minor_iov__lte': end_minor_iov})

        p_lists = PayloadList.objects.filter(global_tag__name=gt_name)
        piov_ids = []
        for pl in p_lists:
            q.update({'payload_list': pl})
            piovs = PayloadIOV.objects.filter(**q).values_list('id', flat=True)
            if piovs:
                piov_ids.extend(piovs)

        queryset = PayloadIOV.objects.filter(id__in=piov_ids)

        return PayloadList.objects.filter(global_tag__name=gt_name) \
            .prefetch_related(Prefetch('payload_iov', queryset=queryset)) \
            .filter(payload_iov__in=queryset).distinct()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadListReadSerializer(queryset, many=True)
        return Response(serializer.data)


class PayloadListAttachAPIView(WriteAuthMixin, UpdateAPIView):
    """Attach a PayloadList to a GlobalTag. Detaches any existing list of the same PayloadType first."""
    serializer_class = PayloadListCreateSerializer

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        data = request.data

        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "admin", "name": data['global_tag']}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            p_list = PayloadList.objects.get(name=data['payload_list'])
        except KeyError:
            return Response({"detail": "PayloadList not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            global_tag = GlobalTag.objects.get(name=data['global_tag'])
        except KeyError:
            return Response({"detail": "GlobalTag not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        pl_type = p_list.payload_type

        gt_status = GlobalTagStatus.objects.get(id=global_tag.status_id)
        if gt_status.name == 'frozen':
            return Response({"detail": "Global Tag is %s." % gt_status.name}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if (PayloadList.objects.filter(global_tag=global_tag, payload_type=pl_type) and gt_status.name == 'locked'):
            return Response({"detail": "Payload List of type %s already attached and Global Tag is locked." % pl_type}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        PayloadList.objects.filter(global_tag=global_tag, payload_type=pl_type).update(global_tag=None)
        p_list.global_tag = global_tag

        serializer = PayloadListCreateSerializer(instance=p_list, data=model_to_dict(p_list))
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "PayloadList update failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "PayloadList was not saved to DB."}, status=500)

        serializer = GlobalTagCreateSerializer(instance=global_tag, data=model_to_dict(global_tag))
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "GlobalTag update failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "GlobalTag was not updated in the DB."}, status=500)

        serializer = PayloadListSerializer(p_list)
        ret = serializer.data
        ret['global_tag'] = global_tag.name
        ret['payload_type'] = pl_type.name
        return Response(ret)


class PayloadIOVAttachAPIView(WriteAuthMixin, UpdateAPIView):
    """
    Attach a PayloadIOV to a PayloadList. Handles overlap resolution:
    - Locked GT: rejects conflicting IOVs (append-only), with special case for open-ended Online GT IOVs.
    - Unlocked GT: splits/trims existing IOVs to accommodate the new one.
    """
    serializer_class = PayloadIOVSerializer

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        iov_config = get_iov_config(settings.CDB_IOV_MODE)
        offset = iov_config['next_iov_offset']

        data = request.data

        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "createiov", "name": data['global_tag']}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            p_list = PayloadList.objects.get(name=data['payload_list'])
        except KeyError:
            return Response({"detail": "PayloadList not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            piov = PayloadIOV.objects.get(id=data['piov_id'])
        except KeyError:
            return Response({"detail": "PayloadIOV not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        is_gt_locked = False
        if p_list.global_tag:
            gt_status = GlobalTagStatus.objects.get(id=p_list.global_tag.status_id)
            if gt_status.name == 'locked':
                is_gt_locked = True
            elif gt_status.name == 'frozen':
                return Response({"detail": "Global Tag is %s." % gt_status.name}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        list_piovs = PayloadIOV.objects.filter(payload_list=p_list)

        if is_gt_locked:
            piovs = list_piovs.filter(major_iov=piov.major_iov, minor_iov=piov.minor_iov)
            if piovs:
                payload_url, major_iov, minor_iov, major_iov_end, minor_iov_end = \
                    piovs.values_list('payload_url', 'major_iov', 'minor_iov', 'major_iov_end', 'minor_iov_end')[0]
                err_msg = "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, " \
                          "minor_iov_end) (%d,%d,%d,%d). Conflicts with existing IOV %s (%d,%d,%d,%d)" % \
                          (piov.major_iov, piov.minor_iov, piov.major_iov_end, piov.minor_iov_end, payload_url,
                           major_iov, minor_iov, major_iov_end, minor_iov_end)
                return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Special case for Online GT - allow open IOV recover last open IOV
            special_case = False
            if (piov.major_iov_end == 0 or piov.major_iov_end == sys.maxsize) and piov.minor_iov_end == sys.maxsize:
                piovs = list_piovs.all().order_by('-comb_iov')
                if piovs:
                    comb_iov, major_iov_end, minor_iov_end = piovs.values_list('comb_iov', 'major_iov_end', 'minor_iov_end')[0]
                    if (major_iov_end == 0 or major_iov_end == sys.maxsize) and minor_iov_end == sys.maxsize:
                        if comb_iov < piov.comb_iov:
                            special_case = True

            if not special_case:
                piovs = list_piovs.filter(Q(major_iov__lt=piov.major_iov) |
                                          Q(major_iov=piov.major_iov, minor_iov__lt=piov.minor_iov)) \
                    .order_by('-major_iov', '-minor_iov')
                if piovs:
                    payload_url, major_iov, minor_iov, major_iov_end, minor_iov_end = \
                        piovs.values_list('payload_url', 'major_iov', 'minor_iov', 'major_iov_end', 'minor_iov_end')[0]
                    if iov_config['is_conflicting_iov_tail'](piov, major_iov_end, minor_iov_end):
                        err_msg = "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, " \
                                  "minor_iov_end) (%d,%d,%d,%d). Conflicts with existing IOV %s (%d,%d,%d,%d)" % \
                                  (piov.major_iov, piov.minor_iov, piov.major_iov_end, piov.minor_iov_end, payload_url,
                                   major_iov, minor_iov, major_iov_end, minor_iov_end)
                        return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                piovs = list_piovs.filter(Q(major_iov__gt=piov.major_iov) |
                                          Q(major_iov=piov.major_iov, minor_iov__gt=piov.minor_iov)) \
                    .order_by('major_iov', 'minor_iov')
                if piovs:
                    payload_url, major_iov, minor_iov, major_iov_end, minor_iov_end = \
                        piovs.values_list('payload_url', 'major_iov', 'minor_iov', 'major_iov_end', 'minor_iov_end')[0]
                    if iov_config['is_conflicting_iov_end'](piov, major_iov_end, minor_iov_end):
                        err_msg = "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, " \
                                  "minor_iov_end) (%d,%d,%d,%d). Conflicts with existing IOV %s (%d,%d,%d,%d)" % \
                                  (piov.major_iov, piov.minor_iov, piov.major_iov_end, piov.minor_iov_end, payload_url,
                                   major_iov, minor_iov, major_iov_end, minor_iov_end)
                        return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            list_piovs.filter(
                Q(major_iov__gt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__gte=piov.minor_iov)) \
                .filter(Q(major_iov_end__lt=piov.major_iov_end) | Q(major_iov_end=piov.major_iov_end,
                                                                    minor_iov_end__lte=piov.minor_iov_end)) \
                .update(payload_list=None)

            piovs = list_piovs.filter(
                Q(major_iov__lt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__lte=piov.minor_iov)).order_by(
                '-major_iov', '-minor_iov')
            if piovs:
                major_iov_end, minor_iov_end = piovs.values_list('major_iov_end', 'minor_iov_end')[0]
                if iov_config['is_conflicting_iov'](piov, major_iov_end, minor_iov_end):
                    piovs[0].major_iov_end = piov.major_iov + offset
                    piovs[0].minor_iov_end = piov.minor_iov + offset
                    piovs[0].save(update_fields=['major_iov_end', 'minor_iov_end'])

                if iov_config['is_iov_end_inside'](piov, major_iov_end, minor_iov_end):
                    third_piov = piovs[0]
                    third_piov.major_iov = piov.major_iov_end
                    third_piov.minor_iov = piov.minor_iov_end
                    third_piov.comb_iov = Decimal(Decimal(third_piov.major_iov) + Decimal(third_piov.minor_iov) / 10 ** 19)
                    third_piov.major_iov_end = major_iov_end + offset
                    third_piov.minor_iov_end = minor_iov_end + offset
                    third_piov.id = None
                    third_piov.save()

            piovs = list_piovs.filter(
                Q(major_iov__gt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__gt=piov.minor_iov)).order_by(
                'major_iov', 'minor_iov')
            if piovs:
                major_iov, minor_iov = piovs.values_list('major_iov', 'minor_iov')[0]
                if iov_config['is_conflicting_iov_end'](piov, major_iov_end, minor_iov_end):
                    piovs[0].major_iov = piov.major_iov_end
                    piovs[0].minor_iov = piov.minor_iov_end
                    piovs[0].comb_iov = Decimal(Decimal(piovs[0].major_iov) + Decimal(piovs[0].minor_iov) / 10 ** 19)
                    piovs[0].save(update_fields=['major_iov', 'minor_iov', 'comb_iov'])

        piov.payload_list = p_list
        piov.comb_iov = Decimal(Decimal(piov.major_iov) + Decimal(piov.minor_iov) / 10 ** 19)

        serializer = PayloadIOVSerializer(instance=piov, data=model_to_dict(piov))
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "PayloadIOV update failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "PayloadIOV was not updated in the DB."}, status=500)

        serializer = PayloadListCreateSerializer(instance=p_list, data=model_to_dict(p_list))
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "PayloadList update failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "PayloadList was not updated in the DB."}, status=500)

        serializer = PayloadIOVSerializer(piov)
        ret = serializer.data
        return Response(ret)



# ── Status change views ──────────────────────────────────────────────────────

class GlobalTagChangeStatusAPIView(WriteAuthMixin, UpdateAPIView):
    """Change a GlobalTag's status (e.g. unlocked -> locked -> frozen)."""
    serializer_class = GlobalTagCreateSerializer

    def get_global_tag(self):
        global_tag_name = self.kwargs.get('globalTagName')
        return GlobalTag.objects.get(name=global_tag_name)

    def get_gt_status(self):
        gt_status = self.kwargs.get('newStatus')
        return GlobalTagStatus.objects.get(name=gt_status)

    def put(self, request, *args, **kwargs):
        plugin = load_permission_plugin()
        target_object = {"object": "GlobalTag", "role": "admin", "name": self.kwargs.get('globalTagName')}
        if not plugin.has_permission(request, target_object):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            gt = self.get_global_tag()
        except KeyError:
            return Response({"detail": "GlobalTag not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            gt_status = self.get_gt_status()
        except KeyError:
            return Response({"detail": "GlobalTag Status not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        gt.status = gt_status
        serializer = GlobalTagCreateSerializer(instance=gt, data=model_to_dict(gt))
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except Exception as e:
            return Response({"detail": "GlobalTag update failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if instance.pk is None:
            return Response({"detail": "GlobalTag was not updated in the DB."}, status=500)

        return Response(serializer.data)



# ── Settings views ───────────────────────────────────────────────────────────

class CDBSettingAPIView(WriteAuthMixin, APIView):
    """Expose CDB_* environment variables as read-only settings."""

    def get(self, request, name):
        if name not in settings.CDB_USER_SETTINGS:
            return Response(
                {"detail": f"Setting '{name}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        value = settings.CDB_USER_SETTINGS.get(name)
        return Response({name: value})

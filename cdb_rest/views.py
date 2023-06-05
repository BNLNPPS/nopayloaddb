import sys
import time

from django.shortcuts import get_object_or_404
from decimal import Decimal

from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, ListAPIView, \
    UpdateAPIView, RetrieveAPIView
from rest_framework.generics import DestroyAPIView
from rest_framework.response import Response
from rest_framework import status
# from rest_framework.renderers import JSONRenderer
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from cdb_rest.authentication import CustomJWTAuthentication

from django.db import transaction, connection

from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import Max
# from django.db.models import QuerySet
# from django.forms.models import model_to_dict

from cdb_rest.models import GlobalTag, GlobalTagStatus, PayloadList, PayloadType, PayloadIOV, PayloadListIdSequence
# from todos.permissions import UserIsOwnerTodo
from cdb_rest.serializers import GlobalTagCreateSerializer, GlobalTagReadSerializer, GlobalTagStatusSerializer, \
    GlobalTagListSerializer
from cdb_rest.serializers import PayloadListCreateSerializer, PayloadListReadSerializer, PayloadTypeSerializer
from cdb_rest.serializers import PayloadIOVSerializer
from cdb_rest.serializers import PayloadListSerializer, PayloadListReadShortSerializer
import cdb_rest.queries


class GlobalTagDetailAPIView(RetrieveAPIView):
    serializer_class = GlobalTagReadSerializer
    queryset = GlobalTag.objects.all()
    # permission_classes = (IsAuthenticated, UserIsOwnerTodo)


class GlobalTagByNameDetailAPIView(RetrieveAPIView):
    serializer_class = GlobalTagReadSerializer
    queryset = GlobalTag.objects.all()
    lookup_url_kwarg = 'globalTagName'

    def get_object(self):
        gt_name = self.kwargs.get('globalTagName')
        queryset = GlobalTag.objects.all()
        obj = get_object_or_404(queryset, name=gt_name)
        return obj


class TimeoutListAPIView(ListAPIView):

    def list(self, request):
        time.sleep(1800)
        return Response()


class GlobalTagListCreationAPIView(ListCreateAPIView):
    # authentication_classes = [CustomJWTAuthentication]
    # permission_classes = (IsAuthenticated)
    serializer_class = GlobalTagCreateSerializer

    def get_queryset(self):
        return GlobalTag.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = GlobalTagReadSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data
        try:
            gt_status = GlobalTagStatus.objects.get(name=data['status'])
            data['status'] = gt_status.pk
        except KeyError:
            return Response({"detail": "GlobalTagStatus not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        ret = serializer.data
        ret['status'] = gt_status.name

        return Response(ret)


class GlobalTagDeleteAPIView(DestroyAPIView):
    serializer_class = GlobalTagReadSerializer
    # permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'globalTagName'
    lookup_field = 'name'

    def get_gtag(self):
        try:
            return GlobalTag.objects.get(name=self.kwargs['globalTagName'])
        except GlobalTag.DoesNotExist:
            return None

    def destroy(self, request, *args, **kwargs):
        gt = self.get_gtag()


        gt_status = GlobalTagStatus.objects.get(id=gt.status_id)
        if gt_status.name == 'locked':
            return Response({"detail": "Global Tag is locked."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(gt)
        if not ret:
            ret = {"detail": "Global tag %s deleted." % gt.name}
        return Response(ret)

class PayloadIOVDeleteAPIView(DestroyAPIView):
    serializer_class = PayloadIOVSerializer
    # permission_classes = [IsAuthenticated]
    #lookup_url_kwargs = ('globalTagName','payloadType','major_iov','minor_iov','major_iov_end','minor_iov_end')
    #lookup_fields = ('payload_list__global_tag__name','payload_list__payload_type__name',
    #                 'major_iov','minor_iov','major_iov_end','minor_iov_end')

    def get_object(self):

        try:
            return PayloadIOV.objects.get(payload_list__global_tag__name=self.kwargs['globalTagName'],
                                         payload_list__payload_type__name=self.kwargs['payloadType'],
                                         major_iov=self.kwargs['major_iov'],
                                         minor_iov=self.kwargs['minor_iov'],
                                         major_iov_end=self.kwargs['major_iov_end'],
                                         minor_iov_end=self.kwargs['minor_iov_end']
                                         )
        except PayloadIOV.DoesNotExist:
            return None

    def destroy(self, request, *args, **kwargs):
        piov = self.get_object()
        if not piov:
            return Response({"detail": "PayloadIOV isn't found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        #gt = GlobalTag.objects.get(name=self.kwargs['globalTagName'])
        #gt_status = GlobalTagStatus.objects.get(id=gt.status_id)

        #if gt_status.name == 'locked':
        #    return Response({"detail": "Global Tag is locked."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(piov)
        if not ret:
            ret = {"detail": "PayloadIOV %s deleted." % piov.payload_url}
        return Response(ret)

class PayloadTypeDeleteAPIView(DestroyAPIView):
    serializer_class = PayloadTypeSerializer
    # permission_classes = [IsAuthenticated]
    #lookup_url_kwarg = 'payloadTypeName'
    #lookup_field = 'name'

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
        ptype = self.get_ptype()
        if not ptype:
            return Response({"detail": "PayloadType isn't found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        plists = list(self.get_plists(ptype))
        if plists:
            return Response({"detail": "PayloadType is used by %d PayloadLists" % len(plists)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ret = self.perform_destroy(ptype)
        if not ret:
            ret = {"detail": "Payload Type %s deleted." % ptype.name}
        return Response(ret)



class GlobalTagsListAPIView(ListAPIView):
    serializer_class = GlobalTagListSerializer

    def get_queryset(self):
        return GlobalTag.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = GlobalTagListSerializer(queryset, many=True)

        return Response(serializer.data)


class GlobalTagsPayloadListsListAPIView(ListAPIView):

    # serializer_class = PayloadListReadSerializer

    def get_queryset(self):
        gt_name = self.kwargs.get('globalTagName')
        return PayloadList.objects.filter(global_tag__name=gt_name)

    def list(self, request, *args, **kwargs):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = PayloadListReadShortSerializer(queryset, many=True)
        ret = {}
        if serializer.data:
            for pl in serializer.data:
                ret[pl['payload_type']] = pl['name']

        return Response(ret)


class GlobalTagStatusCreationAPIView(ListCreateAPIView):
    # authentication_classes = ()
    # permission_classes = ()
    serializer_class = GlobalTagStatusSerializer
    lookup_field = 'name'

    def get_queryset(self):
        return GlobalTagStatus.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = GlobalTagStatusSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data)


class PayloadListListCreationAPIView(ListCreateAPIView):
    # authentication_classes = ()
    # permission_classes = ()
    serializer_class = PayloadListCreateSerializer

    @staticmethod
    def get_next_id():
        return PayloadListIdSequence.objects.create()

    def get_queryset(self):
        return PayloadList.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
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

        # Remove GT if provided
        data['global_tag'] = None

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        ret = serializer.data
        ret['payload_type'] = payload_type.name

        return Response(ret)


class PayloadListDetailAPIView(RetrieveAPIView):
    serializer_class = PayloadListCreateSerializer
    queryset = PayloadList.objects.all()


class PayloadTypeListCreationAPIView(ListCreateAPIView):
    # authentication_classes = ()
    # permission_classes = ()
    serializer_class = PayloadTypeSerializer

    def get_queryset(self):
        return PayloadType.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = PayloadTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data)


class PayloadIOVListCreationAPIView(ListCreateAPIView):
    #    authentication_classes = ()
    #    permission_classes = ()
    serializer_class = PayloadIOVSerializer

    def get_queryset(self):
        return PayloadIOV.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = PayloadIOVSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data

        if 'major_iov_end' not in data:
            data['major_iov_end'] = sys.maxsize
        if 'minor_iov_end' not in data:
            data['minor_iov_end'] = sys.maxsize

        data['comb_iov'] = Decimal(Decimal(data["major_iov"]) + Decimal(data["minor_iov"]) / 10 ** 19)

        if ((data['major_iov_end'] < data['major_iov']) or (
                (data['major_iov_end'] == data['major_iov']) and (data['minor_iov_end'] <= data['minor_iov']))):
            err_msg = "%s PayloadIOV ending IOVs should be greater or equal than starting." \
                      " Provided end IOVs: major_iov: %d major_iov_end: %d minor_iov: %d minor_iov_end: %d" % \
                      (data['payload_url'], data['major_iov'], data['major_iov_end'], data['minor_iov'],
                       data['minor_iov_end'])
            return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        ret = serializer.data
        return Response(ret)


class PayloadIOVDetailAPIView(RetrieveAPIView):
    serializer_class = PayloadIOVSerializer
    queryset = PayloadIOV.objects.all()


class PayloadIOVBulkCreationAPIView(CreateAPIView):
    # authentication_classes = ()
    # permission_classes = ()
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


# API to create GT. GT provided as JSON body
# class GlobalTagCreateAPIView(CreateAPIView):
#
#     serializer_class = GlobalTagCreateSerializer
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         #TODO name check
#
#         self.perform_create(serializer)
#
#         return Response(serializer.data)


class GlobalTagCloneAPIView(CreateAPIView):
    """
    GT deep copy endpoint
    """

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
        global_tag = self.get_global_tag()
        payload_lists = self.get_payload_lists(global_tag)

        global_tag.id = None
        global_tag.name = self.get_clone_name()
        global_tag.status = GlobalTagStatus.objects.get(name='unlocked')
        self.perform_create(global_tag)

        for p_list in payload_lists:
            payload_iovs = self.get_payload_iovs(p_list)
            p_list_id = self.get_next_id()
            p_list.id = p_list_id
            p_list.name = str(p_list.payload_type) + '_' + str(p_list_id)
            p_list.global_tag = global_tag
            self.perform_create(p_list)
            rp = []
            for payload in payload_iovs:
                payload.id = None
                payload.payload_list = p_list
                rp.append(payload)

            PayloadIOV.objects.bulk_create(rp)

        serializer = GlobalTagListSerializer(global_tag)

        return Response(serializer.data)


class PayloadIOVsORMMaxListAPIView(ListAPIView):
    """
    Interface to take list of PayloadIOVs grouped by PayloadLists for a given GT and IOVs
    """

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


class PayloadIOVsORMOrderByListAPIView(ListAPIView):

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


class PayloadIOVsSQLListAPIView(ListAPIView):

    def list(self, request):
        with connection.cursor() as cursor:
            cursor.execute(cdb_rest.queries.get_payload_iovs,
                           {'my_major_iov': self.request.GET.get('majorIOV'),
                            'my_minor_iov': self.request.GET.get('minorIOV'),
                            'my_gt': self.request.GET.get('gtName')})
            row = cursor.fetchall()
        return Response(row)


class PayloadIOVsRangesListAPIView(ListAPIView):
    """
    Interface to take list of PayloadIOVs ranges grouped by PayloadLists for a given GT and IOVs
    """

    def get_queryset(self):
        gt_name = self.request.GET.get('gtName')
        start_major_iov = self.request.GET.get('startMajorIOV')
        start_minor_iov = self.request.GET.get('startMinorIOV')
        end_major_iov = self.request.GET.get('endMajorIOV')
        end_minor_iov = self.request.GET.get('endMinorIOV')

        # TODO:handle endIOVs -1 -1
        q = {'major_iov__gte': start_major_iov, 'minor_iov__gte': start_minor_iov}
        if end_major_iov != '-1':
            q.update({'major_iov__lte': end_major_iov})
        if end_minor_iov != '-1':
            q.update({'minor_iov__lte': end_minor_iov})

        p_lists = PayloadList.objects.filter(global_tag__name=gt_name)
        piov_ids = []
        for pl in p_lists:
            # piovs = PayloadIOV.objects.filter(payload_list = pl, major_iov__lte = endMajorIOV,
            # minor_iov__lte=endMinorIOV, major_iov__gte = startMajorIOV,minor_iov__gte=startMinorIOV).values_list(
            # 'id', flat=True)
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


class PayloadListAttachAPIView(UpdateAPIView):
    serializer_class = PayloadListCreateSerializer

    @transaction.atomic
    def put(self, request, *args, **kwargs):

        data = request.data

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
        #if gt_status.name == 'locked':
        #    return Response({"detail": "Global Tag is locked."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check if GT is running
        # if global_tag.type_id == 'running' :
        #    return Response({"detail": "Global Tag is running."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check if the PayloadList of the same type is already attached. If yes then detach
        if (PayloadList.objects.filter(global_tag=global_tag, payload_type=pl_type) and gt_status.name == 'locked'):
            return Response({"detail": "Payload List of type %s already attached and Global Tag is locked." % pl_type}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        PayloadList.objects.filter(global_tag=global_tag, payload_type=pl_type).update(global_tag=None)
        p_list.global_tag = global_tag

        # serializer.is_valid(raise_exception=True)
        self.perform_update(p_list)

        # Update time for the GT
        self.perform_update(global_tag)

        serializer = PayloadListSerializer(p_list)
        # print(serializer.data['global_tag'])
        # json = JSONRenderer().render(serializer.data)
        ret = serializer.data
        ret['global_tag'] = global_tag.name
        ret['payload_type'] = pl_type.name

        # serializer.data['global_tag'] = gTag.name
        return Response(ret)


class PayloadIOVAttachAPIView(UpdateAPIView):
    serializer_class = PayloadIOVSerializer

    @transaction.atomic
    def put(self, request, *args, **kwargs):

        data = request.data

        try:
            p_list = PayloadList.objects.get(name=data['payload_list'])
        except KeyError:
            return Response({"detail": "PayloadList not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            piov = PayloadIOV.objects.get(id=data['piov_id'])
        except KeyError:
            return Response({"detail": "PayloadIOV not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        is_gt_locked = False
        # Check if PL is attached and GT is unlocked
        if p_list.global_tag:
            gt_status = GlobalTagStatus.objects.get(id=p_list.global_tag.status_id)
            if gt_status.name == 'locked':
                is_gt_locked = True

        list_piovs = PayloadIOV.objects.filter(payload_list=p_list)

        # Check if new PayloadIOV overlaps
        if is_gt_locked:
            # Check if Payload with same start IOVs already attached
            piovs = list_piovs.filter(major_iov=piov.major_iov, minor_iov=piov.minor_iov)
            if piovs:
                payload_url, major_iov, minor_iov, major_iov_end, minor_iov_end = \
                    piovs.values_list('payload_url', 'major_iov', 'minor_iov', 'major_iov_end', 'minor_iov_end')[0]
                # err_msg = "PayloadIOV with starting IOVs %d %d already attached: %s" % \
                # (major_iov, minor_iov, payload_url)
                err_msg = "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, " \
                          "minor_iov_end) (%d,%d,%d,%d). Conflicts with existing IOV %s (%d,%d,%d,%d)" % \
                          (piov.major_iov, piov.minor_iov, piov.major_iov_end, piov.minor_iov_end, payload_url,
                           major_iov, minor_iov, major_iov_end, minor_iov_end)
                return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Special case for Online GT - allow open IOV recover last open IOV
            special_case = False
            # if(piov.major_iov_end == sys.maxsize and piov.minor_iov_end == sys.maxsize):
            if (piov.major_iov_end == 0 or piov.major_iov_end == sys.maxsize) and piov.minor_iov_end == sys.maxsize:
                #piovs = list_piovs.all().order_by('-major_iov', '-minor_iov')
                piovs = list_piovs.all().order_by('-comb_iov')
                if piovs:
                    comb_iov, major_iov_end, minor_iov_end = piovs.values_list('comb_iov', 'major_iov_end', 'minor_iov_end')[0]
                    # if (major_iov_end == sys.maxsize and minor_iov_end == sys.maxsize):
                    if (major_iov_end == 0 or major_iov_end == sys.maxsize) and minor_iov_end == sys.maxsize:
                        #If new open-ended IOV goes after the existing last IOV
                        if comb_iov < piov.comb_iov:
                            special_case = True

                #else:
                #    special_case = True

            if not special_case:
                piovs = list_piovs.filter(Q(major_iov__lt=piov.major_iov) |
                                          Q(major_iov=piov.major_iov, minor_iov__lt=piov.minor_iov)) \
                    .order_by('-major_iov', '-minor_iov')
                if piovs:
                    payload_url, major_iov, minor_iov, major_iov_end, minor_iov_end = \
                        piovs.values_list('payload_url', 'major_iov', 'minor_iov', 'major_iov_end', 'minor_iov_end')[0]
                    if (piov.major_iov < major_iov_end) or (
                            (piov.major_iov == major_iov_end) and (piov.minor_iov < minor_iov_end)):
                        # err_msg = "%s PayloadIOV starting IOVs should be equal or greater than: %d %d. Provided
                        # start IOVs: %d %d" % \ (piov.payload_url, major_iov_end, minor_iov_end, piov.major_iov,
                        # piov.minor_iov)
                        err_msg = "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, " \
                                  "minor_iov_end) (%d,%d,%d,%d). Conflicts with existing IOV %s (%d,%d,%d,%d)" % \
                                  (piov.major_iov, piov.minor_iov, piov.major_iov_end, piov.minor_iov_end, payload_url,
                                   major_iov, minor_iov, major_iov_end, minor_iov_end)
                        return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                piovs = list_piovs.filter(Q(major_iov__gt=piov.major_iov) |
                                          Q(major_iov=piov.major_iov, minor_iov__gt=piov.minor_iov)) \
                    .order_by('major_iov', 'minor_iov')
                if piovs:
                    # major_iov, minor_iov = piovs.values_list('major_iov', 'minor_iov')[0]
                    payload_url, major_iov, minor_iov, major_iov_end, minor_iov_end = \
                        piovs.values_list('payload_url', 'major_iov', 'minor_iov', 'major_iov_end', 'minor_iov_end')[0]
                    if (piov.major_iov_end > major_iov) or (
                            (piov.major_iov_end == major_iov) and (piov.minor_iov_end > minor_iov)):
                        # err_msg = "%s PayloadIOV ending IOVs should be equal or less than: %d %d. Provided end
                        # IOVs: %d %d" % \ (piov.payload_url, major_iov, minor_iov, piov.major_iov_end,
                        # piov.minor_iov_end)
                        err_msg = "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, " \
                                  "minor_iov_end) (%d,%d,%d,%d). Conflicts with existing IOV %s (%d,%d,%d,%d)" % \
                                  (piov.major_iov, piov.minor_iov, piov.major_iov_end, piov.minor_iov_end, payload_url,
                                   major_iov, minor_iov, major_iov_end, minor_iov_end)
                        return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            # piovs fully recovered with inserted to be detached
            piovs = list_piovs.filter(
                Q(major_iov__gt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__gte=piov.minor_iov)) \
                .filter(Q(major_iov_end__lt=piov.major_iov_end) | Q(major_iov_end=piov.major_iov_end,
                                                                    minor_iov_end__lte=piov.minor_iov_end))\
                .update(payload_list=None)

            # cut the end iovs of the previous piov
            piovs = list_piovs.filter(
                Q(major_iov__lt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__lte=piov.minor_iov)).order_by(
                '-major_iov', '-minor_iov')
            if piovs:
                major_iov_end, minor_iov_end = piovs.values_list('major_iov_end', 'minor_iov_end')[0]

                if (piov.major_iov < major_iov_end) or ((piov.major_iov == major_iov_end) and (
                        (piov.minor_iov < minor_iov_end) or (minor_iov_end is None))):
                    # piovs[0].update(major_iov_end = piov.major_iov, minor_iov_end = piov.minor_iov )

                    piovs[0].major_iov_end = piov.major_iov
                    piovs[0].minor_iov_end = piov.minor_iov
                    piovs[0].save(update_fields=['major_iov_end', 'minor_iov_end'])

                # Check if the new IOV is inserted inside the old one
                if (piov.major_iov_end < major_iov_end) or (
                        (piov.major_iov_end == major_iov_end) and (piov.minor_iov_end < minor_iov_end)):
                    # Create 3rd IOV same URL as 1st A-B(inserted)-A

                    third_piov = piovs[0]
                    third_piov.major_iov = piov.major_iov_end
                    third_piov.minor_iov = piov.minor_iov_end
                    third_piov.comb_iov = Decimal(Decimal(third_piov.major_iov) + Decimal(third_piov.minor_iov) / 10 ** 19)
                    third_piov.major_iov_end = major_iov_end
                    third_piov.minor_iov_end = minor_iov_end
                    third_piov.id = None
                    third_piov.save()

                    # serializer = self.get_serializer(data=third_piov)
                    # serializer.is_valid(raise_exception=True)
                    # self.perform_create(third_piov)

            # cut the starting iovs of the next piov
            piovs = list_piovs.filter(
                Q(major_iov__gt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__gt=piov.minor_iov)).order_by(
                'major_iov', 'minor_iov')
            if piovs:
                major_iov, minor_iov = piovs.values_list('major_iov', 'minor_iov')[0]
                if (piov.major_iov_end is None) or (piov.major_iov_end > major_iov) or (
                        (piov.major_iov_end == major_iov) and (
                        (piov.minor_iov_end > minor_iov) or (piov.minor_iov_end is None))):
                    # piovs[0].update(major_iov=piov.major_iov_end, minor_iov=piov.minor_iov_end)
                    piovs[0].major_iov = piov.major_iov_end
                    piovs[0].minor_iov = piov.minor_iov_end
                    piovs[0].comb_iov = Decimal(Decimal(piovs[0].major_iov) + Decimal(piovs[0].major_iov) / 10 ** 19)
                    piovs[0].save(update_fields=['major_iov', 'minor_iov'])

        piov.payload_list = p_list
        piov.comb_iov = Decimal(Decimal(piov.major_iov) + Decimal(piov.minor_iov) / 10 ** 19)

        self.perform_update(piov)

        # Update time for the pL
        self.perform_update(p_list)

        serializer = PayloadIOVSerializer(piov)
        # print(serializer.data['global_tag'])
        # json = JSONRenderer().render(serializer.data)
        ret = serializer.data

        return Response(ret)


class GlobalTagChangeStatusAPIView(UpdateAPIView):
    serializer_class = GlobalTagCreateSerializer

    def get_global_tag(self):
        global_tag_name = self.kwargs.get('globalTagName')
        return GlobalTag.objects.get(name=global_tag_name)

    def get_gt_status(self):
        gt_status = self.kwargs.get('newStatus')
        return GlobalTagStatus.objects.get(name=gt_status)

    # @transaction.atomic
    def put(self, request, *args, **kwargs):
        try:
            gt = self.get_global_tag()
        except KeyError:
            return Response({"detail": "GlobalTag not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            gt_status = self.get_gt_status()
        except KeyError:
            return Response({"detail": "GlobalTag Status not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        gt.status = gt_status
        self.perform_update(gt)

        serializer = GlobalTagCreateSerializer(gt)

        return Response(serializer.data)

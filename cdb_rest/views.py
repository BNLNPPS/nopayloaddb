import sys

from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, ListAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
#from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny
from cdb_rest.authentication import CustomJWTAuthentication


from django.db import transaction

from django.db.models import Prefetch
from django.db.models import Q
#from django.db.models import QuerySet

from cdb_rest.models import GlobalTag, GlobalTagStatus, GlobalTagType, PayloadList, PayloadType, PayloadIOV, PayloadListIdSequence
# from todos.permissions import UserIsOwnerTodo
from cdb_rest.serializers import GlobalTagCreateSerializer, GlobalTagReadSerializer, GlobalTagStatusSerializer, GlobalTagTypeSerializer
from cdb_rest.serializers import PayloadListCreateSerializer, PayloadListReadSerializer, PayloadTypeSerializer
from cdb_rest.serializers import PayloadIOVSerializer
from cdb_rest.serializers import PayloadListSerializer
#from cdb_rest.serializers import PayloadListIdSeqSerializer

from cdb_rest.authentication import CustomJWTAuthentication

#class GlobalTagDetailAPIView(RetrieveUpdateDestroyAPIView):
class GlobalTagDetailAPIView(RetrieveAPIView):
    serializer_class = GlobalTagReadSerializer
    queryset = GlobalTag.objects.all()
    #permission_classes = (IsAuthenticated, UserIsOwnerTodo)

class GlobalTagListCreationAPIView(ListCreateAPIView):


    #authentication_classes = [CustomJWTAuthentication]
    #permission_classes = (IsAuthenticated)
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
            gtStatus = GlobalTagStatus.objects.get(name=data['status'])
            data['status']= gtStatus.pk
        except:
            return Response({"detail": "GlobalTagStatus not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            gtType = GlobalTagType.objects.get(name=data['type'])
            data['type'] = gtType.pk
        except:
            return Response({"detail": "GlobalTagType not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        ret = serializer.data
        ret['status'] = gtStatus.name
        ret['type'] = gtType.name

        return Response(ret)

class GlobalTagStatusCreationAPIView(ListCreateAPIView):

    #authentication_classes = ()
    #permission_classes = ()
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


class GlobalTagTypeCreationAPIView(ListCreateAPIView):


#    authentication_classes = ()
#    permission_classes = ()
    serializer_class = GlobalTagTypeSerializer


    def get_queryset(self):
        return GlobalTagType.objects.all()

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = GlobalTagTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data)


class PayloadListListCreationAPIView(ListCreateAPIView):
    #    authentication_classes = ()
    #    permission_classes = ()
    serializer_class = PayloadListCreateSerializer

    def get_next_id(self):
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
        id = self.get_next_id()

        data['id'] = int(id)
        data['name'] = data['payload_type'] + '_' + str(id)

        try:
            pType = PayloadType.objects.get(name=data['payload_type'])
            data['payload_type'] = pType.pk
        except:
            return Response({"detail": "PayloadType not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        #Remove GT if provided
        data['global_tag'] = None

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        ret = serializer.data
        ret['payload_type'] = pType.name

        return Response(ret)

class PayloadListDetailAPIView(RetrieveAPIView):
    serializer_class = PayloadListCreateSerializer
    queryset = PayloadList.objects.all()

class PayloadTypeListCreationAPIView(ListCreateAPIView):
    #    authentication_classes = ()
    #    permission_classes = ()
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

#        if (data['major_iov_end'] == None):
#            data['minor_iov_end'] == None
#        elif ((data['minor_iov'] == None) and (data['major_iov_end'] < data['major_iov'])):
#            data['minor_iov_end'] == None
#            err_msg = "%s PayloadIOV ending IOVs should be greater or equel than starting. Provided end IOVs: major_iov: %d major_iov_end: %d" % \
#                      (data['payload_url'], data['major_iov'], data['major_iov_end'])
#            return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#        elif((data['major_iov_end'] < data['major_iov']) or ((data['major_iov_end'] == data['major_iov']) and (data['minor_iov_end'] < data['minor_iov']))):
        if ((data['major_iov_end'] < data['major_iov']) or (
                (data['major_iov_end'] == data['major_iov']) and (data['minor_iov_end'] < data['minor_iov']))):
            err_msg = "%s PayloadIOV ending IOVs should be greater or equel than starting. Provided end IOVs: major_iov: %d major_iov_end: %d minor_iov: %d minor_iov_end: %d" % \
                      (data['payload_url'], data['major_iov'], data['major_iov_end'], data['minor_iov'], data['minor_iov_end'])
            return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            pass


        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        #pList.save()
        ret = serializer.data
        #ret['payload_list'] = pList.name
        return Response(ret)

class PayloadIOVDetailAPIView(RetrieveAPIView):
    serializer_class = PayloadIOVSerializer
    queryset = PayloadIOV.objects.all()

class PayloadIOVBulkCreationAPIView(CreateAPIView):
    #    authentication_classes = ()
    #    permission_classes = ()
    serializer_class = PayloadIOVSerializer

    def get_queryset(self):
        return PayloadIOV.objects.all()

    def create(self, request, *args, **kwargs):
        data = request.data
        batch = [PayloadIOV(id = None, payload_url = obj["payload_url"], major_iov = obj["major_iov"], minor_iov = obj["minor_iov"], major_iov_end = sys.maxsize, minor_iov_end = sys.maxsize, payload_list=PayloadList.objects.get(name=obj['payload_list']), inserted=None) for obj in data]

        PayloadIOV.objects.bulk_create(batch)

        return Response()

#API to create GT. GT provided as JSON body
#class GlobalTagCreateAPIView(CreateAPIView):
#
#    serializer_class = GlobalTagCreateSerializer
#
#    def create(self, request, *args, **kwargs):
#        serializer = self.get_serializer(data=request.data)
#        serializer.is_valid(raise_exception=True)
#
#        #TODO name check
#
#        self.perform_create(serializer)
#
#        return Response(serializer.data)


#GT deep copy endpoint

class GlobalTagCloneAPIView(CreateAPIView):

    serializer_class = GlobalTagReadSerializer

    def get_globalTag(self):
        sourceGlobalTagId = self.kwargs.get('sourceGlobalTagId')
        return GlobalTag.objects.get(pk = sourceGlobalTagId)

    def get_payloadLists(self, globalTag):
        return PayloadList.objects.filter(global_tag=globalTag)

    def get_payloadIOVs(self, payloadList):
        return PayloadIOV.objects.filter(payload_list=payloadList)

    @transaction.atomic
    def create(self, request, sourceGlobalTagId):
        globalTag = self.get_globalTag()
        payloadLists = self.get_payloadLists(globalTag)

        globalTag.id = None
        globalTag.name = 'COPY_OF_'+ globalTag.name
        self.perform_create(globalTag)

        for pList in payloadLists:
            payloadIOVs = self.get_payloadIOVs(pList)
            pList.id = None
            pList.global_tag = globalTag
            self.perform_create(pList)
            rp = []
            for payload in payloadIOVs:
                payload.id = None
                payload.payload_list = pList
                rp.append(payload)

            PayloadIOV.objects.bulk_create(rp)

        serializer = GlobalTagReadSerializer(globalTag)

        return Response(serializer.data)


#Interface to take list of PayloadIOVs groupped by PayloadLists for a given GT and IOVs
class PayloadIOVsListAPIView(ListAPIView):

        def get_queryset(self):

            gtName = self.request.GET.get('gtName')
            majorIOV = self.request.GET.get('majorIOV')
            minorIOV = self.request.GET.get('minorIOV')

            piov_querset = PayloadIOV.objects.filter(payload_list__global_tag__name=gtName).filter(
                Q(major_iov__lt=majorIOV) | Q(major_iov=majorIOV, minor_iov__lte=minorIOV)).order_by('payload_list_id',
                                                                                                     '-major_iov',
                                                                                                     '-minor_iov').distinct(
                'payload_list_id')

            return PayloadList.objects.filter(global_tag__name=gtName).prefetch_related(Prefetch(
                  'payload_iov',
                  queryset=piov_querset
                  )).filter(payload_iov__in=piov_querset).distinct()

        def list(self, request):

            queryset = self.get_queryset()
            serializer = PayloadListReadSerializer(queryset, many=True)
            return Response(serializer.data)


class PayloadIOVsList2APIView(ListAPIView):

    def get_queryset(self):
        gtName = self.request.GET.get('gtName')
        majorIOV = self.request.GET.get('majorIOV')
        minorIOV = self.request.GET.get('minorIOV')

        piov_querset = PayloadIOV.objects.filter(payload_list__global_tag__name=gtName).filter(
            Q(major_iov__lt=majorIOV) | Q(major_iov=majorIOV, minor_iov__lte=minorIOV)).order_by('payload_list_id',
                                                                                                 '-major_iov',
                                                                                                 '-minor_iov').distinct(
            'payload_list_id')

        return piov_querset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PayloadIOVSerializer(queryset, many=True)
        return Response(serializer.data)


#Interface to take list of PayloadIOVs ranges groupped by PayloadLists for a given GT and IOVs
class PayloadIOVsRangesListAPIView(ListAPIView):

        def get_queryset(self):

            gtName = self.request.GET.get('gtName')
            startMajorIOV = self.request.GET.get('startMajorIOV')
            startMinorIOV = self.request.GET.get('startMinorIOV')
            endMajorIOV = self.request.GET.get('endMajorIOV')
            endMinorIOV = self.request.GET.get('endMinorIOV')

            #TODO:handle endIOVs -1 -1
            q = {'major_iov__gte': startMajorIOV, 'minor_iov__gte': startMinorIOV}
            if endMajorIOV != '-1':
                q.update({'major_iov__lte': endMajorIOV})
            if endMinorIOV != '-1':
                q.update({'minor_iov__lte': endMinorIOV})

            #plists = PayloadList.objects.filter(global_tag__id=globalTagId)
            plists = PayloadList.objects.filter(global_tag__name=gtName)
            piov_ids = []
            for pl in plists:

                #piovs = PayloadIOV.objects.filter(payload_list = pl, major_iov__lte = endMajorIOV,minor_iov__lte=endMinorIOV,
                #                                  major_iov__gte = startMajorIOV,minor_iov__gte=startMinorIOV).values_list('id', flat=True)
                q.update({'payload_list': pl})
                piovs = PayloadIOV.objects.filter(**q).values_list('id', flat=True)

                if piovs:
                    piov_ids.extend(piovs)

            piov_querset = PayloadIOV.objects.filter(id__in=piov_ids)

            return PayloadList.objects.filter(global_tag__name=gtName).prefetch_related(Prefetch(
                  'payload_iov',
                  queryset=piov_querset
                  )).filter(payload_iov__in=piov_querset).distinct()


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
            pList = PayloadList.objects.get(name=data['payload_list'])
        except:
            return Response({"detail": "PayloadList not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            gTag = GlobalTag.objects.get(name=data['global_tag'])
        except:
            return Response({"detail": "GlobalTag not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        plType = pList.payload_type

        #check if GT is unlocked
        gtStatus = GlobalTagStatus.objects.get(id=gTag.status_id)
        if gtStatus.name == 'locked' :
            return Response({"detail": "Global Tag is locked."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        #check if GT is running
        #if gTag.type_id == 'running' :
        #    return Response({"detail": "Global Tag is running."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



        #check if the PayloadList of the same type is already attached. If yes then detach
        PayloadList.objects.filter(global_tag=gTag, payload_type=plType).update(global_tag=None)
        #gTag = GlobalTag.objects.get(name=data['global_tag'])
        pList.global_tag = gTag

        #print(serializer)
        #serializer.is_valid(raise_exception=True)
        self.perform_update(pList)

        #Update time for the GT
        self.perform_update(gTag)

        serializer = PayloadListSerializer(pList)
        #print(serializer.data['global_tag'])
        #json = JSONRenderer().render(serializer.data)
        ret = serializer.data
        ret['global_tag'] = gTag.name
        ret['payload_type'] = plType.name

        #serializer.data['global_tag'] = gTag.name
        return Response(ret)


class PayloadIOVAttachAPIView(UpdateAPIView):

    serializer_class = PayloadIOVSerializer

    @transaction.atomic
    def put(self, request, *args, **kwargs):

        data = request.data

        try:
            pList = PayloadList.objects.get(name=data['payload_list'])
        except:
            return Response({"detail": "PayloadList not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            piov = PayloadIOV.objects.get(id=data['piov_id'])
        except:
            return Response({"detail": "PayloadIOV not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        is_gt_locked = False
        # Check if PL is attached and unlocked
        if pList.global_tag:
            if pList.global_tag.status_id == 'locked':
                is_gt_locked = True


        list_piovs = PayloadIOV.objects.filter(payload_list=pList)

        #Check if new PayloadIOV overlaps
        if(is_gt_locked):

            # Check if Payload with same start IOVs already attached
            piovs = list_piovs.filter(major_iov=piov.major_iov, minor_iov=piov.minor_iov)
            if (piovs):
                payload_url, major_iov, minor_iov = piovs.values_list('payload_url', 'major_iov', 'minor_iov')[0]
                err_msg = "PayloadIOV with starting IOVs %d %d already attached: %s" % \
                          (major_iov, minor_iov, payload_url)
                return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Special case for Online GT - allow open IOV recover last open IOV
            special_case = False
            if(piov.major_iov == sys.maxsize and piov.minor_iov == sys.maxsize):
                piovs = list_piovs.all().order_by('-major_iov', '-minor_iov')
                if(piovs):
                    major_iov_end, minor_iov_end = piovs.values_list('major_iov_end','minor_iov_end')[0]
                    if (major_iov_end == sys.maxsize and minor_iov_end == sys.maxsize):
                        special_case = True

            if not special_case:
                piovs = list_piovs.filter( Q(major_iov__lt = piov.major_iov) | Q(major_iov = piov.major_iov, minor_iov__lt = piov.minor_iov) ).order_by('-major_iov', '-minor_iov')
                if(piovs):
                    major_iov_end, minor_iov_end = piovs.values_list('major_iov_end','minor_iov_end')[0]
                    if (piov.major_iov < major_iov_end) or ((piov.major_iov == major_iov_end) and (piov.minor_iov < minor_iov_end)):
                        err_msg = "%s PayloadIOV starting IOVs should be equal or greater than: %d %d. Provided start IOVs: %d %d" % \
                                              (piov.payload_url, major_iov_end, minor_iov_end, piov.major_iov, piov.minor_iov)
                        return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                piovs = list_piovs.filter( Q(major_iov__gt = piov.major_iov) | Q(major_iov = piov.major_iov, minor_iov__gt = piov.minor_iov) ).order_by('major_iov', 'minor_iov')
                if (piovs):
                    major_iov, minor_iov = piovs.values_list('major_iov', 'minor_iov')[0]
                    if (piov.major_iov_end > major_iov) or ((piov.major_iov_end == major_iov) and (piov.minor_iov_end > minor_iov)):
                        err_msg = "%s PayloadIOV ending IOVs should be equal or less than: %d %d. Provided end IOVs: %d %d" % \
                              (piov.payload_url, major_iov, minor_iov, piov.major_iov_end, piov.minor_iov_end)
                        return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:

            #piovs fully recovered with inserted to be detached
            piovs = list_piovs.filter(
                Q(major_iov__gt=piov.major_iov) | Q(major_iov=piov.major_iov, minor_iov__gte=piov.minor_iov)).filter(
                Q(major_iov_end__lt=piov.major_iov_end) | Q(major_iov_end=piov.major_iov_end, minor_iov_end__lte=piov.minor_iov_end)).update(payload_list=None)

            #cut the end iovs of the previous piov
            piovs = list_piovs.filter( Q(major_iov__lt = piov.major_iov) | Q(major_iov = piov.major_iov, minor_iov__lte = piov.minor_iov) ).order_by('-major_iov', '-minor_iov')
            if(piovs):
                major_iov_end, minor_iov_end = piovs.values_list('major_iov_end','minor_iov_end')[0]
                if (piov.major_iov < major_iov_end) or ((piov.major_iov == major_iov_end) and ((piov.minor_iov < minor_iov_end) or (minor_iov_end == None))):
                    piovs[0].update(major_iov_end = piov.major_iov, minor_iov_end = piov.minor_iov )

            # cut the starting iovs of the next piov
            piovs = list_piovs.filter( Q(major_iov__gt = piov.major_iov) | Q(major_iov = piov.major_iov, minor_iov__gt = piov.minor_iov) ).order_by('major_iov', 'minor_iov')
            if (piovs):
                major_iov, minor_iov = piovs.values_list('major_iov', 'minor_iov')[0]
                if (piov.major_iov_end == None) or (piov.major_iov_end > major_iov) or ((piov.major_iov_end == major_iov) and ((piov.minor_iov_end > minor_iov) or (piov.minor_iov_end == None))):
                    piovs[0].update(major_iov=piov.major_iov_end, minor_iov=piov.minor_iov_end)

        piov.payload_list = pList

        self.perform_update(piov)

        #Update time for the pL
        self.perform_update(pList)

        serializer = PayloadIOVSerializer(piov)
        #print(serializer.data['global_tag'])
        #json = JSONRenderer().render(serializer.data)
        ret = serializer.data

        return Response(ret)

class GlobalTagChangeStatusAPIView(UpdateAPIView):

    serializer_class = GlobalTagCreateSerializer
    def get_globalTag(self):
        globalTagName = self.kwargs.get('globalTagName')
        return GlobalTag.objects.get(name = globalTagName)

    def get_gtStatus(self):
        gtStatus = self.kwargs.get('newStatus')
        return GlobalTagStatus.objects.get(name=gtStatus)

    #@transaction.atomic
    def put(self, request, *args, **kwargs):
        try:
            gTag = self.get_globalTag()
        except:
            return Response({"detail": "GlobalTag not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            gtStatus = self.get_gtStatus()
        except:
            return Response({"detail": "GlobalTag Status not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        gTag.status = gtStatus
        self.perform_update(gTag)

        serializer = GlobalTagCreateSerializer(gTag)

        return Response(serializer.data)

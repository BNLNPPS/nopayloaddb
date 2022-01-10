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
        #pList = PayloadList.objects.values_list('id', flat=True).get(name=data['payload_list'])
        pList = PayloadList.objects.get(name=data['payload_list'])
        data['payload_list'] = pList.id

        #Check if PL is attached and unlocked
        if pList.global_tag:
            if pList.global_tag.status_id == 'locked':
                return Response({"detail": "Global Tag is locked."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        #Check if  timestamp is greater than the last one
        piovs = PayloadIOV.objects.filter(payload_list = pList)
        #print(piovs.order_by('payload_list_id','-major_iov','-minor_iov').distinct('payload_list_id').values_list('id',flat=True))
        if piovs:
            max_maj_iov, max_min_iov = piovs.order_by('-major_iov', '-minor_iov').values_list('major_iov','minor_iov')[0]
            if (data['major_iov'] < max_maj_iov) or ((data['major_iov'] == max_maj_iov) and (data['minor_iov'] <= max_min_iov)):
                err_msg = "%s PayloadIOV should be greater than: %d %d. Provided IOV: %d %d" % \
                          (data['payload_url'], max_maj_iov, max_min_iov, data['major_iov'], data['minor_iov'])
                return Response({"detail": err_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        pList.save()
        ret = serializer.data
        ret['payload_list'] = pList.name
        return Response(ret)

class PayloadIOVDetailAPIView(RetrieveAPIView):
    serializer_class = PayloadIOVSerializer
    queryset = PayloadIOV.objects.all()

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

            #return PayloadIOV.objects.filter(payload_list__global_tag__name=gtName, major_iov__lte = majorIOV,minor_iov__lte=minorIOV).order_by('payload_list_id','-major_iov','-minor_iov').distinct('payload_list_id')
            #piovs = PayloadIOV.objects.filter(payload_list__global_tag__name=gtName, major_iov__lte = majorIOV,minor_iov__lte=minorIOV).order_by('payload_list_id','-major_iov','-minor_iov').distinct('payload_list_id').values_list('id',flat=True)
            piovs = PayloadIOV.objects.filter(payload_list__global_tag__name=gtName).filter(Q(major_iov__lte=majorIOV)| Q(major_iov=majorIOV,minor_iov__lte=minorIOV)).order_by('payload_list_id', '-major_iov', '-minor_iov').distinct('payload_list_id').values_list('id', flat=True)
            piov_ids = list(piovs)
            piov_querset = PayloadIOV.objects.filter(id__in=piov_ids)

            return PayloadList.objects.filter(global_tag__name=gtName).prefetch_related(Prefetch(
                  'payload_iov',
                  queryset=piov_querset
                  )).filter(payload_iov__in=piov_querset).distinct()

        def list(self, request):

            queryset = self.get_queryset()
            serializer = PayloadListReadSerializer(queryset, many=True)
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
        try:
            plType = PayloadType.objects.get(name=data['payload_type'])
        except:
            return Response({"detail": "PayloadListType not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        #check if GT is unlocked
        if gTag.status_id == 'locked' :
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
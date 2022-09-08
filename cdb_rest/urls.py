from django.urls import path
from cdb_rest.views import GlobalTagListCreationAPIView, GlobalTagDetailAPIView, GlobalTagStatusCreationAPIView, GlobalTagTypeCreationAPIView
from cdb_rest.views import GlobalTagsListAPIView, GlobalTagsPayloadListsListAPIView, GlobalTagByNameDetailAPIView
from cdb_rest.views import PayloadListListCreationAPIView, PayloadTypeListCreationAPIView, PayloadIOVListCreationAPIView, PayloadListDetailAPIView
from cdb_rest.views import PayloadIOVsListAPIView, PayloadIOVsList2APIView, PayloadIOVsRangesListAPIView, PayloadListDetailAPIView, PayloadIOVDetailAPIView
from cdb_rest.views import PayloadListAttachAPIView, GlobalTagChangeStatusAPIView, PayloadIOVAttachAPIView
from cdb_rest.views import PayloadIOVBulkCreationAPIView

#from cdb_rest.views import GlobalTagCreateAPIView
from cdb_rest.views import GlobalTagCloneAPIView

app_name = 'cdb_rest'

urlpatterns = [
    path('gt', GlobalTagListCreationAPIView.as_view(), name="global_tag"),
    path('gt/<int:pk>', GlobalTagDetailAPIView.as_view(), name="global_tag_detail"),
    path('globalTag/<str:globalTagName>', GlobalTagByNameDetailAPIView.as_view(), name="global_tag_detail"),
    path('gtstatus', GlobalTagStatusCreationAPIView.as_view(), name="global_tag_status"),
    path('globalTags', GlobalTagsListAPIView.as_view(), name="global_tags_list"),
    path('gtPayloadLists/<str:globalTagName>', GlobalTagsPayloadListsListAPIView.as_view(), name="global_tag_payload_lists"),

    #Create GT
    #path('globalTag/<gtType>', GlobalTagCreateAPIView.as_view(), name="create_global_tag"),
    #Clone GT
    #path('globalTags/<int:sourceGlobalTagId>', GlobalTagCloneAPIView.as_view(), name="clone_global_tag"),
    path('cloneGlobalTag/<str:globalTagName>/<str:cloneName>', GlobalTagCloneAPIView.as_view(), name="clone_global_tag"),


    path('pl', PayloadListListCreationAPIView.as_view(), name="payload_list"),
    path('pl/<int:pk>', PayloadListDetailAPIView.as_view(), name="payload_list_detail"),
    path('pt', PayloadTypeListCreationAPIView.as_view(), name="payload_type"),

    path('piov', PayloadIOVListCreationAPIView.as_view(), name="payload_iov"),
    path('piov/<int:pk>', PayloadIOVDetailAPIView.as_view(), name="payload_iov_detail"),
    path('bulk_piov', PayloadIOVBulkCreationAPIView.as_view(), name="bulk_payload_iov"),

    path('pl_attach', PayloadListAttachAPIView.as_view(), name="payload_list_attach"),
    path('piov_attach', PayloadIOVAttachAPIView.as_view(), name="payload_iov_list_attach"),


    #get GT PayloadIOVs
    #payloads gtName , runNumber , expNumber
    #path('payloadiovs/<globalTagId>/<majorIOV>/<minorIOV>', PayloadIOVsListAPIView.as_view(), name="payload_list"),
    path('payloadiovs/', PayloadIOVsListAPIView.as_view(), name="payloadiovs"),
    path('payloadiovs2/', PayloadIOVsList2APIView.as_view(), name="payloadiovs2"),
    path('payloadiovsrange/', PayloadIOVsRangesListAPIView.as_view(), name="payload_ranges_list"),

    path('gt_change_status/<str:globalTagName>/<str:newStatus>', GlobalTagChangeStatusAPIView.as_view(), name="global_tag_change_status")

]

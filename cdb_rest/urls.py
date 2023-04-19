from django.urls import path
from cdb_rest.views import GlobalTagListCreationAPIView, GlobalTagDetailAPIView, GlobalTagStatusCreationAPIView
from cdb_rest.views import GlobalTagsListAPIView, GlobalTagsPayloadListsListAPIView, GlobalTagByNameDetailAPIView
from cdb_rest.views import PayloadListListCreationAPIView, PayloadTypeListCreationAPIView, PayloadIOVListCreationAPIView, PayloadListDetailAPIView
from cdb_rest.views import PayloadIOVsORMMaxListAPIView, PayloadIOVsORMOrderByListAPIView, PayloadIOVsSQLListAPIView, PayloadIOVDetailAPIView
from cdb_rest.views import PayloadListAttachAPIView, GlobalTagChangeStatusAPIView, PayloadIOVAttachAPIView
from cdb_rest.views import PayloadIOVBulkCreationAPIView
from cdb_rest.views import GlobalTagDeleteAPIView

from cdb_rest.views import GlobalTagCloneAPIView
from cdb_rest.views import TimeoutListAPIView

app_name = 'cdb_rest'

urlpatterns = [
    path('gt', GlobalTagListCreationAPIView.as_view(), name="global_tag"),
    path('gt/<int:pk>', GlobalTagDetailAPIView.as_view(), name="global_tag_detail"),
    path('globalTag/<str:globalTagName>', GlobalTagByNameDetailAPIView.as_view(), name="global_tag_detail"),
    #DELETE GT
    path('deleteGlobalTag/<str:globalTagName>', GlobalTagDeleteAPIView.as_view(), name="global_tag_delete"),

    path('gtstatus', GlobalTagStatusCreationAPIView.as_view(), name="global_tag_status"),
    path('globalTags', GlobalTagsListAPIView.as_view(), name="global_tags_list"),
    path('gtPayloadLists/<str:globalTagName>', GlobalTagsPayloadListsListAPIView.as_view(), name="global_tag_payload_lists"),

    #Clone GT
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

    path('payloadiovs_orm_orderby/', PayloadIOVsORMOrderByListAPIView.as_view(), name="payloadiovs_orm_orderby"),
    path('payloadiovs_orm_max/', PayloadIOVsORMMaxListAPIView.as_view(), name="payloadiovs_orm_max"),
    #path('payloadiovsrange/', PayloadIOVsRangesListAPIView.as_view(), name="payload_ranges_list"),
    path('payloadiovs/', PayloadIOVsSQLListAPIView.as_view(), name="payloadiovs"),
    path('timeout', TimeoutListAPIView.as_view(), name="timeout"),

    path('gt_change_status/<str:globalTagName>/<str:newStatus>', GlobalTagChangeStatusAPIView.as_view(), name="global_tag_change_status")

]

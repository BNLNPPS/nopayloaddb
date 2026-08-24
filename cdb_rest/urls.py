from django.urls import path
from cdb_rest.views import GlobalTagListCreationAPIView, GlobalTagDetailAPIView, GlobalTagStatusCreationAPIView
from cdb_rest.views import GlobalTagsListAPIView, GlobalTagsPayloadListsListAPIView, GlobalTagByNameDetailAPIView
from cdb_rest.views import PayloadListListCreationAPIView, PayloadTypeListCreationAPIView,\
    PayloadIOVListCreationAPIView, PayloadListDetailAPIView
from cdb_rest.views import PayloadIOVsORMMaxListAPIView, PayloadIOVsORMOrderByListAPIView, PayloadIOVsSQLListAPIView,\
    PayloadIOVDetailAPIView
from cdb_rest.views import PayloadListAttachAPIView, GlobalTagChangeStatusAPIView, PayloadIOVAttachAPIView
from cdb_rest.views import PayloadIOVBulkCreationAPIView
from cdb_rest.views import GlobalTagDeleteAPIView, PayloadIOVDeleteAPIView, PayloadTypeDeleteAPIView, PayloadListDeleteAPIView
from cdb_rest.views import GlobalTagCloneAPIView
from cdb_rest.views import CDBSettingAPIView
from cdb_rest.views import TimeoutListAPIView
from cdb_rest.views import cdb_web_view
from cdb_rest.views import PayloadListByNameAPIView

app_name = 'cdb_rest'

urlpatterns = [
    path('gt', GlobalTagListCreationAPIView.as_view(), name="global_tag"),
    path('gt/<int:pk>', GlobalTagDetailAPIView.as_view(), name="global_tag_detail"),
    path('globalTag/<str:globalTagName>', GlobalTagByNameDetailAPIView.as_view(), name="global_tag_detail"),
    path('deleteGlobalTag/<str:globalTagName>', GlobalTagDeleteAPIView.as_view(), name="global_tag_delete"),
    path('deletePayloadIOV/<str:globalTagName>/<str:payloadType>/<int:major_iov>/<int:minor_iov>',PayloadIOVDeleteAPIView.as_view(), name="payloadiov_delete"),
    path('deletePayloadIOV/<str:globalTagName>/<str:payloadType>/<int:major_iov>/<int:minor_iov>/<int:major_iov_end>/<int:minor_iov_end>',PayloadIOVDeleteAPIView.as_view(), name="payloadiov_delete"),
    path('deletePayloadType/<str:payloadTypeName>', PayloadTypeDeleteAPIView.as_view(), name="payload_type_delete"),
    path('deletePayloadList/<str:payloadListName>', PayloadListDeleteAPIView.as_view(), name="payload_list_delete"),
    path('gtstatus', GlobalTagStatusCreationAPIView.as_view(), name="global_tag_status"),
    path('globalTags', GlobalTagsListAPIView.as_view(), name="global_tags_list"),
    path('gtPayloadLists/<str:globalTagName>', GlobalTagsPayloadListsListAPIView.as_view(), name="global_tag_payload_lists"),
    path('cloneGlobalTag/<str:globalTagName>/<str:cloneName>', GlobalTagCloneAPIView.as_view(), name="clone_global_tag"),
    path('gt_change_status/<str:globalTagName>/<str:newStatus>', GlobalTagChangeStatusAPIView.as_view(),
         name="global_tag_change_status"),


    path('pl', PayloadListListCreationAPIView.as_view(), name="payload_list"),
    path('pl/<int:pk>', PayloadListDetailAPIView.as_view(), name="payload_list_detail"),
    path('pt', PayloadTypeListCreationAPIView.as_view(), name="payload_type"),

    path('piov', PayloadIOVListCreationAPIView.as_view(), name="payload_iov"),
    path('piov/<int:pk>', PayloadIOVDetailAPIView.as_view(), name="payload_iov_detail"),
    path('bulk_piov', PayloadIOVBulkCreationAPIView.as_view(), name="bulk_payload_iov"),

    path('pl_attach', PayloadListAttachAPIView.as_view(), name="payload_list_attach"),
    path('piov_attach', PayloadIOVAttachAPIView.as_view(), name="payload_iov_list_attach"),

    #path('payloadiovs_orm_orderby/', PayloadIOVsORMOrderByListAPIView.as_view(), name="payloadiovs_orm_orderby"),
    #path('payloadiovs_orm_max/', PayloadIOVsORMMaxListAPIView.as_view(), name="payloadiovs_orm_max"),
    # path('payloadiovsrange/', PayloadIOVsRangesListAPIView.as_view(), name="payload_ranges_list"),
    path('payloadiovs/', PayloadIOVsSQLListAPIView.as_view(), name="payloadiovs"),
    path('user_settings/<str:name>/', CDBSettingAPIView.as_view()),
    path('timeout', TimeoutListAPIView.as_view(), name="timeout"),
    path('web/', cdb_web_view, name="cdb_web"),

    # Readable aliases (same views, human-friendly URLs)
    path('global-tags', GlobalTagsListAPIView.as_view(), name="global_tags_list_alias"),
    path('global-tags/statuses', GlobalTagStatusCreationAPIView.as_view(), name="global_tag_status_alias"),
    path('global-tags/<str:globalTagName>', GlobalTagByNameDetailAPIView.as_view(), name="global_tag_by_name_alias"),
    path('global-tags/<str:globalTagName>/payload-lists', GlobalTagsPayloadListsListAPIView.as_view(), name="gt_payload_lists_alias"),
    path('global-tags/<str:globalTagName>/clone/<str:cloneName>', GlobalTagCloneAPIView.as_view(), name="clone_global_tag_alias"),
    path('global-tags/<str:globalTagName>/change-status/<str:newStatus>', GlobalTagChangeStatusAPIView.as_view(), name="gt_change_status_alias"),
    path('global-tags/<str:globalTagName>/delete', GlobalTagDeleteAPIView.as_view(), name="global_tag_delete_alias"),
    path('payload-types', PayloadTypeListCreationAPIView.as_view(), name="payload_types_alias"),
    path('payload-types/<str:payloadTypeName>/delete', PayloadTypeDeleteAPIView.as_view(), name="payload_type_delete_alias"),
    path('payload-lists', PayloadListListCreationAPIView.as_view(), name="payload_lists_alias"),
    path('payload-lists/<int:pk>', PayloadListDetailAPIView.as_view(), name="payload_list_detail_alias"),
    path('payload-lists/by-name/<str:payloadListName>', PayloadListByNameAPIView.as_view(), name="payload_list_by_name"),
    path('payload-lists/attach', PayloadListAttachAPIView.as_view(), name="payload_list_attach_alias"),
    path('payload-lists/<str:payloadListName>/delete', PayloadListDeleteAPIView.as_view(), name="payload_list_delete_alias"),
    path('payload-iovs', PayloadIOVListCreationAPIView.as_view(), name="payload_iovs_alias"),
    path('payload-iovs/<int:pk>', PayloadIOVDetailAPIView.as_view(), name="payload_iov_detail_alias"),
    path('payload-iovs/bulk', PayloadIOVBulkCreationAPIView.as_view(), name="bulk_payload_iov_alias"),
    path('payload-iovs/attach', PayloadIOVAttachAPIView.as_view(), name="payload_iov_attach_alias"),
    path('payload-iovs/query/', PayloadIOVsSQLListAPIView.as_view(), name="payloadiovs_alias"),
    path('payload-iovs/<str:globalTagName>/<str:payloadType>/<int:major_iov>/<int:minor_iov>/delete', PayloadIOVDeleteAPIView.as_view(), name="payloadiov_delete_alias"),
    path('payload-iovs/<str:globalTagName>/<str:payloadType>/<int:major_iov>/<int:minor_iov>/<int:major_iov_end>/<int:minor_iov_end>/delete', PayloadIOVDeleteAPIView.as_view(), name="payloadiov_delete_range_alias"),
    path('settings/<str:name>/', CDBSettingAPIView.as_view(), name="settings_alias"),
]

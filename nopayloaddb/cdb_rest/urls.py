from django.urls import path
from cdb_rest.views import GlobalTagListCreationAPIView, GlobalTagDetailAPIView, GlobalTagStatusCreationAPIView, GlobalTagTypeCreationAPIView
from cdb_rest.views import PayloadListListCreationAPIView, PayloadTypeListCreationAPIView, PayloadIOVListCreationAPIView
from cdb_rest.views import PayloadIOVsListAPIView, PayloadIOVsRangesListAPIView


from cdb_rest.views import GlobalTagCreateAPIView, GlobalTagCloneAPIView

app_name = 'cdb_rest'

urlpatterns = [
    path('gt', GlobalTagListCreationAPIView.as_view(), name="global_tag"),
    path('gt/<int:pk>', GlobalTagDetailAPIView.as_view(), name="global_tag_detail"),
    path('gtstatus', GlobalTagStatusCreationAPIView.as_view(), name="global_tag_status"),
    path('gttype', GlobalTagTypeCreationAPIView.as_view(), name="global_tag_type"),

    #Create GT
    path('globalTag/<gtType>', GlobalTagCreateAPIView.as_view(), name="create_global_tag"),
    #Clone GT
    path('globalTags/<int:sourceGlobalTagId>', GlobalTagCloneAPIView.as_view(), name="clone_global_tag"),


    path('pl', PayloadListListCreationAPIView.as_view(), name="payload_list"),
    path('pt', PayloadTypeListCreationAPIView.as_view(), name="payload_type"),

    path('piov', PayloadIOVListCreationAPIView.as_view(), name="payload_iov"),

    #get GT PayloadIOVs
    #payloads gtName , runNumber , expNumber
    #path('payloadiovs/<globalTagId>/<majorIOV>/<minorIOV>', PayloadIOVsListAPIView.as_view(), name="payload_list"),
    path('payloadiovs/', PayloadIOVsListAPIView.as_view(), name="payload_list"),
    path('payloadiovsrange/', PayloadIOVsRangesListAPIView.as_view(), name="payload_ranges_list")

]

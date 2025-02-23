from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_consultation import DailyRoundSerializer, PatientConsultationSerializer
from care.facility.models.patient_consultation import DailyRound, PatientConsultation
from care.facility.models.patient import PatientRegistration
from care.users.models import User


class PatientConsultationFilter(filters.FilterSet):
    patient = filters.CharFilter(field_name="patient__external_id")
    facility = filters.NumberFilter(field_name="facility_id")


class PatientConsultationViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    lookup_field = "external_id"
    serializer_class = PatientConsultationSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = PatientConsultation.objects.all().select_related("facility").order_by("-id")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientConsultationFilter

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(patient__facility__state=self.request.user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(patient__facility__district=self.request.user.district)
        filters = Q(patient__facility__users__id__exact=self.request.user.id)
        filters |= Q(assigned_to=self.request.user)
        return self.queryset.filter(filters).distinct("id")

    def list(self, request, *args, **kwargs):
        """
        Consultation List

        Supported filters
        - `facility` - ID
        - `patient` - ID
        """
        return super().list(request, *args, **kwargs)


class DailyRoundsViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    serializer_class = DailyRoundSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = DailyRound.objects.all().order_by("-id")

    def get_queryset(self):
        queryset = self.queryset.filter(consultation__external_id=self.kwargs["consultation_external_id"])
        return queryset

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            kwargs["data"]["consultation"] = PatientConsultation.objects.get(
                external_id=self.kwargs["consultation_external_id"]
            ).id
        return super().get_serializer(*args, **kwargs)

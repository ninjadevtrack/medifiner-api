from rest_framework import status
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_registration.exceptions import BadRequest
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.gis.geos import Point
from django.db.models import Prefetch, Sum, Count, Q
from django.db.models.functions import Coalesce
from django.core.mail import send_mail
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _


from epidemic.models import Epidemic
from medications.models import (
    MedicationType,
    MedicationTypeMedicationNameThrough,
    MedicationMedicationNameMedicationDosageThrough,
    ProviderMedicationNdcThrough,
    Provider,
    Medication,
)

from medications.views import (
    medication_name_dosage_type_filters,
)

from .serializers import FindProviderSerializer, ContactFormSerializer


class FindProviderMedicationView(ListAPIView):
    serializer_class = FindProviderSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        query_params:
            - med_ids: list of MedicaitonName ids
            - dosages: list of Dosage ids
            - localization: list of 2 coordinates (must be int or float)
            - distance: int, in miles
        '''
        med_ids = self.request.query_params.getlist('med_ids[]', None)
        dosages = self.request.query_params.getlist('dosages[]', None)
        location = self.request.query_params.get('localization')
        distance = self.request.query_params.get('distance')

        # 1 - validate location
        try:
            location = list(
                map(float, location.split(','))
            )
            location_point = Point(
                location[0], location[1], srid=4326,
            )
        except (IndexError, ValueError, AttributeError):
            raise BadRequest(
                'Location should be provided and be a list of 2 coordinates'
            )

        # 2 - fetch ndc codes from filters: med id and dosage + support for all
        if len(med_ids) == 1 and med_ids[0] == 'all':
            med_ndc_qs = MedicationMedicationNameMedicationDosageThrough.objects.all()
        else:
            med_ndc_qs = MedicationMedicationNameMedicationDosageThrough.objects.filter(
                medication_name_id__in=med_ids,
                medication_dosage_id__in=dosages
            )
        med_ndc_ids = med_ndc_qs.select_related(
            'medication__ndc_codes',
        ).distinct().values_list('medication__ndc_codes', flat=True)

        # 2 - fetch provider medication entries (supply levels) for the ndc ndc_codes
        # and filter by distance
        provider_medication_ids = ProviderMedicationNdcThrough.objects.filter(
            latest=True,
            medication_ndc_id__in=med_ndc_ids,
            provider__geo_localization__distance_lte=(
                location_point,
                D(mi=distance),
            ),
        ).values_list('id', flat=True,)

        # SPECIAL INSTRUCTION
        # Exclude providers from vaccine finder organization ID 4504 (4383 in medfinder)
        # vaccine finder type needs to be 4 (pharamacy), exclude all other
        # More info at https://www.pivotaltracker.com/story/show/162711148

        provider_qs = Provider.objects.filter(
            Q(organization_id=4383) | Q(vaccine_finder_type=4)
        ).filter(
            geo_localization__distance_lte=(
                location_point,
                D(mi=distance),
            ),
        ).annotate(
            distance=Distance(
                'geo_localization',
                location_point,
            ),
            total_supply=Coalesce(
                Sum(
                    'provider_medication__level',
                    filter=Q(
                        provider_medication__id__in=provider_medication_ids,
                        provider_medication__latest=True,
                        active=True,
                    ),
                ),
                0,
            ),
            amount_medications=Count(
                'provider_medication',
                filter=Q(
                    provider_medication__id__in=provider_medication_ids,
                    provider_medication__latest=True,
                    active=True,
                ),
            )
        ).prefetch_related(
            Prefetch(
                'provider_medication',
                queryset=ProviderMedicationNdcThrough.objects.filter(
                    latest=True,
                    id__in=provider_medication_ids,
                ).select_related(
                    'medication_ndc__medication',
                    'medication_ndc__medication__medication_name',
                ).order_by('-level', '-medication_ndc__medication__drug_type')
            )
        ).order_by('-total_supply', '-active', '-amount_medications', 'distance')

        return provider_qs


class BasicInfoView(APIView):

    def get(self, request):
        # Making a bigger response in case more objects are added in the future
        response = {}
        map_choices = dict(Medication.DRUG_TYPE_CHOICES)
        if not Epidemic.objects.first().active:
            map_choices.pop(Medication.PUBLIC_HEALTH_SUPPLY)
        response['drug_type'] = map_choices
        return Response(response)


class GetFormOptionsView(APIView):
    def get(self, request):
        options = medication_name_dosage_type_filters()
        medication_types = MedicationType.objects.order_by(
            'name').values('id', 'name')

        response = {
            'medication_types': medication_types,
            'options': options
        }
        return Response(response)


class ContactFormView(GenericAPIView):
    serializer_class = ContactFormSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            validated_data = serializer.validated_data
            email_to = 'medfinder@healthmap.org'
            from_email = validated_data.get('email')
            context = {
                'representative_name': validated_data.get(
                    'representative_name'
                ),
                'pharmacy_name': validated_data.get('pharmacy_name'),
                'pharmacy_address': validated_data.get('pharmacy_address'),
                'additional_comments': validated_data.get(
                    'additional_comments'
                ),
                'email': from_email,
            }
            # TODO: Template to be completed by front end
            msg_html = render_to_string(
                'public/emails/contact_email.html',
                context=context,
            )
            msg_plain = render_to_string(
                'public/emails/contact_email.txt',
                context=context,
            )

            send_mail(
                'MedFinder: New Interested Pharmacy',
                msg_plain,
                from_email,
                [email_to],
                html_message=msg_html,
            )
            return Response(
                _('Successfully sent email'),
                status=status.HTTP_200_OK,
            )
        return Response(
            _('There are errors in the dara provided'),
            status=status.HTTP_400_BAD_REQUEST,
        )

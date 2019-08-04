from datetime import time
from time import strftime, strptime

from django import forms
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.forms.widgets import Media, TextInput
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

import pytz
import recurrence

from .models.events import (
    CommonEvent,
    Event,
    EventComment,
    EventPhoto,
    EventSeries,
    Place,
)
from .models.locale import SPR, City, Country
from .models.profiles import OrgTeamRequest, Sponsor, Team, UserProfile
from .models.speakers import Presentation, Speaker, SpeakerRequest, Talk


class Lookup(TextInput):
    input_type = "text"
    template_name = "forms/widgets/lookup.html"
    add_id_index = False
    checked_attribute = {"selected": True}
    option_inherits_attrs = False

    def __init__(self, source, key="id", label="__str__", attrs=None):
        super().__init__(attrs)
        self.source = source
        self.key = key
        self.label = label

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context

    def format_value(self, value):
        if value is not None:
            lookup_query = {self.key: value}
            lookup_object = self.source.objects.get(**lookup_query)
            lookup_field = getattr(lookup_object, self.label)
            if callable(lookup_field):
                lookup_value = lookup_field()
            else:
                lookup_value = lookup_field
            return mark_safe('<option value="%s">%s</option>' % (value, lookup_value))
        else:
            return mark_safe('<option value="">--------</option>')


class DateWidget(forms.DateInput):
    """A more-friendly date widget with a p% if widget.value != None %} value="{{ widget.value|stringformat:'s' }}"{% endif %op-up calendar.
    """

    template_name = "forms/widgets/date.html"

    def __init__(self, attrs=None):
        self.date_class = "datepicker"
        if not attrs:
            attrs = {}
        if "date_class" in attrs:
            self.date_class = attrs.pop("date_class")
        if "class" not in attrs:
            attrs["class"] = "date"

        super(DateWidget, self).__init__(attrs=attrs)


class SimpleTimeWidget(forms.Select):
    """A single dropdown time widget
    """

    def __init__(self, attrs=None):
        self.time_class = "timepicker"
        if not attrs:
            attrs = {}
        if "time_class" in attrs:
            self.time_class = attrs.pop("time_class")
        if "class" not in attrs:
            attrs["class"] = "time"

        choices = []
        for m in ("AM", "PM"):
            for hour in range(0, 12):
                if hour == 0:
                    hour = 12
                for minute in range(00, 60, 30):
                    choices.append(
                        (
                            "%02d:%02d %s" % (hour, minute, m),
                            ("%02d:%02d %s" % (hour, minute, m)),
                        )
                    )

        super(SimpleTimeWidget, self).__init__(attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = super(SimpleTimeWidget, self).value_from_datadict(data, files, name)
        t = strptime(value, "%I:%M %p")
        return strftime("%H:%M:%S", t)


class TimeWidget(forms.MultiWidget):
    """A more-friendly time widget.
    """

    def __init__(self, attrs=None):
        self.time_class = "timepicker"
        if not attrs:
            attrs = {}
        if "time_class" in attrs:
            self.time_class = attrs.pop("time_class")
        if "class" not in attrs:
            attrs["class"] = "time"

        widgets = (
            forms.Select(
                attrs=attrs, choices=[(i + 1, "%02d" % (i + 1)) for i in range(0, 12)]
            ),
            forms.Select(
                attrs=attrs, choices=[(i, "%02d" % i) for i in range(00, 60, 15)]
            ),
            forms.Select(attrs=attrs, choices=[("AM", _("AM")), ("PM", _("PM"))]),
        )

        super(TimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if isinstance(value, str):
            try:
                value = strptime(value, "%I:%M %p")
            except:
                value = strptime(value, "%H:%M:%S")
            hour = int(value.tm_hour)
            minute = int(value.tm_min)
            if hour < 12:
                meridian = "AM"
            else:
                meridian = "PM"
                hour -= 12
            return (hour, minute, meridian)
        elif isinstance(value, time):
            hour = int(value.strftime("%I"))
            minute = int(value.strftime("%M"))
            meridian = value.strftime("%p")
            return (hour, minute, meridian)
        return (None, None, None)

    def value_from_datadict(self, data, files, name):
        value = super(TimeWidget, self).value_from_datadict(data, files, name)
        t = strptime(
            "%02d:%02d %s" % (int(value[0]), int(value[1]), value[2]), "%I:%M %p"
        )
        return strftime("%H:%M:%S", t)

    def format_output(self, rendered_widgets):
        return '<span class="%s">%s%s%s</span>' % (
            self.time_class,
            rendered_widgets[0],
            rendered_widgets[1],
            rendered_widgets[2],
        )


class DateTimeWidget(forms.SplitDateTimeWidget):
    """
    A more-friendly date/time widget.
    """

    def __init__(self, attrs=None, date_format=None, time_format=None):
        super(DateTimeWidget, self).__init__(attrs, date_format, time_format)
        self.widgets = (DateWidget(attrs=attrs), SimpleTimeWidget(attrs=attrs))

    def decompress(self, value):
        if value:
            d = strftime("%Y-%m-%d", value.timetuple())
            t = strftime("%I:%M %p", value.timetuple())
            return (d, t)
        else:
            return (None, None)

    def format_output(self, rendered_widgets):
        return "%s %s" % (rendered_widgets[0], rendered_widgets[1])

    def value_from_datadict(self, data, files, name):
        values = super(DateTimeWidget, self).value_from_datadict(data, files, name)
        return " ".join(values)


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            "name",
            "access",
            "description",
            "about_page",
            "category",
            "city",
            "web_url",
            "tz",
            "cover_img",
        ]
        widgets = {"city": Lookup(source=City)}
        raw_id_fields = "city"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].required = True
        self.fields["access"].choices = [(0, "Public"), (2, "Private")]


class NewTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "city", "tz", "cover_img", "access"]
        widgets = {"city": Lookup(source=City)}
        raw_id_fields = "city"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].required = True
        self.fields["access"].choices = [(0, "Public"), (2, "Private")]


class TeamDefinitionForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["category", "web_url", "description", "about_page"]


class DeleteTeamForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, delete team"), required=True)


class TeamContactForm(forms.Form):
    to = forms.ChoiceField(label="")
    body = forms.CharField(label="", widget=forms.widgets.Textarea)


class MultiEmailField(forms.Field):
    def to_python(self, value):
        """Normalize data to a list of strings."""
        # Return an empty list if no input was given.
        if not value:
            return []
        return [email.strip() for email in value.split(",")]

    def validate(self, value):
        """Check if value consists only of valid emails."""
        # Use the parent's handling of required fields, etc.
        super().validate(value)
        for email in value:
            validate_email(email)


class TeamInviteForm(forms.Form):
    to = MultiEmailField(label="", widget=forms.widgets.Textarea)


class TeamEventForm(forms.ModelForm):
    # Translators: Repeating/recurring events
    recurrences = recurrence.forms.RecurrenceField(label=_("Repeat"), required=False)

    class Meta:
        model = Event
        fields = [
            "name",
            "start_time",
            "end_time",
            "recurrences",
            "summary",
            "web_url",
            "announce_url",
            "attendee_limit",
            "enable_comments",
            "enable_photos",
            "enable_presentations",
        ]
        widgets = {
            "place": Lookup(source=Place),
            "start_time": DateTimeWidget,
            "end_time": DateTimeWidget,
        }

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        event_tz = pytz.timezone(self.instance.tz)
        if self.instance.local_start_time:
            self.initial["start_time"] = self.instance.local_start_time
        if self.instance.local_end_time:
            self.initial["end_time"] = self.instance.local_end_time

    def clean(self):
        cleaned_data = super().clean()
        event_tz = pytz.timezone(self.instance.tz)
        cleaned_data["start_time"] = pytz.utc.localize(
            timezone.make_naive(
                event_tz.localize(timezone.make_naive(cleaned_data["start_time"]))
            )
        )
        cleaned_data["end_time"] = pytz.utc.localize(
            timezone.make_naive(
                event_tz.localize(timezone.make_naive(cleaned_data["end_time"]))
            )
        )
        return cleaned_data


class NewTeamEventForm(forms.ModelForm):
    recurrences = recurrence.forms.RecurrenceField(label=_("Repeat"), required=False)

    class Meta:
        model = Event
        fields = ["name", "start_time", "end_time", "recurrences", "summary"]
        widgets = {"start_time": DateTimeWidget, "end_time": DateTimeWidget}

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        event_tz = pytz.timezone(self.instance.tz)
        if self.instance.local_start_time:
            self.initial["start_time"] = self.instance.local_start_time
        if self.instance.local_end_time:
            self.initial["end_time"] = self.instance.local_end_time

    def clean(self):
        cleaned_data = super().clean()
        event_tz = pytz.timezone(self.instance.tz)
        cleaned_data["start_time"] = pytz.utc.localize(
            timezone.make_naive(
                event_tz.localize(timezone.make_naive(cleaned_data["start_time"]))
            )
        )
        cleaned_data["end_time"] = pytz.utc.localize(
            timezone.make_naive(
                event_tz.localize(timezone.make_naive(cleaned_data["end_time"]))
            )
        )
        return cleaned_data


class NewEventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "start_time", "end_time"]
        widgets = {"start_time": DateTimeWidget, "end_time": DateTimeWidget}

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        event_tz = pytz.timezone(self.instance.tz)
        if self.instance.local_start_time:
            self.initial["start_time"] = self.instance.local_start_time
        if self.instance.local_end_time:
            self.initial["end_time"] = self.instance.local_end_time

    def clean(self):
        cleaned_data = super().clean()
        event_tz = pytz.timezone(self.instance.tz)
        cleaned_data["start_time"] = pytz.utc.localize(
            timezone.make_naive(
                event_tz.localize(timezone.make_naive(cleaned_data["start_time"]))
            )
        )
        cleaned_data["end_time"] = pytz.utc.localize(
            timezone.make_naive(
                event_tz.localize(timezone.make_naive(cleaned_data["end_time"]))
            )
        )
        return cleaned_data


class NewEventDetailsForm(forms.ModelForm):
    recurrences = recurrence.forms.RecurrenceField(label=_("Repeat"), required=False)

    class Meta:
        model = Event
        fields = [
            "summary",
            "recurrences",
            "web_url",
            "announce_url",
            "attendee_limit",
            "enable_comments",
            "enable_photos",
            "enable_presentations",
        ]


class EventSettingsForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "attendee_limit",
            "enable_comments",
            "enable_photos",
            "enable_presentations",
        ]


class DeleteEventForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, delete event"), required=True)


class CancelEventForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, cancel this event"), required=True)
    reason = forms.CharField(
        label=_("Reason for cancellation"), widget=forms.widgets.Textarea
    )


class ChangeEventHostForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["team"]


class EventInviteMemberForm(forms.Form):
    member = forms.ChoiceField(label="")


class EventInviteEmailForm(forms.Form):
    emails = MultiEmailField(label="", widget=forms.widgets.Textarea)


class EventContactForm(forms.Form):
    to = forms.ChoiceField(label="")
    body = forms.CharField(label="", widget=forms.widgets.Textarea)


class EventSeriesForm(forms.ModelForm):
    class Meta:
        model = EventSeries
        fields = [
            "name",
            "start_time",
            "end_time",
            "recurrences",
            "summary",
            "attendee_limit",
        ]
        widgets = {"start_time": TimeWidget, "end_time": TimeWidget}


class DeleteEventSeriesForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, delete series"), required=True)


class UploadEventPhotoForm(forms.ModelForm):
    class Meta:
        model = EventPhoto
        fields = ["src", "title", "caption"]


class RemoveEventPhotoForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, remove photo"), required=True)


class EventCommentForm(forms.ModelForm):
    class Meta:
        model = EventComment
        fields = ["body"]


class DeleteCommentForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, delete comment"), required=True)


class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ["name", "web_url", "logo"]


class NewPlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ["name", "address", "city", "longitude", "latitude", "place_url", "tz"]
        widgets = {"city": Lookup(source=City)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].required = True


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "realname",
            "web_url",
            "city",
            "tz",
            "avatar",
            "send_notifications",
            "do_not_track",
        ]
        labels = {
            "send_notifications": _("Send me notification emails"),
            "do_not_track": _("Do not track"),
        }
        widgets = {"city": Lookup(source=City)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].required = True


class ConfirmProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["avatar", "realname", "city"]
        widgets = {"city": Lookup(source=City)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].required = True


class SendNotificationsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["send_notifications"]
        labels = {"send_notifications": _("Send me notification emails")}


class SearchForm(forms.Form):
    city = forms.IntegerField(required=False, widget=Lookup(source=City, label="name"))
    distance = forms.IntegerField(label=_("Distance(km)"), required=True)

    class Meta:
        widgets = {"city": Lookup(source=City, label="name")}


class SearchTeamsByName(forms.Form):
    name = forms.CharField(label=_("Name"), required=False)
    city = forms.IntegerField(required=False, widget=Lookup(source=City, label="name"))
    distance = forms.IntegerField(label=_("Distance(km)"), required=True)

    class Meta:
        widgets = {"city": Lookup(source=City, label="name")}


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "description", "cover_img"]


class OrgContactForm(forms.Form):
    to = forms.ChoiceField(label="")
    body = forms.CharField(label="", widget=forms.widgets.Textarea)


class RequestToJoinOrgForm(forms.ModelForm):
    class Meta:
        model = OrgTeamRequest
        fields = ["team"]


class AcceptRequestToJoinOrgForm(forms.Form):
    confirm = forms.BooleanField(
        label=_("Yes, add this team to my organization"), required=True
    )


class InviteToJoinOrgForm(forms.ModelForm):
    class Meta:
        model = OrgTeamRequest
        fields = ["organization"]


class AcceptInviteToJoinOrgForm(forms.Form):
    confirm = forms.BooleanField(
        label=_("Yes, add my team to this organization"), required=True
    )


class AcceptInviteToJoinTeamForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, add me to this team"), required=True)


class AcceptRequestToJoinTeamForm(forms.Form):
    confirm = forms.BooleanField(
        label=_("Yes, add this person to my team"), required=True
    )


class CommonEventForm(forms.ModelForm):
    class Meta:
        model = CommonEvent
        fields = [
            "name",
            "start_time",
            "end_time",
            "summary",
            "continent",
            "country",
            "spr",
            "city",
            "place",
            "web_url",
            "announce_url",
        ]
        widgets = {
            "country": Lookup(source=Country, label="name"),
            "spr": Lookup(source=SPR, label="name"),
            "city": Lookup(source=City, label="name"),
            "place": Lookup(source=Place, label="name"),
            "start_time": DateTimeWidget,
            "end_time": DateTimeWidget,
        }


class SpeakerBioForm(forms.ModelForm):
    class Meta:
        model = Speaker
        fields = ["avatar", "title", "bio", "categories"]


class DeleteSpeakerForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, delete series"), required=True)


class UserTalkForm(forms.ModelForm):
    class Meta:
        model = Talk
        fields = ["speaker", "title", "abstract", "talk_type", "web_url", "category"]


class DeleteTalkForm(forms.Form):
    confirm = forms.BooleanField(label=_("Yes, delete series"), required=True)


class SchedulePresentationForm(forms.ModelForm):
    class Meta:
        model = Presentation
        fields = ["start_time"]

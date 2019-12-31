from django import forms


class MapForm(forms.Form):
    origin_lat = forms.FloatField(
        label="緯度(Latitude)",
        max_value=90,
        min_value=0
        )
    origin_lon = forms.FloatField(
        label="経度(longitude)",
        max_value=180,
        min_value=0
        )
    dest_lat = forms.FloatField(
        label="緯度(Latitude)",
        max_value=90,
        min_value=0
        )
    dest_lon = forms.FloatField(
        label="経度(longitude)",
        max_value=180,
        min_value=0
        )

    date = forms.DateField(
        label="日付",
        required=True,
        widget=forms.DateInput(attrs={"type":"date"}),
        input_formats=["%Y-%m-%d"]
        )

    time = forms.TimeField(
        label="時刻",
        required=True,
        widget=forms.TimeInput(attrs={"type":"time"}),
        input_formats=["%H:%M"]
        )

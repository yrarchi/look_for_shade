from .sunlight import *


def sunlight(date, time, origin_lat, origin_lon, dest_lat, dest_lon):
    obj = CalcSolarPositon(date, time, origin_lat, origin_lon)
    h = obj.calc_solar_altitude()
    A = obj.calc_solar_azimuth()

    if h > 0:
        obj = CalcPerInsolation(h, A)
        per_insolation_df = obj.calc_per_insolation()

        obj = CalcJvPerStreetAzimuth(date, h, A)
        Jv_df = obj.calc_Jv_per_street_azimuth()

        obj = CalcWarmRoute(Jv_df, per_insolation_df, origin_lat, origin_lon, dest_lat, dest_lon)
        obj.plot_warm_route()
        result = "map"
    else:
        result = "日が沈んでいるので、どこを歩いても同じです"
    return result

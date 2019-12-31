import folium
import networkx as nx
import osmnx as ox
import pandas as pd
import pickle
import datetime
import math


class CalcSolarPositon:
    """太陽高度と方位角を求める
    """

    def __init__(self, date, time, lat, lon):
        self.date = date
        self.time = time
        self.lat = lat
        self.lon = lon


    def calc_sin_cos(self):
        """後の計算で使うsin, cosの値を求めておく
        """
        jan_1 = datetime.date(self.date.year,1,1)
        days = (self.date - jan_1).days

        theta = 2 * math.pi * (days + 0.5) / 365
        sin = []
        cos = []
        for no in range(1, 4):
            sin.append(math.sin((theta * no)))
            cos.append(math.cos((theta * no)))
        return sin, cos


    def calc_declination(self):
        """太陽赤緯 declination(°)を計算する
        """
        sin, cos = self.calc_sin_cos()
        declination = 0.33281 - 22.984 * cos[0] - 0.34990 * cos[1] - 0.13980 * cos[2] + 3.7872 * sin[0] + 0.03250 * sin[1] + 0.07187 * sin[2]
        return declination


    def calc_hour_angle(self):
        """時角 t(°)を計算する
        """
        sin, cos = self.calc_sin_cos()
        e = 0.0072 * cos[0] - 0.0528 * cos[1] - 0.0012 * cos[2] - 0.1229 * sin[0] - 0.1565 * sin[1] - 0.0041 * sin[2]
        t = (self.time.hour + self.time.minute/60 + (self.lon - 135) / 15 + e) * 15 - 180
        return t


    def calc_rad(self):
        """後の計算で使うためにradianに変換しておく
        """
        declination = self.calc_declination()
        t = self.calc_hour_angle()
        lat_rad = math.radians(self.lat)
        declination_rad = math.radians(declination)
        t_rad = math.radians(t)
        return lat_rad, declination_rad, t_rad


    def calc_solar_altitude(self):
        """太陽高度 h(rad)を計算する
        """
        lat_rad, declination_rad, t_rad = self.calc_rad()
        sinh = math.sin(lat_rad) * math.sin(declination_rad) + math.cos(lat_rad) * math.cos(declination_rad) * math.cos(t_rad)
        h = math.asin(sinh)
        return h


    def calc_solar_azimuth(self):
        """方位角 A(rad)を計算する
        """
        lat_rad, declination_rad, t_rad = self.calc_rad()
        h = self.calc_solar_altitude()

        sinA = math.cos(declination_rad) * math.sin(t_rad) / math.cos(h)
        cosA = (math.sin(h) * math.sin(lat_rad) - math.sin(declination_rad)) / math.cos(h) / math.cos(lat_rad)
        A = math.atan2(sinA, cosA) + math.pi
        return A


class CalcPerInsolation:
    """道路の方位角ごとに、直達日射を浴びる体の表面積の割合を計算する
    """

    spacing_from_bldg = 3000
    bldg_h = 6000
    person_h = 1700


    def __init__(self, h, A):
        self.h = h
        self.A = A


    def calc_coordinate_of_shade(self):
        """影の落ちる位置の座標を計算する
        """
        shade_longth = self.bldg_h / math.tan(self.h)
        shade_x = shade_longth * math.sin(self.A) * -1
        shade_y = shade_longth * math.cos(self.A) * -1
        return shade_x, shade_y


    def calc_vertical_distance_from_bldg_to_shade(self):
        """建物から影までの垂線の長さを計算する
        """
        shade_x, shade_y = self.calc_coordinate_of_shade()
        vertical_distance_from_bldg_list = []
        street_azimuth_list = []
        distance_shade_top_view = (shade_x **2 + shade_y **2) **0.5

        A = self.A if self.A > math.pi else self.A - math.pi
        for street_azimuth in [math.pi / 180 * i for i in range(180)]:
            distance = distance_shade_top_view * math.cos(abs(A - street_azimuth) - math.pi/2)
            vertical_distance_from_bldg_list.append(distance)
            street_azimuth_list.append(street_azimuth)

        df_vertical_distance_from_bldg = pd.DataFrame(vertical_distance_from_bldg_list, index=street_azimuth_list)
        return df_vertical_distance_from_bldg


    def calc_per_insolation(self):
        """直達日射を浴びる体の表面積の割合を計算する
        """
        df_vertical_distance_from_bldg = self.calc_vertical_distance_from_bldg_to_shade()
        per_insolation_list = []
        street_azimuth_list = []
        for street_azimuth in [math.pi / 180 * i for i in range(180)]:
            vertical_distance_from_bldg = df_vertical_distance_from_bldg.loc[street_azimuth, 0]
            if vertical_distance_from_bldg > self.spacing_from_bldg:
                len_covered_shade = self.bldg_h * (vertical_distance_from_bldg - self.spacing_from_bldg) / vertical_distance_from_bldg
                if self.person_h > len_covered_shade:
                    per_insolation = (self.person_h - len_covered_shade) / self.person_h
                else:
                    per_insolation = 0
            else:
                per_insolation = 1
            per_insolation_list.append(per_insolation)
            street_azimuth_list.append(round(math.degrees(street_azimuth), 0))

        per_insolation_df = pd.DataFrame(per_insolation_list, index=street_azimuth_list)
        return per_insolation_df


class CalcJvPerStreetAzimuth:
    """道路の方位角ごとに直達日射を計算する
    """

    solar_constant = 1370  # 太陽定数(w/m^2)
    atmospheric_transmittance_list = [0.72, 0.69, 0.64, 0.61, 0.60, 0.59, 0.60, 0.61, 0.64, 0.67, 0.69, 0.71]  # 大気透過率　福岡


    def __init__(self, date, h, A):
        self.date = date
        self.h = h
        self.A = A


    def calc_normal_direct_insolation(self):
        """法線面直達日射量を計算する
        """
        if self.h <= 0:
            Jd = 0
        else:
            month = self.date.month
            P = self.atmospheric_transmittance_list[month - 1]
            cosec_h = 1 / math.sin(self.h)
            Jd = self.solar_constant * (P ** cosec_h)
        return Jd


    def calc_vertical_direct_insolation(self, azimuth_surface):
        """鉛直面直達日射量を計算する
        """
        Jd = self.calc_normal_direct_insolation()
        diff_rad = self.A - azimuth_surface
        Jv = Jd * math.cos(self.h) * math.cos(diff_rad)
        return Jv


    def calc_azimuth_of_surface_exposed_to_insolation(self, street_azimuth):
        """直達日射を受ける面の方位角を求める(体の腹側か背中側か)
        """
        if math.pi/2 < abs(self.A - street_azimuth) < math.pi /2 * 3:
            azimuth_surface = street_azimuth - math.pi
        else:
            azimuth_surface = street_azimuth
        return azimuth_surface


    def calc_Jv_per_street_azimuth(self):
        """ 直達日射を道路の角度ごとに計算する
        """
        Jv_list = []
        street_azimuth_list = []
        for street_azimuth in [math.pi / 180 * i for i in range(180)]:
            azimuth_surface = self.calc_azimuth_of_surface_exposed_to_insolation(street_azimuth)
            Jv = self.calc_vertical_direct_insolation(azimuth_surface)
            Jv_list.append(Jv)
            street_azimuth_list.append(round(math.degrees(street_azimuth), 0))

        Jv_df = pd.DataFrame(Jv_list, index=street_azimuth_list)
        Jv_df.to_csv("test.csv")
        return Jv_df


class CalcWarmRoute:
    """暖かいルートを地図に表示する
    """

    def __init__(self, Jv_df, per_insolation_df, origin_lat, origin_lon, dest_lat, dest_lon):
        self.Jv_df = Jv_df
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.dest_lat = dest_lat
        self.dest_lon = dest_lon
        self.per_insolation_df = per_insolation_df


    def get_road_data(self):
        """対象範囲内の道路の角度と長さを得る
        """
        with open("app_sunlight/static/app_sunlight/pickle/bearings_and_len_fukuokacity.pkl", "rb") as bearings_len:
            G = pickle.load(bearings_len)
        return G


    def map_coldness(self):
        """体に浴びる直達日射の量による寒さ度合いを道路データにマッピング
        """
        G = self.get_road_data()
        coldness_dict = {}
        for edge, bearing in nx.get_edge_attributes(G, "rough_bearing").items():
            Jv = self.Jv_df.loc[bearing, 0]
            per_insolation = self.per_insolation_df.loc[bearing, 0]
            length = G.edges[edge]["length"]
            coldness_dict[edge] = length / Jv * per_insolation
        nx.set_edge_attributes(G, coldness_dict, "coldness")
        return G


    def calc_route(self):
        """一番暖かいルートを求める
        """
        G = self.map_coldness()
        origin_node = ox.get_nearest_node(G, (self.origin_lat, self.origin_lon))
        dest_node = ox.get_nearest_node(G, (self.dest_lat, self.dest_lon))
        route_warm = nx.shortest_path(G, origin_node, dest_node, weight="coldness")
        return G, route_warm, origin_node, dest_node


    def plot_warm_route(self):
        """一番暖かいルートを地図にプロット
        """
        route_map = folium.Map(
            location=[self.origin_lat, self.origin_lon],
            tiles='https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',
            attr="<a href='https://maps.gsi.go.jp/development/ichiran.html' target='_blank'>地理院タイル</a>",
            zoom_start=11)

        G, route_warm, _, _ = self.calc_route()
        m = ox.plot.plot_route_folium(G, route_warm, route_map=route_map)

        folium.Marker(
            location=[self.origin_lat, self.origin_lon],
            popup='出発地', icon=folium.Icon(icon='walking')
        ).add_to(m)

        folium.Marker(
            location=[self.dest_lat, self.dest_lon],
            popup='目的地', icon=folium.Icon(icon='walking')
        ).add_to(m)

        m.save('app_sunlight/static/app_sunlight/html/map_result.html')

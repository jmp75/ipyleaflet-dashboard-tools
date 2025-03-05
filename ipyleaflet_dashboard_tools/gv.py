from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import xarray as xr
from ipyleaflet import Icon, Map, Marker, MarkerCluster, basemaps

# from ipyleaflet import basemaps, FullScreenControl, LayerGroup, Map, MeasureControl, Polyline, Marker, MarkerCluster, CircleMarker, WidgetControl
from ipywidgets import HTML, Output

# Had unexpected issues with displaying matplotlib in output widgets.
# https://github.com/jupyter-widgets/ipywidgets/issues/1853#issuecomment-349201240 seems to do the job...
from ipywidgets.widgets.interaction import show_inline_matplotlib_plots


def default_html_popup_factory(identifier:str) -> HTML:
    """A default popup factory that creates a simple HTML widget with the identifier as the value."""
    message = HTML()
    message.description = "Identifier"
    message.value = str(identifier)
    message.placeholder = ""
    return message

@dataclass
class MarkerInfo:
    """holds geolocation information of an identified point, optionally with a marker object.
    """
    identifier : str = ""
    lat : float = 0.0
    lon : float = 0.0
    marker: Marker = None

class MapMarkers:
    """A class to hold a map and a collection of markers, with a dictionary to look up markers by identifier."""
    def __init__(self, map:Map):
        self.map = map
        self.markers:Dict[str,MarkerInfo] = dict()
    
    def add_marker(self, identifier:str, marker:MarkerInfo):
        self.markers[identifier] = marker

class GeoViewer:
    """A class to facilitate the display of xarray held geospatial data in a map, with hooks to customise actions on click."""

    def __init__(
        self,
        x_data: xr.Dataset,
        lat: str = "lat",
        lon: str = "lon",
        identifier: str = "station",
    ):
        """_summary_

        Args:
            x_data (xr.Dataset): xarray dataset or dataarray
            lat (str, optional): coordinate in x_data with the latitude information. Defaults to 'lat'.
            lon (str, optional): coordinate in x_data with the longitude information. Defaults to 'lon'.
            identifier (str, optional): coordinate in x_data with an identifier used as a key for action on marker events (onclick or potentially other). Defaults to 'station'.
        """
        self.__marker_info: Dict[str, MarkerInfo] = dict()
        self.x_data = x_data
        self.identifier = identifier
        values_id = x_data[identifier].values
        if len(values_id) != len(set(values_id)):
            raise ValueError(
                f"Values in identifier coordinate '{identifier}' is not unique in the dataset"
            )
        lats = x_data[lat].values
        lons = x_data[lon].values
        self.lat_key = lat
        self.lon_key = lon
        n = len(lats)
        for i in range(n):
            self.__add_marker_info(lats[i], lons[i], values_id[i])

    def marker_info(self, identifier: str) -> MarkerInfo:
        """Retrieve the marker information for a given identifier."""
        return self.__marker_info.get(identifier, None)

    def __add_marker_info(self, lat: float, lon: float, ident: str):
        self.__marker_info[ident] = MarkerInfo(ident, lat, lon)

    def filter_markers(self, identifiers: List[str]):
        """Filter the markers to only include those with identifiers in the list."""
        self.__marker_info = {k: v for k, v in self.__marker_info.items() if k in identifiers}

    def build_mapmarkers(
        self,
        click_handler_factory: Optional[Callable[[str], Callable[[Any], None]]] = None,
        icon_factory: Optional[Callable[[str], Icon]] = None,
        popup_factory: Optional[Callable[[str], HTML]] = None,
        zoom: int = 4,
        basemap=basemaps.OpenTopoMap
    ) -> MapMarkers:
        """Build a map with markers for each of the identified points in the dataset.

        Args:
            click_handler_factory (Optional[Callable[[str], Callable[[Any], None]]], optional): A factory method to create marker on_click callbacks. Defaults to None.
            icon_factory (Optional[Callable[[str], Icon]], optional): factory function that creates an ipyleaflet Icon for each identifier. Defaults to None.
            popup_factory (Optional[Callable[[str], HTML]], optional): factory function to create an HTML popup for each identifier/marker. Defaults to None.
            zoom (int, optional): initial leaflet zoom level. Defaults to 4.
            basemap (_type_, optional): basemap. Defaults to basemaps.OpenTopoMap.

        Returns:
            MapMarkers: A MapMarkers object with the map and markers.
        """
        mean_lat = self.x_data[self.lat_key].values.mean()
        mean_lng = self.x_data[self.lon_key].values.mean()
        # create the map
        m = Map(center=(mean_lat, mean_lng), zoom=zoom, basemap=basemap)
        m.layout.height = "1200px"
        popup_factory = popup_factory or default_html_popup_factory
        icon_factory = icon_factory or (lambda x: None)
        mm = MapMarkers(m)
        markers = []
        for k in self.__marker_info:
            message = popup_factory(k)
            icon = icon_factory(k)
            info = self.__marker_info[k]
            location = info.lat, info.lon
            marker = Marker(location=location, draggable=False, icon=icon)
            if click_handler_factory is not None:
                click_handler = click_handler_factory(k)
                marker.on_click(click_handler)
            marker.popup = message
            mm.add_marker(k, MarkerInfo(identifier=k, lat=info.lat, lon=info.lon, marker=marker))
            markers.append(marker)
        marker_cluster = MarkerCluster(markers=markers)
        m.add_layer(marker_cluster)
        return mm

    def build_map(
        self,
        click_handler_factory: Optional[Callable[[str], Callable[[Any], None]]] = None,
        icon_factory: Optional[Callable[[str], Icon]] = None,
        popup_factory: Optional[Callable[[str], HTML]] = None,
        zoom: int = 4,
        basemap=basemaps.OpenTopoMap
    ) -> Map:
        """Legacy API function. Build a map with markers for each of the identified points in the dataset.

        Args:
            click_handler_factory (Optional[Callable[[str], Callable[[Any], None]]], optional): A factory method to create marker on_click callbacks. Defaults to None.
            icon_factory (Optional[Callable[[str], Icon]], optional): factory function that creates an ipyleaflet Icon for each identifier. Defaults to None.
            popup_factory (Optional[Callable[[str], HTML]], optional): factory function to create an HTML popup for each identifier/marker. Defaults to None.
            zoom (int, optional): initial leaflet zoom level. Defaults to 4.
            basemap (_type_, optional): basemap. Defaults to basemaps.OpenTopoMap.

        Returns:
            Map: A Map object with the markers.
        """
        mm = self.build_mapmarkers(click_handler_factory, icon_factory, popup_factory, zoom, basemap)
        return mm.map

    def __plot_series(
        self, out_widget: Output, variable: str, loc_id: str, dim_id: str = None
    ):
        """ """
        tts = self.get_data(variable=variable, loc_id=loc_id, dim_id=dim_id)
        # if using bqplot down the track, see https://github.com/jtpio/voila-gpx-viewer
        out_widget.clear_output()
        with out_widget:
            _ = tts.plot(figsize=(16, 8))
            # do not use display(blah) which then displays the obnoxious matplotlib.lines.Line2D object at etc.>]
            ax = plt.gca()
            ax.set_title(loc_id)
            show_inline_matplotlib_plots()

    def __mk_click_handler_plot_ts(self, out_widget: Output, variable="q_obs_mm"):
        def click_handler_plot_ts(**kwargs):
            xy = kwargs["coordinates"]
            ident = self.get_code(xy[0], xy[1])
            self.__plot_series(out_widget, variable=variable, loc_id=ident)

        return click_handler_plot_ts

def click_handler_no_op(**kwargs):
    return

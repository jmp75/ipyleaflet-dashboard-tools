#!/usr/bin/env python

"""Tests for `ipyleaflet_dashboard_tools` package."""

from ipyleaflet_dashboard_tools.gv import GeoViewer

import xarray as xr
import numpy as np
import pandas as pd
import pytest

import ipyleaflet as ipl
import ipywidgets as ipw

def create_dataset():
    STATION_ID_DIM = "station"
    TIME_ID_DIM = "time"
    lon = np.array([1.0, 2, 3])
    lat = np.array([4.0, 5, 6])
    time = pd.date_range("2000-01-01", periods=7)
    np.random.seed(0)
    temperature = np.random.randn(3, 7)
    precipitation = np.random.randn(3, 7)
    stations = ["a", "b", "c"]
    ds = xr.Dataset(
        data_vars=dict(
            temperature=([STATION_ID_DIM, TIME_ID_DIM], temperature),
            precipitation=([STATION_ID_DIM, TIME_ID_DIM], precipitation),
        ),
        coords=dict(
            lon=(STATION_ID_DIM, lon),
            lat=(STATION_ID_DIM, lat),
            station=(STATION_ID_DIM, stations),
            time=time,
        ),
        attrs=dict(description="Weather related data."),
    )
    return ds


def test_creation_defaults():
    x = create_dataset()
    gv = GeoViewer(x, lat="lat", lon="lon", identifier="station")
    map = gv.build_map()
    assert map is not None

class TestGeoViewer:
    def __init__(self) -> None:
        self.clicks = {}
        self.popups = {}

    def _log_click(self, id:str, **kwargs):
        if id not in self.clicks:
            self.clicks[id] = []
        self.clicks[id].append(kwargs)

    def mk_click_handler_factory(self):
        def factory(ident:str):
            def f(**kwargs):
                self._log_click(ident, **kwargs)
            return f
        return factory
        
    def mk_icon_factory(self):
        def f(ident:str):
            return ipl.AwesomeIcon(
                name="gauge", marker_color="orange", icon_color="white", spin=False
            )
        return f

    def mk_popup_factory(self):
        def f(ident:str):
            message = ipw.HTML()
            message.description = "Identifier"
            message.value = str(ident)
            message.placeholder = ""
            self.popups[ident] = message
            return message
        return f

def test_creation_custom_factories():
    x = create_dataset()
    gv = GeoViewer(x, lat="lat", lon="lon", identifier="station")
    tgv = TestGeoViewer()
    mm = gv.build_mapmarkers(
        click_handler_factory=tgv.mk_click_handler_factory(),
        icon_factory=tgv.mk_icon_factory(),
        popup_factory=tgv.mk_popup_factory(),
    )
    assert mm is not None
    assert len(mm.markers) == 3, "There should be three markers"
    marker_a = mm.markers["a"].marker
    cb = marker_a._click_callbacks.callbacks
    assert len(cb) == 1, "There should be only one callback for the marker on click event handler"
    cb_func = cb[0] # the callback function expected to have kw arguments **kwargs
    cb_func(my_key = 'my_value')
    assert 'a' in tgv.clicks
    args = tgv.clicks['a']
    assert len(args) == 1
    assert "my_key" in args[0], "The click handler should have received the argument 'my_key' with value 'my_value'"
    assert args[0]["my_key"] == "my_value"


if __name__ == "__main__":
    test_creation_defaults()
    test_creation_custom_factories()
    
from fastapi.encoders import jsonable_encoder

from app import store

from app.classes import RoastSession, RoastEventId, Point
from app.loggers import LOG_UVICORN

import numpy


async def auto_detect_charge():
    session: RoastSession = store.session
    ror: list[Point] = session.channels[0].ror
    if (RoastEventId.C not in session.roast_events) & (len(ror) > 5):
        # window array: [ 0][ 1][ 2][ 3][ 4]
        #    ror array: [-5][-4][-3][-2][-1]
        #                       ^^^^
        #                       CHARGE

        window = list(map(lambda p: p.value, ror[-5:]))
        dpre = (window[0] + window[1]) / 2.0
        dpost = (window[3] + window[4]) / 2.0
        if (
            (window[0] > 0.0)
            & (window[1] > 0.0)
            & (window[3] < 0.0)
            & (window[4] < 0.0)
            & (abs(dpost) > abs(dpre) * 2)
        ):
            charge_index = len(ror) - 3

            LOG_UVICORN.info("auto detected chargeat ror index: %s", charge_index)

            session.roast_events[RoastEventId.C] = charge_index

            # re calculate time
            session.start_time = session.channels[0].data[charge_index].timestamp
            for channel in session.channels:
                for point in channel.data:
                    point.time = (point.timestamp - session.start_time).total_seconds()
                for point in channel.ror:
                    point.time = (point.timestamp - session.start_time).total_seconds()

            await store.socketio_server.emit(
                "roast_events",
                jsonable_encoder(
                    [
                        {"id": key, "index": value}
                        for key, value in session.roast_events.items()
                    ]
                ),
            )


async def auto_detect_drop():
    session: RoastSession = store.session
    ror: list[Point] = session.channels[0].ror
    if (
        (RoastEventId.TP in session.roast_events)
        & (RoastEventId.D not in session.roast_events)
        & (len(ror) > 5)
    ):
        # window array: [ 0][ 1][ 2][ 3][ 4]
        #    ror array: [-5][-4][-3][-2][-1]
        #                       ^^^^
        #                       DROP

        window = list(map(lambda p: p.value, ror[-5:]))
        dpre = (window[0] + window[1]) / 2.0
        dpost = (window[3] + window[4]) / 2.0
        if (
            (window[0] > 0.0)
            & (window[1] > 0.0)
            & (window[3] < 0.0)
            & (window[4] < 0.0)
            & (abs(dpost) > abs(dpre) * 2)
        ):
            drop_index = len(ror) - 3

            LOG_UVICORN.info("auto detected drop at ror index: %s", drop_index)

            session.roast_events[RoastEventId.D] = drop_index

            await store.socketio_server.emit(
                "roast_events",
                jsonable_encoder(
                    [
                        {"id": key, "index": value}
                        for key, value in session.roast_events.items()
                    ]
                ),
            )


async def auto_detect_dry_end():
    session: RoastSession = store.session

    if (RoastEventId.TP in session.roast_events) & (
        RoastEventId.DE not in session.roast_events
    ):
        bt: list[Point] = session.channels[0].data

        dry_end = 150

        if (bt[-1].value > dry_end) & (bt[-2].value > dry_end):

            dry_end_index = len(bt) - 2

            session.roast_events[RoastEventId.DE] = dry_end_index

            await store.socketio_server.emit(
                "roast_events",
                jsonable_encoder(
                    [
                        {"id": key, "index": value}
                        for key, value in session.roast_events.items()
                    ]
                ),
            )


async def auto_detect_turning_point():

    session: RoastSession = store.session

    if (RoastEventId.C in session.roast_events) & (
        RoastEventId.TP not in session.roast_events
    ):

        bt: list[Point] = session.channels[0].data

        tp = 1000
        high_temp = 0
        target_index = 0
        tp_found = False
        temp_drop = 0

        for p in bt:
            tp = min(p.value, tp)
            high_temp = max(p.value, high_temp)

            temp_drop = high_temp - tp
            if (bt[-1].value > tp) & (bt[-2].value > tp) & (temp_drop > 50):
                target_index = len(bt) - 3
                tp_found = True
                break

        if tp_found:
            session.roast_events[RoastEventId.TP] = target_index
            await store.socketio_server.emit(
                "roast_events",
                jsonable_encoder(
                    [
                        {"id": key, "index": value}
                        for key, value in session.roast_events.items()
                    ]
                ),
            )


# https://github.com/erykml/medium_articles/blob/master/Machine%20Learning/outlier_detection_hampel_filter.ipynb
def hampel_filter_forloop_point(input_series: list[Point], window_size, n_sigmas=3):

    input_series_value = []
    for p in input_series:
        input_series_value.append(p.value)

    n = len(input_series)
    filtered = input_series.copy()
    k = 1.4826  # scale factor for Gaussian distribution

    outliers = []

    # possibly use np.nanmedian
    for i in range((window_size), (n - window_size)):
        x0 = numpy.median(input_series_value[(i - window_size) : (i + window_size)])
        s0 = k * numpy.median(
            numpy.abs(input_series_value[(i - window_size) : (i + window_size)] - x0)
        )
        if numpy.abs(input_series_value[i] - x0) > n_sigmas * s0:
            filtered[i] = Point(input_series[i].timestamp, input_series[i].time, x0)
            outliers.append(input_series[i])

    return filtered, outliers

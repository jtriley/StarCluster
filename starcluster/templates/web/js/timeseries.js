// Values must be a list of two-element lists with the first element being
// a javascript timestamp and the second element a value
// NOTE: A Javascript timestamp is the number of milliseconds since
// January 1, 1970 00:00:00 UTC. This is almost the same as Unix timestamps,
// except it's in milliseconds, so remember to multiply by 1000!
var d = {{ time_series_data }};

// helper for returning the weekends in a period
function weekendAreas(axes) {
    var markings = [];
    var d = new Date(axes.xaxis.min);
    // go to the first Saturday
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 1) % 7))
    d.setUTCSeconds(0);
    d.setUTCMinutes(0);
    d.setUTCHours(0);
    var i = d.getTime();
    do {
        // when we don't set yaxis, the rectangle automatically
        // extends to infinity upwards and downwards
        markings.push({ xaxis: { from: i, to: i + 2 * 24 * 60 * 60 * 1000 } });
        i += 7 * 24 * 60 * 60 * 1000;
    } while (i < axes.xaxis.max);

    return markings;
}

var options = {
    xaxis: { mode: "time", tickLength: 5 },
    yaxis: { min: 0 },
    selection: { mode: "x" },
    grid: { markings: weekendAreas,
            color: "#ffffff",
            markingsColor: "#993333" }
};

var plot = $.plot($("#placeholder"), [d], options);

var overview = $.plot($("#overview"), [d], {
    series: {
        lines: { show: true, lineWidth: 1 },
        shadowSize: 0
    },
    xaxis: { ticks: [], mode: "time" },
    yaxis: { ticks: [], min: 0, autoscaleMargin: 0.1 },
    selection: { mode: "x" }
});

// now connect the two

$("#placeholder").bind("plotselected", function (event, ranges) {
    // do the zooming
    plot = $.plot($("#placeholder"), [d],
                  $.extend(true, {}, options, {
                      xaxis: { min: ranges.xaxis.from, max: ranges.xaxis.to }
                  }));

    // don't fire event on the overview to prevent eternal loop
    overview.setSelection(ranges, true);
});

$("#overview").bind("plotselected", function (event, ranges) {
    plot.setSelection(ranges);
});

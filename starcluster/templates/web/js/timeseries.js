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
    xaxis: { zoomRange: {{ xzoomrange }}, panRange: {{ xpanrange }}, mode: "time", tickLength: 5 },
    yaxis: { zoomRange: {{ yzoomrange }}, panRange: {{ ypanrange }}, min: 0 },
    selection: { mode: "x" },
    grid: { markings: weekendAreas,
            color: "#ffffff",
            markingsColor: "#993333",
            hoverable: true,
            clickable: true },
    zoom: { interactive: true },
    pan: { interactive: true },
    series: { lines: { show: true }, points: { show: false }, shadowSize: 6 },
};

var placeholder = $("#placeholder");
var plot = $.plot(placeholder, [d], options);

function addArrow(dir, right, top, offset) {
    $('<img class="button" title="Pan ' + dir + '" src="/imgs/arrow-' + dir + '.png" style="right:' + right + 'px;top:' + top + 'px">').appendTo(placeholder).click(function (e) {
        e.preventDefault();
        plot.pan(offset);
    });
}

function addZoom(dir, right, top) {
    if(dir=="in"){
        $('<img class="button" title="Zoom In" src="/imgs/zoom' + dir + '.png" style="right:' + right + 'px;top:' + top + 'px">').appendTo(placeholder).click(function (e) {
            e.preventDefault();
            plot.zoom();
        });
    } else if(dir=="out"){
        $('<img class="button" title="Zoom Out" src="/imgs/zoom' + dir + '.png" style="right:' + right + 'px;top:' + top + 'px">').appendTo(placeholder).click(function (e) {
            e.preventDefault();
            plot.zoomOut();
        });
    } else if(dir=="reset"){
        $('<img class="button" title="Reset Plot" src="/imgs/reset.png" style="right:' + right + 'px;top:' + top + 'px">').appendTo(placeholder).click(function (e) {
            e.preventDefault();
            plot = $.plot(placeholder, [d], options);
            addControls();
        });
    }
}

function addBackground(right, top) {
    $('<img class="button" src="/imgs/controlsbg.png" style="right:' + right + 'px;top:' + top + 'px">').appendTo(placeholder)
}

function addControls() {
    var ctrx = 50;
    var ctry = 40;
    var vertlen = 60;
    var horlen = 35;

    addBackground(ctrx - 18, ctry - 30);
    addArrow('up', ctrx, ctry - vertlen/2.0, { top: -100 });
    addZoom('in', ctrx-3, 25);
    addZoom('reset', ctrx-3, 40);
    addZoom('out', ctrx-3, 55);
    addArrow('down', ctrx, ctry + vertlen/2.0, { top: 100 });
    addArrow('right', ctrx - horlen/2.0 - 1, ctry + 2, { left: 100 });
    addArrow('left', ctrx + horlen/2.0 - 4, ctry + 2, { left: -100 });
}

addControls();

function showTooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
        position: 'absolute',
        display: 'none',
        top: y + 5,
        left: x + 5,
        border: '1px solid #fdd',
        padding: '2px',
        'background-color': '#000',
        opacity: 0.80
    }).appendTo("body").fadeIn(200);
}

var previousPoint = null;
placeholder.bind("plothover", function (event, pos, item) {
    if (item) {
        if (previousPoint != item.dataIndex) {
            previousPoint = item.dataIndex;

            $("#tooltip").remove();
            var x = item.datapoint[0].toFixed(2),
                y = item.datapoint[1].toFixed(4);

            showTooltip(item.pageX, item.pageY, "$" + y);
        }
    }
    else {
        $("#tooltip").remove();
        previousPoint = null;
    }
});

$("#placeholder").bind("plotclick", function (event, pos, item) {
    if (item) {
        plot.highlight(item.series, item.datapoint);
    }
});

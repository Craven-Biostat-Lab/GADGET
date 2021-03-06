// script for event search page
// requires jquery

// string variables "genes_arg", "genesyms_arg", and "q_arg" declared on html page (query string arguments)

var initiallimit = 20; // number of events to show on page load
var limit = 20; // number of events to show when "more" button is clicked
var offset = 0; // keep track of how many events are on the page

var summarylimit = 20; // number of event summary rows to show on page load
var summaryorder = 'abstracts' // default sort order for the summary table

$(document).ready(function()
{
    var querystring = genes_arg + q_arg + "&limit=" + initiallimit;
    offset += initiallimit;
    
    // get initial event results
    spin();
    $.get('eventlist.html', querystring)
    .success(function(result)
    {
        $("div#description").show();
        $("table#events").append(result);
        $("div#results").fadeIn(200);
        $("table#download").fadeIn('slow');
        hidespinner();
        $("#more").show();
    })
    .error(function() {
        hidespinner();
        flash("No events found!  Please try a different query.");
    });
    
    eventsummary(); // fetch and render event summary
    
    // fetch and display more events
    $('input#more').click(function()
    {
        var querystring = genes_arg + q_arg + "&limit=" + limit + "&offset=" + offset;
        offset += limit;
        
        spin();
        $("input#more").hide();
        $.get("eventlist", querystring)
        .success(function(result) 
        {
            $("table#events").append(result);
            hidespinner();
            $("input#more").show();
        })
        .error(function() 
        {
            $("input#more").hide();
            hidespinner();
            $("div#content").append("No more interactions for this query!");
        });
    });
});

// fetch and display a table of genes referenced in events for this query
function eventgenes()
{
    if ($("table#eventgenes").length == 0) // make sure the table doesn't already exist
    {
        spin();
        $("div#description a#showeventgenes").parent("li").hide();
        
        var querystring = genes_arg + q_arg;
        $.get("eventgenes", querystring)
        .success(function(result)
        {
            $("div#eventgenes").append(result).slideDown();
        })
        .complete(function()
        {
            hidespinner();
        });
    }
}

// add the given gene to the search
function addgene(gene)
{
    // create new "genes" querystring argument
    var newgenes;
    if (genesyms_arg == "") 
        {newgenes = "&genes=";}
    else 
        {newgenes = genesyms_arg + ", ";}
    
    window.location = "eventsearch?" + q_arg + newgenes + gene;
}

// fetch and render the event summary
function eventsummary()
{
    var querystring = genes_arg + q_arg + "&orderby=" + summaryorder;
    
    if (summarylimit != null)
    {
        querystring = querystring + "&limit=" + summarylimit
    }
    
    $.getJSON('eventsummary', querystring)
    .success(function(data)
    {
        if (data.validresult)
        {
            $("table#eventsummary").html(data.result);
            $("div#eventsummarycontainer").slideDown(200);
        }
    });
}

// re-sort (re-fetch and render) the event summary table
function ordersummary(key)
{
    summaryorder = key;
    eventsummary();
}

// get full, unlimited summary
function moresummary()
{
    $("div#eventsummarycontainer a#moresummary").hide();
    summarylimit = null;
    eventsummary();
}

// preserve initial form values so the form matches the results on page load
// (without this, the form values get messed up when the user presses the back button.)

var initialquery = null;
var initialgenes = null;

$(window).bind('pageshow', function() {
    if (initialquery == null) {initialquery = $("input#id_q").val();}
    else {$("input#id_q").val(initialquery);}
    
    if (initialgenes == null) {initialgenes = $("input#id_genes").val();}
    else {$("input#id_genes").val(initialgenes);}
});

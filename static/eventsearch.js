// script for event search page
// requires jquery

// string variables "genes_arg" and "q_arg" declared on html page (query string arguments)

var initiallimit = 20; // number of events to show on page load
var limit = 20; // number of events to show when "more" button is clicked
var offset = 0; // keep track of how many events are on the page

$(document).ready(function()
{
    var querystring = genes_arg + q_arg + "&limit=" + initiallimit;
    offset += initiallimit;
    
    // get initial results
    spin();
    $.get('eventlist.html', querystring)
    .success(function(result)
    {
        $("div#description").show();
        $("table#events").append(result).fadeIn(200);
        $("#more").show();
        hideflash();
    })
    .error(function() {flash("No events found!  Please try a different query.")});
    
    // fetch and display more events
    $('input#more').click(function()
    {
        var querystring = genes_arg + q_arg + "&limit=" + limit + "&offset=" + offset;
        offset += limit;
        
        spin();
        $.get("eventlist", querystring)
        .success(function(result) 
        {
            $("table#events").append(result);
            hideflash();
        })
        .error(function() 
        {
            flash("No more events for this query.");
            $("#more").hide();
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
            hideflash();
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


// script for gene search page
// requires jquery

// string variables "q" and "orderby" declared on html page (query string arguments)

var initialLimit = 100;
var limit = 100;
var offset = 0;

var abstractlimit = 15;

// build the query string and redirect to a page with the new ordering
function order(key)
{
    var querystring = "q=" + q + "&orderby=" + key;
    window.location = "genesearch?" + querystring;
}

$(document).ready(function()
{
    var queryString = "q=" + q + "&orderby=" + orderby + "&limit=" + initialLimit;
    offset += initialLimit;
    
    // get initial results
    spin();
    $.get("genelist.html", queryString)
    .success(function(result)
    {
        // append new genes to table, show "more" button
        $("div#description").show();
        $("#generank").append(result).fadeTo(200, 1);
        stripetables();
        $("#more").show();
        hideflash();
    })
    .error(function() {flash("No results found!  Please try a different query.")});
    
    // get and display more genes when the "more" button gets clicked
    $("input#more").click(function()
    {
        var queryString = "q=" + q + "&orderby=" + orderby + "&limit=" + limit + "&offset=" + offset;
        offset += limit;
        
        // get more genes
        spin();
        $.get("genelist.html", queryString)
        .success(function(result)
        {
            // append new genes to table
            $("#generank").append(result);
            stripetables();
            hideflash();
        })
        .error(function()
        {
            // no more genes, hide the button
            flash("No more results.");
            $("#more").hide();
        });
    });
    
    // download button
    $("input#download").click(function()
    {
        window.location = "genelist.csv?download=True&q=" + q + "&orderby=" + orderby;
    });
    
    // show / hide abstracts when the + or - gets clicked
    $("#generank").delegate("a.showabstracts", "click", function()
    {
        var gene = $(this).attr("gene");
        
        if ($("#generank tr#a" + gene).length == 0) // see if the tr for absracts exists
        {
            // assemble querystring
            var querystring = "q=" + q + "&gene=" + gene + "&limit=" + abstractlimit;
            
            // set up abstract area
            $(this).html("&ndash;");
            $("#generank tr#" + gene).after('<tr class="abstracts" id="a' + gene + '"><td colspan="100"><img src="/static/spinner2.gif"></td></tr>');
            
            // fetch and display abstracts
            $.get("abstracts.html", querystring)
            .success(function(result)
            {
                // append abstracts to td
                $("#generank tr#a" + gene + " td img").remove(); // hide spinner
                $("#generank tr#a" + gene + " td").append('<div style="display:none; padding-top:5px;"><b>Abstracts:</b><ul>' + result + '</ul></div>')
                
                // if there are more abstracts, show a "more" link
                var hits = parseInt($("#generank tr#" + gene).attr("hits"));
                if (hits > abstractlimit)
                {
                    $("#generank tr#a" + gene + " td div").append('<a id="more' + gene + '" gene="' + gene + '" class="moreabstracts" href="javascript: void(0);" offset="' + abstractlimit + '">More abstracts...</a>');
                }
                
                $("#generank tr#a" + gene + " td div").slideDown();
                
                // get event preview
                var querystring = "q=" + q + "&genes=" + gene + "&limit=3&preview=1";
                $.get("eventlist.html", querystring)
                .success(function(result)
                {
                    $("#generank tr#a" + gene + " td div").prepend(result + "<br><br>");
                });
            });
        }
        else
        {
            // hide the abstract pane
            $("#generank tr#a" + gene + " td div").slideUp('fast', function() {$("#generank tr#a" + gene).remove()});
            $(this).html("+");
        }
    });
    
    // show more abstracts when the "more abstracts" link gets clicked
    $("#generank").delegate("a.moreabstracts", "click", function() 
    {
        spin();
        
        var id = $(this).attr("id");
        var gene = $(this).attr("gene");
        var offset = parseInt($(this).attr("offset"));
        var hits = parseInt($("#generank tr#" + gene).attr("hits"));
        
        // update offset
        $(this).attr("offset", offset + abstractlimit);
        
        // fetch and display abstracts
        var querystring = "q=" + q + "&gene=" + gene + "&limit=" + abstractlimit + "&offset=" + offset;
        $.get("abstracts.html", querystring)
        .success(function(result)
        {
            $("#generank tr.abstracts#a" + gene + " td div ul").append(result);
            
            // hide the "more" link if there are no more abstracts
            if (offset + abstractlimit > hits)
            {
                $("#generank a#" + id).hide();
            }
        })
        .error(function()
        {
            $("#generank a#" + id).hide();
            flash("No more abstracts for this gene!");
        });
        
        hideflash();
    });
});

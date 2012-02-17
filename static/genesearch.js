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
    $.getJSON("genelist", queryString)
    .success(function(data)
    {
        if (data.validresult)
        {
            // append new genes to table, show "more" button
            $("#generank").append(data.result);
            stripetables();
            
            $("div#description").show();
            $("#results").fadeTo(200, 1);
            $("table#download").fadeIn('slow');
            
            $("#more").show();
            hideflash();        
        }
        else
        {
            // display error message
            flash(data.errmsg);
        }
    })
    .error(function() {flasherror();} );
    
    // get and display more genes when the "more" button gets clicked
    $("input#more").click(function()
    {
        var queryString = "q=" + q + "&orderby=" + orderby + "&limit=" + limit + "&offset=" + offset;
        offset += limit;
        
        // get more genes
        spin();
        $.getJSON("genelist", queryString)
        .success(function(data)
        {
            if (data.validresult)
            {
                // append new genes to table
                $("#generank").append(data.result);
                stripetables();
                hideflash();
            }
            else
            {
                // If "validresult" is false, we ran out of genes.  (Ot
                flash("No more genes match your query.");
                $("#more").hide(); 
            }
        })
        .error(function() {
            flasherror();
            $("#more").hide();    
        });
        
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
            $("#generank tr#" + gene).after('<tr class="abstracts" id="a' + gene + '"><td colspan="13"><img src="/static/spinner2.gif"></td></tr>');
            
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

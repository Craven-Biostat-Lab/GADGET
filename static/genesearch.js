// script for gene search page
// requires jquery

// string variables "q", "genes", "species", "usehomologs" and "orderby"
// declared on html page (from query string arguments)

var initialLimit = 100;
var limit = 100;
var offset = 0;

var abstractlimit = 15;

// build the query string and redirect to a page with the new ordering
function order(key)
{
    var querystring = "q=" + q + "&genes=" + genes + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + key;
    window.location = "genesearch?" + querystring;
}

$(document).ready(function()
{
    var queryString = "q=" + q + "&genes=" + genes + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + initialLimit;
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
        var queryString = "q=" + q + "&genes=" + genes + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + limit + "&offset=" + offset;
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
        
        if ($("#generank tr#abstracts" + gene).length == 0) // see if the tr for absracts exists
        {
            // assemble querystring
            var querystring = "q=" + q + "&genes=" + genes + "," + gene + "&species=" + species + "&usehomologs=" + usehomologs + "&limit=" + abstractlimit;
            
            // set up abstract area
            $("#generank tr#gene" + gene).after('<tr class="abstracts" id="abstracts' + gene + '"><td colspan="13"><img src="/static/spinner2.gif"></td></tr>');
            
            // fetch and display abstracts
            $.getJSON("abstracts.html", querystring)
            .success(function(data)
            {
                if (data.validresult)
                {
                    // append abstracts to td
                    $("#generank tr#abstracts" + gene + " td img").remove(); // hide spinner
                    $("#generank tr#abstracts" + gene + " td").append('<div style="display:none; padding-top:5px;"><b>Abstracts:</b><ul>' + data.result + '</ul></div>')
                    
                    // if there are more abstracts, show a "more" link
                    var hits = parseInt($("#generank tr#gene" + gene).attr("hits"));
                    if (hits > abstractlimit)
                    {
                        $("#generank tr#abstracts" + gene + " td div").append('<a id="more' + gene + '" gene="' + gene + '" class="moreabstracts" href="javascript: void(0);" offset="' + abstractlimit + '">More abstracts...</a>');
                    }
                    
                    $("#generank tr#abstracts" + gene + " td div").slideDown();
                    
                    // get event preview
                    var querystring = "q=" + q + "&gene_entrez_ids=" + genes + ',' + gene + "&limit=3&preview=1";
                    $.get("eventlist.html", querystring)
                    .success(function(result)
                    {
                        $("#generank tr#abstracts" + gene + " td div").prepend(result + "<br><br>");
                    });
                }
                
            })
            .error(function() {
                flash("An error occurred!  Please check your internet connection and try again.  If the error persists, please contact us.");
            });
        }
        else
        {
            // hide the abstract pane
            $("#generank tr#abstracts" + gene + " td div").slideUp('fast', function() {$("#generank tr#abstracts" + gene).remove()});
        }
    });
    
    // show more abstracts when the "more abstracts" link gets clicked
    $("#generank").delegate("a.moreabstracts", "click", function() 
    {
        spin();
        
        var id = $(this).attr("id");
        var gene = $(this).attr("gene");
        var offset = parseInt($(this).attr("offset"));
        var hits = parseInt($("#generank tr#gene" + gene).attr("hits"));
        
        // update offset
        $(this).attr("offset", offset + abstractlimit);
        
        // fetch and display abstracts
        var querystring = "q=" + q + "&genes=" + genes + "," + gene + "&species=" + species + "&usehomologs=" + usehomologs + "&limit=" + abstractlimit + "&offset=" + offset;
        $.getJSON("abstracts.html", querystring)
        .success(function(data)
        {
            if (data.validresult)
            {
                $("#generank tr.abstracts#abstracts" + gene + " td div ul").append(data.result);
                
                // hide the "more" link if there are no more abstracts
                if (offset + abstractlimit > hits)
                {
                    $("#generank a#" + id).hide();
                }
            }
            else
            {
                $("#generank a#" + id).hide();
                flash(data.errmsg);
            }
        })
        .error(function()
        {
            $("#generank a#" + id).hide();
            flash("An error occurred!  Please check your internet connection and try again.  If the error persists, please contact us.");
        });
        
        hideflash();
    });
});

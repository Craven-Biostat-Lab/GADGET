// script for keyphrase search page
// requires jquery

// string variables "q", "genes", "species", "usehomologs" and "orderby"
// declared on html page (from query string arguments)

// number of keywords to fetch on page load
var initialLimit = 100;

// number of keywords to fetch when the "more" button is pressed
var limit = 100;
var offset = 0;

// build the query string and redirect to a page with the new ordering
function order(key)
{
    var querystring = "q=" + q + "&genes=" + genesyms + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + key;
    window.location = "keywordsearch?" + querystring;
}

// collapse the slider panes in the gene results table for a specific keyphrase
function hidepanes(keyphrase)
{
    $("table#keywords tr#abstracts" + keyphrase + " td.pane div").slideUp('fast', function() { $("table#keywords tr#abstracts" + keyphrase).hide(); });
    $("table#keywords a#showabs" + keyphrase).text("Show abstracts");
}

$(document).ready(function()
{
    var queryString = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + initialLimit;
    offset += initialLimit;
    
    // get initial results
    spin();
    $.getJSON("keywordlist", queryString)
    .success(function(data)
    {
        if (data.validresult)
        {
            $("table#keywords").append(data.result);
         
            // show abstract count
            if (data.abstractcount)
                $("span#abstractcount").html(data.abstractcount).show();
            
            $("div#description").show();
            $("#results").fadeTo(200, 1);
            $("table#download").fadeIn('slow');
            
            $("#more").show();
            hidespinner();     
        }
        else
        {
            // display error message
            flash(data.errmsg);
        }
    })
    .error(function() {hidespinner(); flasherror();} );
    
    
    // get and display more genes when the "more" button gets clicked
    $("input#more").click(function()
    {
        var queryString = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + limit + "&offset=" + offset;
        offset += limit;
        
        // hide "more" button while we're fetching more genes
        $("input#more").hide();

        // get more genes
        spin();
        $.getJSON("keywordlist", queryString)
        .success(function(data)
        {
            if (data.validresult)
            {
                // append new genes to table
                $("table#keywords").append(data.result);
                hidespinner();
                $("input#more").show();
            }
            else
            {
                // If "validresult" is false, we ran out of genes.  
                hidespinner();
                $("input#more").hide(); 
                $("div#content").append("No more genes match your query!");
            }
        })
        .error(function() 
        {
            hidespinner();
            flasherror();
            $("input#more").hide();    
        });
        
    });
    
    $("table#keywords").delegate("a.showabstracts", "click", function()
    {
        var keywordnum = $(this).attr("keywordnum");
        
        if ($("table#keywords tr#abstracts" + keywordnum).length == 0) // see if the tr for absracts exists
        {
            // the abstracts pane doesn't exist.
            hidepanes(keywordnum); // hide other panes
            
            // how many abstracts for this keyword?
            var abstractcount = $("tr#keyphrase" + keywordnum).attr("hits");
            
            // assemble querystring
            var querystring = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&genesyms=" + genesyms + "&species=" + species + "&usehomologs=" + usehomologs + "&unique=" + keywordnum + "&keywordnum=" + keywordnum + "&orderby=relevance" + "&abstractcount=" + abstractcount;
        
            // set up abstract pane
            $("table#keywords tr#keyphrase" + keywordnum).after('<tr class="abstracts" id="abstracts' + keywordnum + '"><td></td><td class="pane" colspan="12"><img src="/static/spinner2.gif"></td></tr>');
            
            // change link text
            $(this).text("Hide abstracts");
            
            // fetch and display abstracts
            $.get("abstractview.html", querystring)
            .success(function(result)
            {
                    // append abstracts to td
                    $("table#keywords tr#abstracts" + keywordnum + " td.pane img").remove(); // hide spinner
                    $("table#keywords tr#abstracts" + keywordnum + " td.pane").html(result); 
                    $("table#keywords tr#abstracts" + keywordnum + " td.pane").append('<a href="javascript:void(0);" class="hidepanes" keywordnum="' + keywordnum + '">Hide abstracts</a>');
                    
                    $("table#keywords tr#abstracts" + keywordnum + " td.pane div").slideDown();
                    fetchabstracts(keywordnum);
                
            })
            .error(function() 
            {
                flasherror();
            });
        }
        else // the abstract pane exists
        {
            // is the abstracts pane hidden?
            if (!$("table#keywords tr#abstracts" + keywordnum).is(":visible"))
            {
                // the abstract pane exists but is hidden
                // show the abstract pane
                hidepanes(keywordnum);
                $("table#keywords tr#abstracts" + keywordnum).show();
                $("table#keywords tr#abstracts" + keywordnum + " td.pane div").slideDown();

                $(this).text("Hide abstracts");
            }
            else
            {
                // the abstract exists and is visible
                // hide the abstract pane
                hidepanes(keywordnum);
            }
        }
        
    });
    
    
    // hide the pane when the "hide" link gets clicked
    $("table#keywords").delegate("a.hidepanes", "click", function()
    {
        var keyword = $(this).attr("keywordnum");
        hidepanes(keyword);
    });
});


// preserve initial form values so the form matches the results on page load
// (without this, the form values get messed up when the user presses the back button.)

var initialquery = null;
var initialgenes = null;
var initialgeneop = null;
var initialspecies = null;
var initialhomologs = null;

$(window).bind('pageshow', function() {
    if (initialquery == null) {initialquery = $("input#id_q").val();}
    else {$("input#id_q").val(initialquery);}
    
    if (initialgenes == null) {initialgenes = $("input#id_genes").val();}
    else {$("input#id_genes").val(initialgenes);}
    
    // if neither gene operator is selected, select 'any' by default
    // the django field 'inital' field doesn't work because the form is bound to the request.
    if($("input[name='geneop']:checked").length==0)
        {$("input[name='geneop'][value='any']").attr('checked', 'checked');}

    if (initialgeneop == null) {initialgeneop = $("input[name='geneop']:checked").attr('value');}
    else {$("input[name='geneop'][value='" + initialgeneop + "']").attr('checked', 'checked');}

    if (initialspecies == null) {initialspecies = $("select#id_species").val();}
    else {$("select#id_species").val(initialspecies);}
    
    if (initialhomologs == null) {initialhomologs = $("input#id_usehomologs").attr("checked");}
    else {$("input#id_usehomologs").attr("checked", initialhomologs);}
});
